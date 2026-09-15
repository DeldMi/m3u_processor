import os
from functools import wraps
from flask import session, abort, redirect, url_for, request, current_app

ROLE_HIERARCHY = {
    "admin": 3,
    "editor": 2,
    "viewer": 1
}

def login_user(user_row: dict):
    session["user_id"] = user_row["id"]
    session["username"] = user_row["username"]
    session["role"] = user_row["role"]

def logout_user():
    session.clear()

def current_user():
    if "user_id" in session:
        return {"id": session["user_id"], "username": session["username"], "role": session["role"]}
    return None

def require_role(min_role: str):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = current_user()
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1].strip()
                from src.config import ConfigManager
                root_dir = os.path.abspath(os.path.join(current_app.root_path, ".."))
                cfg = ConfigManager(root_dir).get_all()
                if token and token == cfg.get("API_TOKEN"):
                    return f(*args, **kwargs)

            if not user:
                return redirect(url_for("auth_login"))
            if ROLE_HIERARCHY.get(user["role"], 0) < ROLE_HIERARCHY.get(min_role, 0):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator