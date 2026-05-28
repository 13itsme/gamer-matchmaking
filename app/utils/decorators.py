from functools import wraps
from flask import session, redirect, url_for, request, jsonify


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"error": "You must be logged in", "redirect": "/login"}), 401
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)

    return decorated_function


def guest_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" in session:
            return redirect(url_for("games.index"))
        return f(*args, **kwargs)

    return decorated_function


def get_current_user():
    from app.models.user import User
    user_id = session.get("user_id")
    if user_id:
        return User.query.get(user_id)
    return None
