from flask import Flask
from configuration import Configuration
from flask_migrate import Migrate, init, migrate, upgrade
from models import database, Role, UserRole, User
from sqlalchemy_utils import database_exists, create_database

application = Flask(__name__)
application.config.from_object(Configuration)

migrateObject = Migrate(application, database)

done = False

while not done:
    try:
        if not database_exists(application.config["SQLALCHEMY_DATABASE_URI"]):
            create_database(application.config["SQLALCHEMY_DATABASE_URI"])

        database.init_app(application)

        with application.app_context() as context:
            init()
            migrate(message="Production migration")
            upgrade()

            adminRole = Role(name="admin")
            customerRole = Role(name="customer")
            storekeeperRole = Role(name="storekeeper")

            database.session.add(adminRole)
            database.session.commit()
            database.session.add(customerRole)
            database.session.commit()
            database.session.add(storekeeperRole)
            database.session.commit()

            admin = User(forename="admin", surname="admin", email="admin@admin.com", password="1")
            database.session.add(admin)
            database.session.commit()
            adminUserRole = UserRole(userId=admin.id, roleId=adminRole.id)
            database.session.add(adminUserRole)
            database.session.commit()

            done = True
    except Exception as error:
        print(error)
