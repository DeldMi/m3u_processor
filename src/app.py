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
@app.route("/assets/<path:filename>")
def react_assets(filename):
    """Serve os assets do build React nos dois prefixes usados historicamente.

    Builds anteriores usavam /assets enquanto o Flask passou a publicar a
    SPA em /app-assets. Manter os dois caminhos evita que uma instalação
    com dist antigo devolva o index.html como JavaScript (erro MIME).
    """
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


@app.route("/users")
@require_role("admin")
def view_users():
    react_app = serve_react_app()
    if react_app:
        return react_app
    return render_template("users.html", users=list_public_users(manager.db))


@app.route("/settings")
@require_role("admin")
def view_settings():
    react_app = serve_react_app()
    if react_app:
        return react_app
    return render_template("settings.html", config=manager.config_mgr.get_all())


@app.route("/settings/<path:subpath>")
@require_role("admin")
def view_settings_subpath(subpath):
    """Serve subseções da SPA quando acessadas diretamente pelo Flask."""
    react_app = serve_react_app()
    if react_app:
        return react_app
    return render_template("settings.html", config=manager.config_mgr.get_all())


@app.route("/api/status")
@require_role("viewer")
def get_status():
    user = current_user(manager.db)
    data = {"status": PROCESS_STATE["status"]}
    if user and has_permission(manager.db, int(user["id"]), user["role"], "dashboard", "view"):
        data.update({"total_canais": PROCESS_STATE["total_canais"], "canais_online": PROCESS_STATE["canais_online"], "canais_offline": PROCESS_STATE["canais_offline"]})
    if user and has_permission(manager.db, int(user["id"]), user["role"], "channels", "view"):
        channels = manager.db.list_channels()
        if channels:
            data["total_canais"] = len(channels)
            data["canais_online"] = sum(channel.get("status") == "online" for channel in channels)
            data["canais_offline"] = sum(channel.get("status") == "offline" for channel in channels)
            data["canais_desconhecidos"] = sum(channel.get("status") == "desconhecido" for channel in channels)
    if user and has_permission(manager.db, int(user["id"]), user["role"], "playlists", "view"):
        data["manifestos"] = get_output_manifests()
        PROCESS_STATE["manifestos"] = data["manifestos"]
    if user and has_permission(manager.db, int(user["id"]), user["role"], "logs", "view"):
        data["ultimo_log"] = PROCESS_STATE["ultimo_log"]
        data["logs"] = list(PROCESS_LOGS)
        data["log_count"] = len(PROCESS_LOGS)
        data["historico"] = manager.db.list_process_runs(limit=20)
    if user and has_permission(manager.db, int(user["id"]), user["role"], "sync", "view"):
        data["sync"] = {"status": PROCESS_STATE["status"], "active": PROCESS_STATE["status"] in ("Executando...", "Pausado")}
    return jsonify(data)


@app.route("/api/v1/internet-health")
@require_role("viewer")
def api_internet_health():
    return jsonify(check_internet_health())


@app.route("/api/v1/logs")
@require_role("viewer")
def api_get_logs():
    return jsonify(manager.db.list_process_events(limit=1000))


@app.route("/api/v1/history")
@require_role("viewer")
def api_get_history():
    return jsonify(manager.db.list_process_runs(limit=100))


@app.route("/api/v1/sync/pause", methods=["POST"])
@require_role("editor")
def api_pause_sync():
    if PROCESS_STATE["status"] not in ("Executando...", "Pausado"):
        return jsonify({"status": "inativo"}), 409
    if PAUSE_REQUESTED.is_set():
        PAUSE_REQUESTED.clear(); PROCESS_STATE["status"] = "Executando..."; add_process_log("Execução retomada pelo usuário."); return jsonify({"status": "retomado"})
    PAUSE_REQUESTED.set(); PROCESS_STATE["status"] = "Pausado"; add_process_log("Execução pausada pelo usuário.", "warning"); return jsonify({"status": "pausado"})


