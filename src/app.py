import os
import threading
import glob
import time
import shutil
import sqlite3
import sys
import re
import uuid
from collections import deque
from datetime import datetime

from flask import Flask, render_template, jsonify, request, redirect, url_for, send_from_directory, send_file
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from apscheduler.schedulers.background import BackgroundScheduler

from src.auth import login_user, logout_user, current_user, require_role
from src.config import ConfigManager
from src.core.scheduler import configure_scheduler
from src.domains.health.internet import check_internet_health as _check_internet_health
from src.domains.playlists.service import get_output_manifests as _get_output_manifests
from src.domains.sync.service import execute_health_check as _execute_health_check
from src.domains.sync.service import execute_pipeline as _execute_pipeline
from src.domains.authz.service import create_user as authz_create_user, update_user as authz_update_user, list_public_users, public_user, has_permission
from src.domains.monitoring.service import ResourceMonitor
from src.domains.monitoring.routes import register_monitoring_routes
from src.manager import PlaylistManager

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "frontend", "templates"), static_folder=os.path.join(BASE_DIR, "frontend", "static"))
REACT_DIR = os.path.join(BASE_DIR, "frontend", "react", "dist")
app.secret_key = ConfigManager(BASE_DIR).get_all().get("SECRET_KEY", "m3u_processor_secret_key_fixed")
manager = PlaylistManager(BASE_DIR)
scheduler = BackgroundScheduler(daemon=True)
PUBLIC_ONLY = os.getenv("PUBLIC_ONLY", "0") == "1"
if not PUBLIC_ONLY:
    scheduler.start()

PROCESS_STATE = {"status": "Ocioso", "total_canais": 0, "canais_online": 0, "canais_offline": 0, "manifestos": [], "ultimo_log": "Sistema pronto para execucao."}
PROCESS_LOGS = deque(maxlen=250)
PAUSE_REQUESTED = threading.Event()
STOP_REQUESTED = threading.Event()
ACTIVE_RUN_ID = None
NOTIFICATIONS = deque(maxlen=100)
RESOURCE_MONITOR = ResourceMonitor(history_size=120)
PROCESS_STATE["publication_mode"] = "NONE"
PIPELINE_LOCK = threading.Lock()
MIN_FREE_SPACE_BYTES = 512 * 1024 * 1024

PROCESS_LOGS.extend(manager.db.list_process_events(limit=250))
LAST_RUNS = manager.db.list_process_runs(limit=1)
if LAST_RUNS:
    last_run = LAST_RUNS[0]
    PROCESS_STATE.update({"status": last_run["status"] if last_run["status"] != "Executando..." else "Interrompido", "total_canais": last_run["total_canais"], "canais_online": last_run["canais_online"], "canais_offline": last_run["canais_offline"], "ultimo_log": last_run["last_message"] or PROCESS_STATE["ultimo_log"]})


def add_notification(level: str, title: str, message: str, source: str = "Execução", path: str = "", details: str = ""):
    NOTIFICATIONS.appendleft({
        "id": uuid.uuid4().hex,
        "level": level,
        "title": title,
        "message": message,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "path": path,
        "details": details,
    })


def add_process_log(message: str, level: str = "info", run_id=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    PROCESS_LOGS.appendleft({"timestamp": timestamp, "level": level, "message": message})
    try:
        manager.db.add_process_event(message, level, ACTIVE_RUN_ID if run_id is None else run_id)
    except (OSError, sqlite3.OperationalError):
        pass
    if level in {"success", "warning", "error"}:
        source = "Health Check" if any(token in message.lower() for token in ("health check", "verificação de canais", "internet")) else "Execução"
        add_notification(level, "Health Check" if source == "Health Check" else "Execução", message, source=source, path="/" if source == "Execução" else "/api/v1/health")


def has_sufficient_disk_space() -> bool:
    return shutil.disk_usage(BASE_DIR).free >= MIN_FREE_SPACE_BYTES


def update_log_state(message: str):
    PROCESS_STATE["ultimo_log"] = message
    add_process_log(message)


def check_internet_health() -> dict:
    return _check_internet_health(manager.config_mgr.get_all())


def get_output_manifests():
    return _get_output_manifests(manager)


def execute_health_check():
    return _execute_health_check(manager=manager, process_state=PROCESS_STATE, pipeline_lock=PIPELINE_LOCK)


def execute_pipeline(publication_mode=None):
    mode = (publication_mode or manager.config_mgr.get_all().get("SYNC_PUBLICATION_MODE", "NONE")).upper()
    return _execute_pipeline(manager=manager, process_state=PROCESS_STATE, process_logs=PROCESS_LOGS, pause_requested=PAUSE_REQUESTED, stop_requested=STOP_REQUESTED, pipeline_lock=PIPELINE_LOCK, state={"active_run_id": ACTIVE_RUN_ID}, min_free_space_bytes=MIN_FREE_SPACE_BYTES, update_log=add_process_log, publication_mode=mode)


def setup_scheduler():
    configure_scheduler(scheduler, manager, execute_pipeline, execute_health_check)


if not PUBLIC_ONLY:
    setup_scheduler()

register_monitoring_routes(app, manager, PROCESS_STATE, PROCESS_LOGS, NOTIFICATIONS, RESOURCE_MONITOR, add_notification=add_notification)


@app.before_request
def restrict_public_server():
    if PUBLIC_ONLY and not (request.path.startswith("/playlist/") or request.path.startswith("/epg/")):
        return jsonify({"error": "Apenas links públicos estão disponíveis nesta porta."}), 404


@app.context_processor
def inject_user():
    return dict(user=current_user())


def serve_react_app():
    index_path = os.path.join(REACT_DIR, "index.html")
    if os.path.exists(index_path):
        return send_file(index_path)
    return None


@app.route("/login", methods=["GET", "POST"])
def auth_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with manager.db.get_connection() as conn:
            user = conn.execute("SELECT * FROM users WHERE username = ?;", (username,)).fetchone()
            if user is not None:
                keys = user.keys()
                is_active = bool(user["active"]) if "active" in keys else True
                password_hash = user["password_hash"] if "password_hash" in keys else ""
                if is_active and password_hash and check_password_hash(password_hash, password):
                    login_user(dict(user))
                    return redirect(url_for("view_dashboard"))
        return render_template("login.html", error="Credenciais invalidas.")
    react_app = serve_react_app()
    if react_app:
        return react_app
    return render_template("login.html")


@app.route("/logout")
def auth_logout():
    logout_user()
    return redirect(url_for("auth_login"))


@app.route("/")
@require_role("viewer")
def view_dashboard():
    react_app = serve_react_app()
    if react_app:
        return react_app
    return render_template("dashboard.html")


@app.route("/api/me")
def api_me():
    user = current_user()
    if not user:
        return jsonify({"user": None}), 401
    return jsonify({"user": user})


@app.route("/app-assets/<path:filename>")
def react_assets(filename):
    return send_from_directory(REACT_DIR, filename)


@app.route("/playlists")
@require_role("viewer")
def view_playlists():
    react_app = serve_react_app()
    if react_app:
        return react_app
    return render_template("playlists.html")


@app.route("/channels")
@require_role("viewer")
def view_channels():
    react_app = serve_react_app()
    if react_app:
        return react_app
    return render_template("channels.html")
