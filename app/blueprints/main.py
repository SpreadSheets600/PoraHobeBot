from flask import Blueprint, render_template
from flask_dance.contrib.google import google
from ..auth import login_required

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
def index():
    return render_template("index.html")


@main_bp.route("/profile")
@login_required
def profile():
    resp = google.get("/oauth2/v2/userinfo")
    assert resp.ok, resp.text

    user_info = resp.json()
    return render_template("profile.html", user=user_info)


@main_bp.route("/logout")
@login_required
def logout():
    from flask import redirect, url_for
    google.token = None
    return redirect(url_for('main.index'))
