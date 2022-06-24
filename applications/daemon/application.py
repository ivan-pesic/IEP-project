from collections import Counter

from redis import Redis

from applications.configuration import Configuration
from applications.models import database, Product, Category, ProductCategory
from datetime import datetime
from sqlalchemy import and_, or_
from flask import Flask
import os
import time

os.environ['TZ'] = 'Europe/Belgrade'
time.tzset()
application = Flask(__name__)
application.config.from_object(Configuration)
database.init_app(application)

def categoriesValidForProduct(product, categories):
    dbCategories = Category.query.with_entities(Category.name).join(ProductCategory). \
        filter_by(productId=product.id).all()
    categoriesMap = Counter(dbCategories)
    for category in categories:
        if category not in categoriesMap:
            print(
                "Category {} is not valid for product {}. Discarding update.".format(category,
                                                                                     product.name))
            return False
    return True

while True:
    try:
        with Redis(host=Configuration.REDIS_HOST) as redis:
            print("Daemon up and running.")
            while True:
                with application.app_context():
                    bytesStream = redis.blpop(Configuration.REDIS_PRODUCTS_LIST)[1]
                    print("Message received.")
                    line = bytesStream.decode("utf-8")
                    data = line.split(",")

                    categories = data[0].split("|")
                    productName = data[1]
                    quantity = int(data[2])
                    purchasePrice = float(data[3])

                    product = Product.query.filter(Product.name == productName).first()

                    # no product - create a new one
                    if product is None:
                        print("Making a new product: name: {}, price: {}, quantity: {}, categories: {}".format(
                            productName, purchasePrice, quantity, categories))
                        product = Product(name=productName, price=purchasePrice, available=quantity)
                        database.session.add(product)
                        database.session.commit()

                        for category in categories:
                            dbCategory = Category.query.filter(Category.name == category).first()
                            # category doesn't exist - create a new one
                            if dbCategory is None:
                                print("Making a new category: {}".format(category))
                                dbCategory = Category(name=category)
                                database.session.add(dbCategory)
                                database.session.commit()

                            productCategory = ProductCategory(productId=product.id, categoryId=dbCategory.id)
                            database.session.add(productCategory)

                        database.session.commit()
                    # product exists - check categories first
                    else:
                        print("Updating existing product: name: {}, price: {}, quantity: {}, categories: {}".format(
                            productName, purchasePrice, quantity, categories))
                        if not categoriesValidForProduct(product, categories):
                            continue
                        # categories valid - update product price and quantity
                        currentPrice = product.price
                        currentQuantity = product.available
                        newPrice = (currentQuantity * currentPrice + quantity * purchasePrice) / (
                                currentQuantity + quantity)
                        newQuantity = currentQuantity + quantity
                        product.price = newPrice
                        product.available = newQuantity
                        database.session.commit()
                        print("Updating product: name: {}, price: {}, quantity: {}, categories: {} successful".format(
                            product.name, product.price, product.available, product.categories))
                        # TODO: implement checking of orders


    except Exception as error:
        print(error)
