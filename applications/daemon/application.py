from collections import Counter

from redis import Redis

from applications.configuration import Configuration
from applications.models import database, Product, Category, ProductCategory, ProductOrder
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
    dbCategories = Category.query.join(ProductCategory).filter_by(productId=product.id).all()
    dbCatsList = []
    for category in dbCategories:
        dbCatsList.append(category.name)
    categoriesMap = Counter(dbCatsList)
    for category in categories:
        if category not in categoriesMap:
            print(
                "Category {} is not valid for product {}. Discarding update.".format(category,
                                                                                     product.name))
            return False
    return True


def statusNeedsUpdate(order):
    productOrders = ProductOrder.query.filter(ProductOrder.orderId == order.id).all()

    isFinished = 0
    i = 0
    for productOrder in productOrders:
        if productOrder.received == productOrder.requested:
            isFinished += 1
        i += 1

    return i == isFinished


def checkForOrders(product):
    for order in product.orders:
        if order.status == "COMPLETE":
            continue
        productOrder = ProductOrder.query.filter(
            and_(ProductOrder.productId == product.id, ProductOrder.orderId == order.id)).first()
        remainingToReceive = productOrder.requested - productOrder.received
        if product.available >= remainingToReceive:
            product.available -= remainingToReceive
            productOrder.received = productOrder.requested
            if statusNeedsUpdate(order):
                order.status = "COMPLETE"
        else:
            productOrder.received += product.available
            product.available = 0

        database.session.commit()


while True:
    try:
        print("Daemon up and running.", flush=True)
        while True:
            with Redis(host=Configuration.REDIS_HOST) as redis:
                with application.app_context():
                    bytesStream = redis.blpop(Configuration.REDIS_PRODUCTS_LIST)[1]
                    print("Message received.", flush=True)
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
                            productName, purchasePrice, quantity, categories), flush=True)
                        product = Product(name=productName, price=purchasePrice, available=quantity)
                        database.session.add(product)
                        database.session.commit()

                        for category in categories:
                            dbCategory = Category.query.filter(Category.name == category).first()
                            # category doesn't exist - create a new one
                            if dbCategory is None:
                                print("Making a new category: {}".format(category), flush=True)
                                dbCategory = Category(name=category)
                                database.session.add(dbCategory)
                                database.session.commit()

                            productCategory = ProductCategory(productId=product.id, categoryId=dbCategory.id)
                            database.session.add(productCategory)

                        database.session.commit()
                    # product exists - check categories first
                    else:
                        print("Updating existing product: name: {}, price: {}, quantity: {}, categories: {}".format(
                            productName, purchasePrice, quantity, categories), flush=True)
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
                            product.name, product.price, product.available, product.categories), flush=True)
                        # when existing product is updated, it should be checked whether some order has to be updated
                        checkForOrders(product)


    except Exception as error:
        print(error)
