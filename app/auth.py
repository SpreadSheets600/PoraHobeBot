from functools import wraps
from flask import redirect, url_for
from flask_dance.contrib.google import google


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not google.authorized:
            return redirect(url_for("google.login"))
        return f(*args, **kwargs)

    return decorated_function
