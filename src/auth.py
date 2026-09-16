import os
from datetime import datetime
from functools import wraps
from flask import session, abort, redirect, url_for, request, current_app

ROLE_HIERARCHY = {"admin": 3, "editor": 2, "viewer": 1}

# Compatibilidade das rotas antigas com o novo modelo Recurso × Ação.
ROUTE_PERMISSIONS = {
    "api_status": ("dashboard", "view"),
    "api_internet_health": ("health", "view"),
    "api_get_logs": ("logs", "view"),
    "api_get_history": ("logs", "view"),
    "api_pause_sync": ("sync", "execute"),
    "api_stop_sync": ("sync", "execute"),
    "api_get_playlists": ("playlists", "view"),
    "api_delete_playlists": ("playlists", "delete"),
    "api_rename_playlist": ("playlists", "edit"),
    "api_get_channels": ("channels", "view"),
    "api_channel_options": ("channels", "view"),
    "api_upload_channel_logo": ("channels", "edit"),
    "api_users": ("users", "view"),
    "api_update_user": ("users", "edit"),
    "api_update_profile": ("users", "edit"),
    "api_admin_restart": ("system", "admin"),
    "api_admin_shutdown": ("system", "admin"),
    "api_update_channel": ("channels", "edit"),
    "api_generate_custom_playlist": ("playlists", "create"),
    "api_toggle_channel_status": ("channels", "edit"),
    "api_toggle_autoremove": ("channels", "edit"),
    "api_trigger_sync": ("sync", "execute"),
    "api_save_config": ("settings", "admin"),
    "api_get_config": ("settings", "view"),
    "view_users": ("users", "view"),
    "view_settings": ("settings", "view"),
    "view_channels": ("channels", "view"),
    "view_playlists": ("playlists", "view"),
    "view_dashboard": ("dashboard", "view"),
}


def login_user(user_row: dict):
    session.clear()
    session["user_id"] = user_row["id"]
    session["username"] = user_row["username"]
    session["role"] = user_row["role"]


def logout_user():
    session.clear()


def _authz(db):
    from src.domains.authz.service import ensure_schema
    ensure_schema(db)
    return __import__("src.domains.authz.service", fromlist=["has_permission", "public_user"])


def current_user(db=None):
    if "user_id" not in session:
        return None
    if db is None:
        try:
            from src.db import Database
            from src.config import ConfigManager
            root_dir = os.path.abspath(os.path.join(current_app.root_path, ".."))
            cfg = ConfigManager(root_dir).get_all()
            db = Database(os.path.join(root_dir, "data", "app.db"))
        except Exception:
            return {"id": session["user_id"], "username": session["username"], "role": session["role"]}
    try:
        service = _authz(db)
        user = service.public_user(db, int(session["user_id"]))
        if not user or not user.get("active", 1):
            logout_user()
            return None
        expires = user.get("expires_at")
        if expires:
            try:
                if datetime.fromisoformat(str(expires).replace("Z", "+00:00")).replace(tzinfo=None) < datetime.now():
                    logout_user()
                    return None
            except ValueError:
                pass
        session["username"] = user["username"]
        session["role"] = user["role"]
        return user
    except Exception:
        return {"id": session["user_id"], "username": session["username"], "role": session["role"]}


def require_role(min_role: str):
    """Compatibilidade legada, agora complementada por autorização granular."""
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
                if request.path.startswith("/api/"):
                    return {"error": "Não autenticado"}, 401
                return redirect(url_for("auth_login"))
            if ROLE_HIERARCHY.get(user.get("role"), 0) < ROLE_HIERARCHY.get(min_role, 0):
                abort(403)
            permission = ROUTE_PERMISSIONS.get(f.__name__)
            if permission:
                from src.domains.authz.service import has_permission
                from src.app import manager
                if not has_permission(manager.db, int(user["id"]), user["role"], *permission):
                    if request.path.startswith("/api/"):
                        return {"error": "Permissão insuficiente", "resource": permission[0], "action": permission[1]}, 403
                    abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_permission(resource: str, action: str):
    """Autoriza por recurso/ação; falha fechado para usuários autenticados."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = current_user()
            if not user:
                if request.path.startswith("/api/"):
                    return {"error": "Não autenticado"}, 401
                return redirect(url_for("auth_login"))
            from src.domains.authz.service import has_permission
            from src.app import manager
            if not has_permission(manager.db, int(user["id"]), user["role"], resource, action):
                if request.path.startswith("/api/"):
                    return {"error": "Permissão insuficiente", "resource": resource, "action": action}, 403
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
