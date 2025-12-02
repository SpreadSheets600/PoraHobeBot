from flask_dance.contrib.google import google
from flask import redirect, url_for
from functools import wraps


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not google.authorized:
            return redirect(url_for("google.login"))

        return f(*args, **kwargs)

    return decorated_function
