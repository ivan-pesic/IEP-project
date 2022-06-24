from flask import Flask, request, Response, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, create_refresh_token, get_jwt, \
    get_jwt_identity
from redis.client import Redis
from sqlalchemy import and_
import re
import io
import csv

from applications.configuration import Configuration
from applications.models import database
from applications.roleDecorator import roleCheck

application = Flask(__name__)
application.config.from_object(Configuration)
jwt = JWTManager(application)

MSG = "message"
FILE_MISSING = "Field file is missing."
INCORRECT_NUMBER_OF_VALUES = "Incorrect number of values on line {}."
INCORRECT_QUANTITY = "Incorrect quantity on line {}."
INCORRECT_PRICE = "Incorrect price on line {}."


@application.route("/update", methods=["POST"])
@jwt_required()
@roleCheck(role="storekeeper")
def updateProducts():
    if "file" not in request.files:
        return jsonify({MSG: FILE_MISSING}), 400

    content = request.files["file"].stream.read().decode("utf-8")
    stream = io.StringIO(content)
    reader = csv.reader(stream)

    i = 0
    for row in reader:
        if len(row) != 4:
            return jsonify({MSG: INCORRECT_NUMBER_OF_VALUES.format(i)}), 400
        try:
            quantity = int(row[2])
        except ValueError:
            return jsonify({MSG: INCORRECT_QUANTITY.format(i)}), 400
        if quantity < 1:
            return jsonify({MSG: INCORRECT_QUANTITY.format(i)}), 400
        try:
            price = float(row[3])
        except ValueError:
            return jsonify({MSG: INCORRECT_PRICE.format(i)}), 400
        if price <= 0:
            return jsonify({MSG: INCORRECT_PRICE.format(i)}), 400
        i = i + 1

    stream.seek(0)
    reader = csv.reader(stream)

    with Redis(host=Configuration.REDIS_HOST) as redis:
        for row in reader:
            redis.rpush(Configuration.REDIS_PRODUCTS_LIST, row[0] + "," + row[1] + "," + row[2] + "," + row[3])

    return Response(status=200)


if (__name__ == "__main__"):
    database.init_app(application)
    application.run(debug=True, port=5001)
