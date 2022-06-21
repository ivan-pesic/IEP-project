from flask import Flask, request, Response, jsonify
from configuration import Configuration
from models import database, User, UserRole
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, create_refresh_token, get_jwt, \
    get_jwt_identity
from sqlalchemy import and_
import re
from roleDecorator import roleCheck

MSG = "message"
FIELD_MISSING = "Field {} is missing."
INVALID_FIELD = "Invalid {}."
ALREADY_EXISTS = "Email already exists."
INVALID_CREDENTIALS = "Invalid credentials."
UNKNOWN_USER = "Unknown user."

CUSTOMER = 2
MANAGER = 3

application = Flask(__name__)
application.config.from_object(Configuration)


def checkIfEmailIsValid(email):
    regex = "^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$"
    result = re.search(regex, email)
    if not result or len(email) > 256:
        return False
    return True


@application.route("/register", methods=["POST"])
def register():
    email = request.json.get("email", "")
    password = request.json.get("password", "")
    forename = request.json.get("forename", "")
    surname = request.json.get("surname", "")
    isCustomer = request.json.get("isCustomer", None)

    emailEmpty = len(email) == 0
    passwordEmpty = len(password) == 0
    forenameEmpty = len(forename) == 0
    surnameEmpty = len(surname) == 0
    isCustomerEmpty = isCustomer is None

    if forenameEmpty:
        return jsonify({MSG: FIELD_MISSING.format("forename")}), 400
    if surnameEmpty:
        return jsonify({MSG: FIELD_MISSING.format("surname")}), 400
    if emailEmpty:
        return jsonify({MSG: FIELD_MISSING.format("email")}), 400
    if passwordEmpty:
        return jsonify({MSG: FIELD_MISSING.format("password")}), 400
    if isCustomerEmpty:
        return jsonify({MSG: FIELD_MISSING.format("isCustomer")}), 400

    # check email
    if not checkIfEmailIsValid(email):
        return jsonify({MSG: INVALID_FIELD.format("email")}), 400
    # check password
    if (not re.search(".{8,256}", password)
            or not re.search("\d+", password)
            or not re.search("[a-z]+", password)
            or not re.search("[A-Z]+", password)):
        return jsonify({MSG: INVALID_FIELD.format("password")}), 400
    # check if user exists
    if User.query.filter(User.email == email).first() is not None:
        return jsonify({MSG: ALREADY_EXISTS}), 400

    # create user
    user = User(email=email, password=password, forename=forename, surname=surname)
    database.session.add(user)
    database.session.commit()

    roleId = CUSTOMER if isCustomer else MANAGER

    userRole = UserRole(userId=user.id, roleId=roleId)
    database.session.add(userRole)
    database.session.commit()

    return Response(status=200)


jwt = JWTManager(application)


@application.route("/login", methods=["POST"])
def login():
    email = request.json.get("email", "")
    password = request.json.get("password", "")

    emailEmpty = len(email) == 0
    passwordEmpty = len(password) == 0

    if emailEmpty:
        return jsonify({MSG: FIELD_MISSING.format("email")}), 400
    if passwordEmpty:
        return jsonify({MSG: FIELD_MISSING.format("password")}), 400
    if not checkIfEmailIsValid(email):
        return jsonify({MSG: INVALID_FIELD.format("email")}), 400
    if len(password) > 256:
        return jsonify({MSG: INVALID_FIELD.format("password")}), 400

    user = User.query.filter(and_(User.email == email, User.password == password)).first()

    if (not user):
        return jsonify({MSG: INVALID_CREDENTIALS}), 400

    additionalClaims = {
        "forename": user.forename,
        "surname": user.surname,
        "roles": [str(role) for role in user.roles]
    }

    accessToken = create_access_token(identity=user.email, additional_claims=additionalClaims)
    refreshToken = create_refresh_token(identity=user.email, additional_claims=additionalClaims)

    # return Response ( accessToken, status = 200 )
    return jsonify(accessToken=accessToken, refreshToken=refreshToken)


@application.route("/check", methods=["POST"])
@jwt_required()
def check():
    return "Token is valid!"


@application.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    refreshClaims = get_jwt()

    additionalClaims = {
        "forename": refreshClaims["forename"],
        "surname": refreshClaims["surname"],
        "roles": refreshClaims["roles"]
    }

    return jsonify(accessToken=create_access_token(identity=identity), additional_claims=additionalClaims)


@application.route("/delete", methods=["POST"])
@jwt_required()
@roleCheck(role="admin")
def delete():
    identity = get_jwt_identity()
    refreshClaims = get_jwt()

    email = request.json.get("email", "")
    emailEmpty = len(email) == 0

    if emailEmpty:
        return jsonify({MSG: FIELD_MISSING.format("email")}), 400
    if checkIfEmailIsValid(email):
        return jsonify({MSG: INVALID_FIELD.format("email")}), 400

    user = User.query.filter(User.email == email).first()

    if user is None:
        return jsonify({MSG: UNKNOWN_USER}), 400

    UserRole.query.filter(UserRole.id == user.id).delete()
    User.query.filter(User.email == email).delete()

    database.session.commit()

    return Response(status=200)


if (__name__ == "__main__"):
    database.init_app(application)
    application.run(debug=True, port=5002)
