import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate

from app.config import get_config

db = SQLAlchemy()
socketio = SocketIO()
bcrypt = Bcrypt()
migrate = Migrate()


def create_app():
    app = Flask(__name__)

    app.config.from_object(get_config())

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(
        app,
        async_mode="threading",
        cors_allowed_origins="*",
        logger=app.config["DEBUG"],
        engineio_logger=app.config["DEBUG"]
    )

    """
     ***
     Here i'll add all routes 
     ***
    """
    return app
