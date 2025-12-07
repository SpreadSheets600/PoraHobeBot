from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required, logout_user
from flask_dance.contrib.discord import discord
from flask_dance.contrib.google import google

from app.models import Note

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    return render_template("login.html")


@main_bp.route("/profile")
@login_required
def profile():
    def _safe_json(client, endpoint):
        if not client.authorized:
            return None

        response = client.get(endpoint)
        return response.json() if response.ok else None

    google_profile = _safe_json(google, "/oauth2/v2/userinfo")
    discord_profile = _safe_json(discord, "/api/users/@me")

    # Get user stats
    total_uploads = Note.query.filter_by(user_id=current_user.id).count()
    recent_uploads = (
        Note.query.filter_by(user_id=current_user.id)
        .order_by(Note.created_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "profile.html",
        user=current_user,
        google_profile=google_profile,
        discord_profile=discord_profile,
        total_uploads=total_uploads,
        recent_uploads=recent_uploads,
    )


@main_bp.route("/logout")
@login_required
def logout():
    logout_user()

    return redirect(url_for("main.login"))
