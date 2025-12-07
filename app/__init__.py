from typing import Optional

from flask import Flask, flash, redirect, url_for
from flask_dance.consumer import oauth_authorized, oauth_error
from flask_dance.contrib.discord import make_discord_blueprint
from flask_dance.contrib.google import make_google_blueprint
from flask_login import current_user, login_user

from .extensions import db, login_manager, migrate
from .models import OAuth, User


def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "main.login"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from .blueprints.main import main_bp

    app.register_blueprint(main_bp)

    google_bp = make_google_blueprint(
        client_id=app.config["GOOGLE_CLIENT_ID"],
        client_secret=app.config["GOOGLE_CLIENT_SECRET"],
        scope=[
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
            "openid",
        ],
        redirect_url="/login/google/authorized",
        reprompt_consent=True,
    )
    app.register_blueprint(google_bp, url_prefix="/login")

    discord_bp = make_discord_blueprint(
        client_id=app.config["DISCORD_CLIENT_ID"],
        client_secret=app.config["DISCORD_CLIENT_SECRET"],
        scope=["identify", "email"],
        redirect_url="/login/discord/authorized",
    )
    app.register_blueprint(discord_bp, url_prefix="/login")

    def _finish_login(
        provider_name: str,
        provider_user_id: str,
        email: Optional[str],
        name: Optional[str],
        token: dict,
    ):
        if not email:
            flash(
                f"{provider_name.title()} Account Must Contain A Public Email.", "error"
            )
            return False

        if current_user.is_authenticated:
            user = current_user
            oauth = OAuth.query.filter_by(
                provider=provider_name, provider_user_id=provider_user_id
            ).first()

            if not oauth:
                oauth = OAuth(
                    provider=provider_name,
                    provider_user_id=provider_user_id,
                    token=token,
                    user_id=user.id,
                )
                db.session.add(oauth)
            else:
                oauth.token = token

            db.session.commit()
            flash(f"{provider_name.title()} Account Linked!", "success")
            return redirect(url_for("main.settings"))

        oauth = OAuth.query.filter_by(
            provider=provider_name,
            provider_user_id=provider_user_id,
        ).first()

        if oauth:
            user = oauth.user
            oauth.token = token
        else:
            user = User.query.filter_by(email=email).first()
            if not user:
                user = User(name=name or email.split("@")[0], email=email)
                db.session.add(user)
                db.session.flush()

            oauth = OAuth(
                provider=provider_name,
                provider_user_id=provider_user_id,
                token=token,
                user=user,
            )
            db.session.add(oauth)

        db.session.commit()

        login_user(user)
        flash(f"Signed In With {provider_name.title()}", "success")
        return redirect(url_for("main.index"))

    @oauth_authorized.connect_via(google_bp)
    def google_logged_in(blueprint, token):
        if not token:
            flash("Google Authentication Ffailed.", "error")
            return False

        resp = blueprint.session.get("/oauth2/v2/userinfo")
        if not resp.ok:
            flash("Failed To load Google Profile.", "error")
            return False

        info = resp.json()
        google_user_id = str(info["id"])

        if "refresh_token" in token:
            existing = OAuth.query.filter_by(
                provider=blueprint.name, provider_user_id=google_user_id
            ).first()
            if existing:
                existing.token["refresh_token"] = token["refresh_token"]

        return _finish_login(
            provider_name=blueprint.name,
            provider_user_id=google_user_id,
            email=info.get("email"),
            name=info.get("name"),
            token=token,
        )

    @oauth_authorized.connect_via(discord_bp)
    def discord_logged_in(blueprint, token):
        if not token:
            flash("Discord Authentication Failed.", "error")
            return False

        resp = blueprint.session.get("/api/users/@me")
        if not resp.ok:
            flash("Failed To Load Discord Profile.", "error")
            return False

        info = resp.json()
        discord_user_id = str(info["id"])

        response = _finish_login(
            provider_name=blueprint.name,
            provider_user_id=discord_user_id,
            email=info.get("email"),
            name=info.get("username"),
            token=token,
        )

        return response

    @oauth_error.connect_via(google_bp)
    @oauth_error.connect_via(discord_bp)
    def oauth_error_handler(blueprint, error, error_description=None, error_uri=None):
        message = f"{blueprint.name.title()} OAuth error: {error_description or error}"
        app.logger.error(message)
        flash(message, "error")

    return app
