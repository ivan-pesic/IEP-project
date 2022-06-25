from flask import Flask, request, Response, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, create_refresh_token, get_jwt, \
    get_jwt_identity
from redis.client import Redis
from sqlalchemy import and_, func, desc, asc
import re
import io
import csv

from applications.configuration import Configuration
from applications.models import database, Category, ProductCategory, Product, Order, ProductOrder
from applications.roleDecorator import roleCheck

application = Flask(__name__)
application.config.from_object(Configuration)
jwt = JWTManager(application)


@application.route("/productStatistics", methods=["GET"])
@jwt_required()
@roleCheck(role="admin")
def productStatistics():
    sold = func.sum(ProductOrder.requested)
    waiting = func.sum(ProductOrder.requested - ProductOrder.received)

    query = Product.query.join(ProductOrder).group_by(Product.name) \
        .with_entities(Product.name, sold.label("sold"), waiting.label("waiting"))

    statistics = []

    for product in query:
        statistics.append(
            {
                "name": product.name,
                "sold": int(product.sold),
                "waiting": int(product.waiting)
            }
        )

    return jsonify({"statistics": statistics})


@application.route("/categoryStatistics", methods=["GET"])
@jwt_required()
@roleCheck(role="admin")
def categoryStatistics():
    categories = Category.query.all()

    dict = {}

    for category in categories:
        dict[category.name] = 0

    for product in Product.query.all():
        orders = product.orders
        for order in orders:
            productOrder = ProductOrder.query.filter(
                and_(ProductOrder.productId == product.id, ProductOrder.orderId == order.id)).first()
            for category in product.categories:
                dict[category.name] += productOrder.requested

    return jsonify({"statistics": [x[0] for x in sorted(dict.items(), key=lambda x: (-x[1], x[0]))]})

@application.route("/", methods=["GET"])
def index():
    return Response("Admin container up and running.")

if __name__ == "__main__":
    database.init_app(application)
    application.run(debug=True, host="0.0.0.0", port=5003)
