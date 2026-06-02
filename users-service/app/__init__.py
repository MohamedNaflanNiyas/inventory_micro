import time
from sqlalchemy.exc import OperationalError
from flask import Flask
from .config import Config
from .routes import db, users_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    # Retry loop to wait for postgres to be ready
    with app.app_context():
        retries = 5
        while retries > 0:
            try:
                db.create_all()
                print("Succesfully connected to DB")
                break
            except OperationalError:
                retries -= 1
                print(f"DB not ready yet. Retrying in 5 seconds....({retries})")
                time.sleep(5)
        if retries ==0:
            raise Exception("Unable to connect to DB")


        app.register_blueprint(users_bp)
        return app
