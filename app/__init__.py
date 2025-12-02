from typing import Optional

from flask_dance.consumer import oauth_authorized, oauth_error
from flask_dance.contrib.discord import make_discord_blueprint
from flask_dance.contrib.google import make_google_blueprint
from flask import Flask, flash, redirect, url_for
from flask_login import login_user
import requests

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
    )
    app.register_blueprint(google_bp, url_prefix="/login")

    discord_bp = make_discord_blueprint(
        client_secret=app.config["DISCORD_CLIENT_SECRET"],
        scope=["identify", "email", "guilds.join"],
        client_id=app.config["DISCORD_CLIENT_ID"],
        prompt="consent",
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
                f"{provider_name.title()} Account Must Include A Public Email.", "error"
            )
            return False

        oauth = OAuth.query.filter_by(
            provider_user_id=provider_user_id,
            provider=provider_name,
        ).one_or_none()

        if oauth:
            user = oauth.user
            oauth.token = token
        else:
            user = User.query.filter_by(email=email).one_or_none()

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

    def _join_discord_guild(discord_user_id: str, access_token: str):
        bot_token = app.config.get("DISCORD_BOT_TOKEN")
        guild_id = app.config.get("DISCORD_GUILD_ID")

        if not guild_id or not bot_token:
            return

        url = f"https://discord.com/api/v10/guilds/{guild_id}/members/{discord_user_id}"
        headers = {"Authorization": f"Bot {bot_token}"}
        payload = {"access_token": access_token}

        try:
            response = requests.put(url, headers=headers, json=payload, timeout=10)

        except requests.RequestException as exc:
            app.logger.warning("Failed To Add User To Discord Guild: %s", exc)
            return

        if response.status_code not in (200, 201, 204):
            app.logger.warning(
                "Discord Guild Join Failed (%s): %s",
                response.status_code,
                response.text,
            )

    @oauth_authorized.connect_via(google_bp)
    def google_logged_in(blueprint, token):
        if not token:
            flash("Google Authentication Failed.", "error")
            return False

        resp = blueprint.session.get("/oauth2/v2/userinfo")

        if not resp.ok:
            flash("Unable To Read Google Profile Information.", "error")
            return False

        google_info = resp.json()
        google_user_id = str(google_info["id"])

        return _finish_login(
            provider_user_id=google_user_id,
            email=google_info.get("email"),
            provider_name=blueprint.name,
            name=google_info.get("name"),
            token=token,
        )

    @oauth_authorized.connect_via(discord_bp)
    def discord_logged_in(blueprint, token):
        if not token:
            flash("Discord Authentication Failed.", "error")
            return False

        resp = blueprint.session.get("/api/users/@me")
        if not resp.ok:
            flash("Unable To Read Discord Profile Information.", "error")
            return False

        discord_info = resp.json()
        discord_user_id = str(discord_info["id"])

        redirect_response = _finish_login(
            name=discord_info.get("username"),
            provider_user_id=discord_user_id,
            email=discord_info.get("email"),
            provider_name=blueprint.name,
            token=token,
        )

        if redirect_response and token.get("access_token"):
            _join_discord_guild(discord_user_id, token["access_token"])

        return redirect_response

    @oauth_error.connect_via(google_bp)
    @oauth_error.connect_via(discord_bp)
    def oauth_error_handler(blueprint, error, error_description=None, error_uri=None):
        message = f"{blueprint.name.title()} OAuth error: {error_description or error}."
        app.logger.error(message)

        flash(message, "error")

    return app
