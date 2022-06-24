from flask import Flask, request, Response, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, create_refresh_token, get_jwt, \
    get_jwt_identity
from redis.client import Redis
from sqlalchemy import and_
import re
import io
import csv

from applications.configuration import Configuration
from applications.models import database, Category, ProductCategory, Product, Order, ProductOrder
from applications.roleDecorator import roleCheck

application = Flask(__name__)
application.config.from_object(Configuration)
jwt = JWTManager(application)

MSG = "message"
REQUESTS_MISSING = "Field requests is missing."
PRODUCT_ID_MISSING = "Product id is missing for request number {}."
PRODUCT_QUANTITY_MISSING = "Product quantity is missing for request number {}."
INVALID_PRODUCT_ID = "Invalid product id for request number {}."
INVALID_QUANTITY = "Invalid product quantity for request number {}."
INVALID_PRODUCT_FOR_REQUEST = "Invalid product for request number {}."


@application.route("/search", methods=["GET"])
@jwt_required()
@roleCheck(role="customer")
def search():
    productName = request.args.get("name", "")
    categoryName = request.args.get("category", "")

    categories = Category.query.join(ProductCategory).join(Product).filter(
        and_(Category.name.contains(categoryName), Product.name.contains(productName))).distinct().all()
    products = Product.query.join(ProductCategory).join(Category).filter(
        and_(Category.name.contains(categoryName), Product.name.contains(productName))).distinct().all()

    categoriesForOutput = []

    for category in categories:
        categoriesForOutput.append(category.name)

    productsForOutput = []
    for product in products:
        productCategories = Category.query.join(ProductCategory).filter(
            ProductCategory.productId == product.id
        ).distinct().all()

        productCategoriesArray = []
        for category in productCategories:
            productCategoriesArray.append(category.name)

        output = {
            "categories": productCategoriesArray,
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "quantity": product.available
        }

        productsForOutput.append(output)

    # print(categoriesForOutput)
    # print(productsForOutput)
    # print("-----------------------------------")
    return jsonify({"categories": categoriesForOutput, "products": productsForOutput})


@application.route("/order", methods=["POST"])
@jwt_required()
@roleCheck(role="customer")
def order():
    requests = request.json.get("requests", None)

    if not requests:
        return jsonify({MSG: REQUESTS_MISSING}), 400

    i = 0
    for item in requests:
        # check id
        try:
            id = item['id']
            try:
                id = int(item['id'])
                if id < 1:
                    return jsonify({MSG: INVALID_PRODUCT_ID.format(i)}), 400
            except ValueError:
                return jsonify({MSG: INVALID_PRODUCT_ID.format(i)}), 400
        except KeyError:
            return jsonify({MSG: PRODUCT_ID_MISSING.format(i)}), 400
        # check quantity
        try:
            quantity = item['quantity']
            try:
                quantity = int(item['quantity'])
                if quantity < 1:
                    return jsonify({MSG: INVALID_QUANTITY.format(i)}), 400
            except ValueError:
                return jsonify({MSG: INVALID_QUANTITY.format(i)}), 400
        except KeyError:
            return jsonify({MSG: PRODUCT_QUANTITY_MISSING.format(i)}), 400
        # check if product exists
        product = Product.query.filter(Product.id == id).first()
        if product is None:
            return jsonify({MSG: INVALID_PRODUCT_FOR_REQUEST.format(i)}), 400

        i = i + 1

    # products are valid - now an order is made
    order = Order(price=0, status="COMPLETE", email=get_jwt_identity())
    database.session.add(order)
    database.session.flush()

    for item in requests:
        id = int(item['id'])
        quantity = int(item['quantity'])

        product = Product.query.filter(Product.id == id).first()
        order.price += product.price * quantity
        productCount = product.available
        received = 0

        if (productCount >= quantity):
            received = quantity
            product.available -= quantity
        else:
            received = productCount
            order.status = "PENDING"
            product.available = 0

        productOrder = ProductOrder(productId=product.id, orderId=order.id, requested=quantity,
                                    received=received, price=product.price)
        database.session.add(productOrder)
        database.session.commit()

    return jsonify({"id": order.id})


@application.route("/status", methods=["GET"])
@jwt_required()
@roleCheck(role="customer")
def status():
    orders = []
    allOrders = Order.query.all()

    for order in allOrders:
        products = []
        for product in order.products:
            name = product.name
            categories = [category.name for category in product.categories]
            productOrder = ProductOrder.query.filter(ProductOrder.orderId == order.id,
                                                     ProductOrder.productId == product.id).first()
            price = productOrder.price
            received = productOrder.received
            requested = productOrder.requested

            products.append(
                {
                    "categories": categories,
                    "name": name,
                    "price": price,
                    "received": received,
                    "requested": requested
                }
            )

        orders.append(
            {
                "products": products,
                "price": order.price,
                "status": order.status,
                "timestamp": order.timestamp
            }
        )

    return jsonify({"orders": orders})


if __name__ == "__main__":
    database.init_app(application)
    application.run(debug=True, port=5000)