@app.route("/api/v1/sync/stop", methods=["POST"])
@require_role("editor")
def api_stop_sync():
    if PROCESS_STATE["status"] not in ("Executando...", "Pausado"):
        return jsonify({"status": "inativo"}), 409
    STOP_REQUESTED.set(); PAUSE_REQUESTED.clear(); add_process_log("Interrupção solicitada pelo usuário.", "warning"); return jsonify({"status": "interrupcao_solicitada"})


@app.route("/api/v1/playlists")
@require_role("viewer")
def api_get_playlists():
    manifests = get_output_manifests(); PROCESS_STATE["manifestos"] = manifests
    return jsonify({"status": PROCESS_STATE["status"], "manifestos": manifests})


@app.route("/api/v1/playlists", methods=["DELETE"])
@require_role("editor")
def api_delete_playlists():
    names = (request.json or {}).get("m3u_names", [])
    deleted = []
    for m3u_name in names:
        if not isinstance(m3u_name, str) or not m3u_name.startswith("playlist_") or not m3u_name.endswith(".m3u"):
            continue
        m3u_path = os.path.join(manager.output_dir, os.path.basename(m3u_name))
        xml_name = os.path.splitext(os.path.basename(m3u_name))[0].replace("playlist_", "epg_") + ".xml"
        xml_path = os.path.join(manager.output_dir, xml_name)
        for file_path in (m3u_path, xml_path):
            try: os.remove(file_path)
            except FileNotFoundError: pass
        deleted.append(os.path.basename(m3u_name))
    PROCESS_STATE["manifestos"] = get_output_manifests(); add_process_log(f"Removida(s) {len(deleted)} lista(s) publicada(s).", "warning")
    return jsonify({"status": "removido", "deleted": deleted})


@app.route("/api/v1/playlists/<path:m3u_name>", methods=["PATCH"])
@require_role("editor")
def api_rename_playlist(m3u_name):
    old_name = os.path.basename(m3u_name); new_label = str((request.json or {}).get("name", "")).strip()
    match = re.fullmatch(r"playlist(?:_[A-Za-z0-9_-]+)?_parte_(\d{2})\.m3u", old_name)
    safe_label = re.sub(r"[^a-zA-Z0-9_-]+", "_", new_label).strip("_-")
    if not match or not safe_label: return jsonify({"error": "Nome ou lista inválida"}), 400
    old_xml = os.path.splitext(old_name)[0].replace("playlist_", "epg_") + ".xml"
    new_name = f"playlist_{safe_label}_parte_{match.group(1)}.m3u"; new_xml = f"epg_{safe_label}_parte_{match.group(1)}.xml"
    old_m3u_path = os.path.join(manager.output_dir, old_name); old_xml_path = os.path.join(manager.output_dir, old_xml)
    new_m3u_path = os.path.join(manager.output_dir, new_name); new_xml_path = os.path.join(manager.output_dir, new_xml)
    if not os.path.isfile(old_m3u_path) or not os.path.isfile(old_xml_path): return jsonify({"error": "Lista ou XML não encontrado"}), 404
    if old_name != new_name and (os.path.exists(new_m3u_path) or os.path.exists(new_xml_path)): return jsonify({"error": "Já existe uma lista com esse nome"}), 409
    with open(old_m3u_path, "r", encoding="utf-8", errors="ignore") as playlist_file: content = playlist_file.read().replace(f"/epg/{old_xml}", f"/epg/{new_xml}")
    with open(old_m3u_path, "w", encoding="utf-8") as playlist_file: playlist_file.write(content)
    os.replace(old_m3u_path, new_m3u_path); os.replace(old_xml_path, new_xml_path); PROCESS_STATE["manifestos"] = get_output_manifests(); add_process_log(f"Lista renomeada para {new_name}.", "success")
    return jsonify({"status": "atualizado", "m3u_name": new_name, "xml_name": new_xml})


@app.route("/api/v1/channels", methods=["GET"])
@require_role("viewer")
def api_get_channels():
    country = request.args.get("country"); city = request.args.get("city"); category = request.args.get("category"); status = request.args.get("status")
    channels = manager.db.list_channels(country, category, status, request.args.get("search", ""), request.args.get("sort", "id"), request.args.get("direction", "asc"))
    if city and city != "todos": channels = [channel for channel in channels if channel.get("city") == city]
    return jsonify(channels)


