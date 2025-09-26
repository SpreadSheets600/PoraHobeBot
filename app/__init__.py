from flask_dance.contrib.google import make_google_blueprint
from flask_dance.consumer.storage.sqla import SQLAlchemyStorage
from flask_migrate import Migrate, upgrade
from flask_sqlalchemy import SQLAlchemy
from alembic.command import revision
from flask_login import LoginManager
from alembic.config import Config
from flask import Flask

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from .models import User

        return User.query.get(int(user_id))

    from .blueprints.main import main_bp

    app.register_blueprint(main_bp)

    from .models import OAuth

    google_bp = make_google_blueprint(
        client_id=app.config["GOOGLE_CLIENT_ID"],
        client_secret=app.config["GOOGLE_CLIENT_SECRET"],
        scope=[
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
            "openid",
        ],
        storage=SQLAlchemyStorage(OAuth, db.session),
    )
    app.register_blueprint(google_bp, url_prefix="/login")

    with app.app_context():
        config = Config("migrations/alembic.ini")
        revision(config, autogenerate=True, message="Auto migration")
        upgrade()

    return app
