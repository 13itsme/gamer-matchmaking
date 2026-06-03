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

    from app.routes.auth import auth_bp
    from app.routes.profile import profile_bp
    from app.routes.games import games_bp
    from app.routes.invitations import invitations_bp
    from app.routes.chat import chat_bp
    from app.routes.ratings import ratings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(games_bp)
    app.register_blueprint(invitations_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(ratings_bp)

    from app.sockets import events
    from app.models import user, profile, game, user_game, invitation, message, trust_rating, trust_score

    return app