@app.route("/api/v1/channels/options")
@require_role("viewer")
def api_channel_options(): return jsonify(manager.db.channel_filter_options())


@app.route("/api/v1/channels/logo", methods=["POST"])
@require_role("editor")
def api_upload_channel_logo():
    image = request.files.get("image")
    if not image or not image.filename: return jsonify({"error": "Nenhuma imagem foi enviada"}), 400
    allowed = {".png", ".jpg", ".jpeg", ".webp", ".gif"}; extension = os.path.splitext(image.filename)[1].lower()
    if extension not in allowed: return jsonify({"error": "Formato de imagem não permitido"}), 400
    upload_dir = os.path.join(BASE_DIR, "frontend", "static", "uploads"); os.makedirs(upload_dir, exist_ok=True)
    filename = f"channel_{int(time.time() * 1000)}_{secure_filename(image.filename)}"; image.save(os.path.join(upload_dir, filename)); return jsonify({"url": f"/static/uploads/{filename}"})


@app.route("/api/v1/users", methods=["GET", "POST"])
@require_role("admin")
def api_users():
    if request.method == "POST":
        data = dict(request.get_json(silent=True) or request.form)
        actor = current_user(manager.db)
        if actor and not has_permission(manager.db, int(actor["id"]), actor["role"], "users", "admin"):
            # Criar conta não permite que um operador se autoeleve nem delegue permissões administrativas.
            data["role"] = "viewer"
            data.pop("permissions", None)
        user = authz_create_user(manager.db, data)
        if not user: return jsonify({"error": "Usuário inválido, senha fraca ou login já existente"}), 400
        return jsonify(user), 201
    return jsonify(list_public_users(manager.db))


@app.route("/api/v1/users/<int:user_id>", methods=["PATCH"])
@require_role("admin")
def api_update_user(user_id):
    data = dict(request.get_json(silent=True) or {})
    actor = current_user(manager.db)
    if actor and not has_permission(manager.db, int(actor["id"]), actor["role"], "users", "admin"):
        data.pop("role", None)
        data.pop("permissions", None)
    user = authz_update_user(manager.db, user_id, data)
    if not user: return jsonify({"error": "Usuário não encontrado, inválido ou sem alterações"}), 400
    return jsonify(user)


@app.route("/api/profile", methods=["PATCH"])
def api_update_profile():
    user = current_user()
    if not user: return jsonify({"error": "Não autenticado"}), 401
    values = request.json or {}
    allowed = {"username", "display_name", "full_name", "email", "avatar", "phone", "description", "department", "password"}
    values = {key: value for key, value in values.items() if key in allowed}
    if "role" in request.json or "active" in request.json or "permissions" in request.json:
        return jsonify({"error": "Alteração de papel, status ou permissões exige administração."}), 403
    updated = authz_update_user(manager.db, int(user["id"]), values)
    if not updated: return jsonify({"error": "Perfil inválido ou sem alterações"}), 400
    return jsonify({"status": "atualizado", "user": updated})


@app.route("/api/admin/restart", methods=["POST"])
@require_role("admin")
def api_admin_restart():
    def restart(): os.execv(sys.executable, [sys.executable, "-m", "src.app"])
    threading.Timer(0.25, restart).start(); return jsonify({"status": "reiniciando"})


@app.route("/api/admin/shutdown", methods=["POST"])
@require_role("admin")
def api_admin_shutdown():
    threading.Timer(0.25, os._exit, args=(0,)).start(); return jsonify({"status": "desligando"})


@app.route("/api/v1/channels/<int:ch_id>", methods=["PATCH"])
@require_role("editor")
def api_update_channel(ch_id):
    if not manager.db.update_channel(ch_id, request.json or {}): return jsonify({"error": "Canal nao encontrado ou sem campos validos"}), 404
    return jsonify(next(item for item in manager.db.list_channels() if item["id"] == ch_id))


