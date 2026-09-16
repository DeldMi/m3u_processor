import os
from datetime import datetime
from functools import wraps
from flask import session, abort, redirect, url_for, request, current_app

ROLE_HIERARCHY = {"admin": 3, "editor": 2, "viewer": 1}

ROUTE_PERMISSIONS = {
    "api_status": ("dashboard", "view"), "api_internet_health": ("health", "view"),
    "api_get_logs": ("logs", "view"), "api_get_history": ("logs", "view"),
    "api_pause_sync": ("sync", "execute"), "api_stop_sync": ("sync", "execute"),
    "api_get_playlists": ("playlists", "view"), "api_delete_playlists": ("playlists", "delete"),
    "api_rename_playlist": ("playlists", "edit"), "api_get_channels": ("channels", "view"),
    "api_channel_options": ("channels", "view"), "api_upload_channel_logo": ("channels", "edit"),
    "api_users": ("users", "view"), "api_update_user": ("users", "edit"),
    "api_update_profile": ("users", "edit"), "api_admin_restart": ("system", "admin"),
    "api_admin_shutdown": ("system", "admin"), "api_update_channel": ("channels", "edit"),
    "api_generate_custom_playlist": ("playlists", "create"), "api_toggle_channel_status": ("channels", "edit"),
    "api_toggle_autoremove": ("channels", "edit"), "api_trigger_sync": ("sync", "execute"),
    "api_save_config": ("settings", "admin"), "api_get_config": ("settings", "view"),
    "view_users": ("users", "view"), "view_settings": ("settings", "view"),
    "view_channels": ("channels", "view"), "view_playlists": ("playlists", "view"),
    "view_dashboard": ("dashboard", "view"),
}

# Rotas que aceitam mais de um método precisam de uma permissão diferente por operação.
ROUTE_METHOD_PERMISSIONS = {
    "api_users": {
        "GET": ("users", "view"),
        "POST": ("users", "create"),
    },
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
            ConfigManager(root_dir).get_all()
            db = Database(os.path.join(root_dir, "data", "app.db"))
        except Exception:
            logout_user()
            return None
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
        logout_user()
        return None


def _api_token_is_valid() -> bool:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return False
    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        return False
    from src.config import ConfigManager
    root_dir = os.path.abspath(os.path.join(current_app.root_path, ".."))
    configured = str(ConfigManager(root_dir).get_all().get("API_TOKEN") or "").strip()
    return bool(configured and token == configured)


def _permission_denied(permission):
    if request.path.startswith("/api/"):
        return {"error": "Permissão insuficiente", "resource": permission[0], "action": permission[1]}, 403
    abort(403)


def _route_permission(endpoint_name: str):
    method_permissions = ROUTE_METHOD_PERMISSIONS.get(endpoint_name)
    if method_permissions:
        return method_permissions.get(request.method)
    return ROUTE_PERMISSIONS.get(endpoint_name)


def require_role(min_role: str):
    """Compatibilidade legada: rotas mapeadas usam autorização granular por método."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = current_user()
            permission = _route_permission(f.__name__)
            if not user:
                if _api_token_is_valid() and request.path.startswith("/api/") and permission and permission[0] in {"dashboard", "health", "logs", "playlists", "channels", "sync", "settings", "public_files"}:
                    return f(*args, **kwargs)
                if request.path.startswith("/api/"):
                    return {"error": "Não autenticado"}, 401
                return redirect(url_for("auth_login"))

            if permission:
                from src.domains.authz.service import has_permission
                from src.app import manager
                if not has_permission(manager.db, int(user["id"]), user["role"], *permission):
                    return _permission_denied(permission)
            elif ROLE_HIERARCHY.get(user.get("role"), 0) < ROLE_HIERARCHY.get(min_role, 0):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_permission(resource: str, action: str):
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
                return _permission_denied((resource, action))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