@app.route("/api/v1/playlists/generate", methods=["POST"])
@require_role("editor")
def api_generate_custom_playlist():
    manifests = manager.generate_custom_playlist(request.json or {}); PROCESS_STATE["manifestos"] = manifests; add_process_log(f"Lista personalizada gerada com {len(manifests)} arquivo(s).", "success"); return jsonify({"status": "gerado", "manifestos": manifests})


@app.route("/api/v1/channels/<int:ch_id>/status", methods=["PATCH"])
@require_role("editor")
def api_toggle_channel_status(ch_id):
    data = request.json or {}; new_status = data.get("status", "offline")
    with manager.db.get_connection() as conn: conn.execute("UPDATE channels SET status = ? WHERE id = ?;", (new_status, ch_id)); conn.commit()
    return jsonify({"status": "atualizado"})


@app.route("/api/v1/channels/<int:ch_id>/autoremove", methods=["PATCH"])
@require_role("editor")
def api_toggle_autoremove(ch_id):
    data = request.json or {}; flag = data.get("auto_remove_if_offline", 1)
    with manager.db.get_connection() as conn: conn.execute("UPDATE channels SET auto_remove_if_offline = ? WHERE id = ?;", (flag, ch_id)); conn.commit()
    return jsonify({"status": "atualizado"})


@app.route("/api/v1/sync", methods=["POST"])
@require_role("editor")
def api_trigger_sync():
    if not has_sufficient_disk_space():
        add_process_log("Sincronização bloqueada: espaço em disco insuficiente.", "error")
        return jsonify({"status": "erro", "error": "Espaço em disco insuficiente. Libere espaço e tente novamente."}), 507
    internet = check_internet_health()
    if not internet.get("online"):
        add_process_log("Sincronização bloqueada: conexão com a Internet indisponível.", "warning")
        return jsonify({"status": "bloqueado", "error": "Internet indisponível. A sincronização não foi iniciada."}), 503
    payload = request.get_json(silent=True) or {}
    mode = str(payload.get("publication_mode") or manager.config_mgr.get_all().get("SYNC_PUBLICATION_MODE", "NONE")).upper()
    if mode not in {"NONE", "CREATE", "UPDATE", "CREATE_UPDATE"}:
        return jsonify({"error": "Modo de publicação inválido."}), 400
    PROCESS_STATE["publication_mode"] = mode
    if PROCESS_STATE["status"] != "Executando..." and not PIPELINE_LOCK.locked():
        threading.Thread(target=execute_pipeline, args=(mode,), daemon=True).start()
        add_process_log(f"Sincronização iniciada. Publicação: {mode}.", "info")
        return jsonify({"status": "iniciado", "publication_mode": mode})
    return jsonify({"status": "ja_em_execucao"})


@app.route("/api/config", methods=["POST"])
@require_role("admin")
def api_save_config():
    data = request.json or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Configuração inválida."}), 400
    known = set(manager.config_mgr.get_all())
    unknown = sorted(set(data) - known)
    if unknown:
        return jsonify({"error": "Configuração desconhecida.", "keys": unknown}), 400
    try:
        for key, value in data.items():
            manager.config_mgr.update_key(key, value)
    except (KeyError, OSError, ValueError) as exc:
        return jsonify({"error": f"Não foi possível salvar a configuração: {exc}"}), 400
    setup_scheduler()
    add_process_log("Configurações salvas com sucesso.", "success")
    return jsonify({"status": "atualizado"})


@app.route("/api/config", methods=["GET"])
@require_role("admin")
def api_get_config(): return jsonify(manager.config_mgr.get_public())


@app.route("/playlist/<filename>")
def serve_playlist(filename): return send_from_directory(manager.output_dir, filename, mimetype="application/x-mpegurl")


@app.route("/epg/<filename>")
def serve_epg(filename): return send_from_directory(manager.output_dir, filename, mimetype="application/xml")


if __name__ == "__main__":
    cfg = manager.config_mgr.get_all(); host_key = "PUBLIC_HOST" if PUBLIC_ONLY else "WEB_HOST"; port_key = "PUBLIC_PORT" if PUBLIC_ONLY else "WEB_PORT"; app.run(host=cfg[host_key], port=cfg[port_key], debug=False)
