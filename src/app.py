import os
import threading
import asyncio
import glob
import time
import re
import shutil
import sqlite3
import sys
from collections import deque
from datetime import datetime
from flask import Flask, render_template, jsonify, request, redirect, url_for, send_from_directory, send_file
from werkzeug.security import check_password_hash, generate_password_hash
from src.manager import PlaylistManager
from src.config import ConfigManager
from src.auth import login_user, logout_user, current_user, require_role
from apscheduler.schedulers.background import BackgroundScheduler

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
app = Flask(__name__, 
            template_folder=os.path.join(BASE_DIR, "frontend", "templates"),
            static_folder=os.path.join(BASE_DIR, "frontend", "static"))
REACT_DIR = os.path.join(BASE_DIR, "frontend", "react", "dist")

app.secret_key = ConfigManager(BASE_DIR).get_all().get("SECRET_KEY", "m3u_processor_secret_key_fixed")
manager = PlaylistManager(BASE_DIR)
scheduler = BackgroundScheduler(daemon=True)
PUBLIC_ONLY = os.getenv("PUBLIC_ONLY", "0") == "1"
if not PUBLIC_ONLY:
    scheduler.start()

PROCESS_STATE = {
    "status": "Ocioso",
    "total_canais": 0,
    "canais_online": 0,
    "canais_offline": 0,
    "manifestos": [],
    "ultimo_log": "Sistema pronto para execucao."
}
PROCESS_LOGS = deque(maxlen=250)
PAUSE_REQUESTED = threading.Event()
STOP_REQUESTED = threading.Event()
ACTIVE_RUN_ID = None
PIPELINE_LOCK = threading.Lock()
MIN_FREE_SPACE_BYTES = 512 * 1024 * 1024

class PipelineInterrupted(Exception):
    pass

def pipeline_checkpoint(stage: str):
    global PROCESS_STATE
    if STOP_REQUESTED.is_set():
        raise PipelineInterrupted("Execução interrompida pelo usuário.")
    while PAUSE_REQUESTED.is_set() and not STOP_REQUESTED.is_set():
        PROCESS_STATE["status"] = "Pausado"
        time.sleep(0.2)
    if STOP_REQUESTED.is_set():
        raise PipelineInterrupted("Execução interrompida pelo usuário.")
    if PROCESS_STATE["status"] == "Pausado":
        PROCESS_STATE["status"] = "Executando..."
        add_process_log("Execução retomada.")

PROCESS_LOGS.extend(manager.db.list_process_events(limit=250))
LAST_RUNS = manager.db.list_process_runs(limit=1)
if LAST_RUNS:
    last_run = LAST_RUNS[0]
    PROCESS_STATE.update({
        "status": last_run["status"] if last_run["status"] != "Executando..." else "Interrompido",
        "total_canais": last_run["total_canais"],
        "canais_online": last_run["canais_online"],
        "canais_offline": last_run["canais_offline"],
        "ultimo_log": last_run["last_message"] or PROCESS_STATE["ultimo_log"]
    })

def add_process_log(message: str, level: str = "info"):
    global ACTIVE_RUN_ID
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    PROCESS_LOGS.appendleft({
        "timestamp": timestamp,
        "level": level,
        "message": message
    })
    try:
        manager.db.add_process_event(message, level, ACTIVE_RUN_ID)
    except (OSError, sqlite3.OperationalError):
        pass

def has_sufficient_disk_space() -> bool:
    return shutil.disk_usage(BASE_DIR).free >= MIN_FREE_SPACE_BYTES

def get_output_manifests():
    cfg = manager.config_mgr.get_all()
    manifests = []
    for m3u_path in sorted(glob.glob(os.path.join(manager.output_dir, "*.m3u"))):
        m3u_name = os.path.basename(m3u_path)
        xml_name = os.path.splitext(m3u_name)[0].replace("playlist_", "epg_") + ".xml"
        xml_path = os.path.join(manager.output_dir, xml_name)
        try:
            with open(m3u_path, "r", encoding="utf-8", errors="ignore") as playlist_file:
                total = sum(1 for line in playlist_file if line.startswith("#EXTINF:"))
        except OSError:
            total = 0
        manifests.append({
            "m3u_name": m3u_name,
            "m3u_url": f"{cfg['PUBLIC_BASE_URL']}/playlist/{m3u_name}",
            "xml_name": xml_name,
            "xml_url": f"{cfg['PUBLIC_BASE_URL']}/epg/{xml_name}",
            "total": total,
            "xml_exists": os.path.exists(xml_path)
        })
    return manifests

def update_log_state(message: str):
    global PROCESS_STATE
    PROCESS_STATE["ultimo_log"] = message
    add_process_log(message)

def execute_pipeline():
    global PROCESS_STATE, ACTIVE_RUN_ID
    if PROCESS_STATE["status"] == "Executando..." or not PIPELINE_LOCK.acquire(blocking=False):
        return

    loop = None
    try:
        if not has_sufficient_disk_space():
            PROCESS_STATE["status"] = "Erro"
            PROCESS_STATE["ultimo_log"] = "Espaço em disco insuficiente para executar a sincronização."
            return
        STOP_REQUESTED.clear()
        PAUSE_REQUESTED.clear()
        ACTIVE_RUN_ID = manager.db.start_process_run()
        PROCESS_STATE["status"] = "Executando..."
        update_log_state("Iniciando auditoria completa...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(manager.sync_and_audit(progress_callback=update_log_state, control_callback=pipeline_checkpoint))
        PROCESS_STATE["total_canais"] = res.get("total", 0)
        PROCESS_STATE["canais_online"] = res.get("online", 0)
        PROCESS_STATE["canais_offline"] = res.get("offline", 0)
        PROCESS_STATE["manifestos"] = res.get("partitions", [])
        PROCESS_STATE["status"] = "Concluido"
        PROCESS_STATE["ultimo_log"] = f"Sucesso! {res.get('online', 0)} canais operantes salvos em {len(res.get('partitions', []))} lista(s). Log: {res.get('log_file')}"
        add_process_log(PROCESS_STATE["ultimo_log"], "success")
        manager.db.finish_process_run(ACTIVE_RUN_ID, "Concluido", res, PROCESS_STATE["ultimo_log"])
    except PipelineInterrupted as exc:
        PROCESS_STATE["status"] = "Interrompido"
        PROCESS_STATE["ultimo_log"] = str(exc)
        add_process_log(PROCESS_STATE["ultimo_log"], "warning")
        manager.db.finish_process_run(ACTIVE_RUN_ID, "Interrompido", {}, PROCESS_STATE["ultimo_log"])
    except (OSError, sqlite3.OperationalError) as e:
        PROCESS_STATE["status"] = "Erro"
        PROCESS_STATE["ultimo_log"] = "Falha de armazenamento durante a execução. Libere espaço em disco e tente novamente."
        if "database or disk is full" not in str(e).lower() and "no space left" not in str(e).lower():
            PROCESS_STATE["ultimo_log"] = f"Falha de armazenamento: {str(e)}"
        add_process_log(PROCESS_STATE["ultimo_log"], "error")
        if ACTIVE_RUN_ID is not None:
            try:
                manager.db.finish_process_run(ACTIVE_RUN_ID, "Erro", {}, PROCESS_STATE["ultimo_log"])
            except (OSError, sqlite3.OperationalError):
                pass
    except Exception as e:
        PROCESS_STATE["status"] = "Erro"
        PROCESS_STATE["ultimo_log"] = f"Falha na execucao: {str(e)}"
        add_process_log(PROCESS_STATE["ultimo_log"], "error")
        manager.db.finish_process_run(ACTIVE_RUN_ID, "Erro", {}, PROCESS_STATE["ultimo_log"])
    finally:
        PAUSE_REQUESTED.clear()
        STOP_REQUESTED.clear()
        ACTIVE_RUN_ID = None
        if loop is not None:
            loop.close()
        PIPELINE_LOCK.release()

def execute_health_check():
    if PIPELINE_LOCK.locked() or not has_sufficient_disk_space():
        return
    try:
        result = asyncio.run(manager.refresh_channel_health())
        PROCESS_STATE["total_canais"] = result["total"]
        PROCESS_STATE["canais_online"] = result["online"]
        PROCESS_STATE["canais_offline"] = result["offline"]
        PROCESS_STATE["ultimo_log"] = f"Saúde atualizada: {result['online']} online, {result['offline']} offline."
    except (OSError, sqlite3.OperationalError):
        return

def setup_scheduler():
    scheduler.remove_all_jobs()
    cfg = manager.config_mgr.get_all()
    mode = cfg.get("SCHEDULE_MODE", "DISABLED")
    scheduler.add_job(execute_health_check, "interval", seconds=max(15, cfg.get("HEALTH_CHECK_INTERVAL_SECONDS", 60)), id="m3u_health_job", replace_existing=True, max_instances=1, coalesce=True, next_run_time=datetime.now())

    if mode == "INTERVAL":
        hours = max(1, cfg.get("SCHEDULE_INTERVAL_HOURS", 12))
        scheduler.add_job(execute_pipeline, 'interval', hours=hours, id="m3u_sync_job")
    elif mode == "CRON":
        try:
            h, m = cfg.get("SCHEDULE_CRON_TIME", "03:00").split(":")
            scheduler.add_job(execute_pipeline, 'cron', hour=int(h), minute=int(m), id="m3u_sync_job")
        except Exception:
            pass

if not PUBLIC_ONLY:
    setup_scheduler()

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

# --- AUTENTICACAO ---
@app.route("/login", methods=["GET", "POST"])
def auth_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        with manager.db.get_connection() as conn:
            user = conn.execute("SELECT * FROM users WHERE username = ?;", (username,)).fetchone()
            if user and check_password_hash(user["password_hash"], password):
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

# --- INTERFACES HTML ---
@app.route("/")
def view_dashboard():
    # Se o usuario nao estiver logado, redireciona para login
    if not current_user():
        return redirect(url_for("auth_login"))
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

@app.route("/users")
@require_role("admin")
def view_users():
    react_app = serve_react_app()
    if react_app:
        return react_app
    return render_template("users.html", users=manager.db.list_users())

@app.route("/settings")
@require_role("admin")
def view_settings():
    react_app = serve_react_app()
    if react_app:
        return react_app
    return render_template("settings.html", config=manager.config_mgr.get_all())

# --- ENDPOINTS REST & TELEMETRIA ---
@app.route("/api/status")
def get_status():
    data = dict(PROCESS_STATE)
    channels = manager.db.list_channels()
    if channels:
        data["total_canais"] = len(channels)
        data["canais_online"] = sum(channel.get("status") == "online" for channel in channels)
        data["canais_offline"] = sum(channel.get("status") == "offline" for channel in channels)
        data["canais_desconhecidos"] = sum(channel.get("status") == "desconhecido" for channel in channels)
    data["logs"] = list(PROCESS_LOGS)
    data["log_count"] = len(PROCESS_LOGS)
    data["historico"] = manager.db.list_process_runs(limit=20)
    return jsonify(data)

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
    if PROCESS_STATE["status"] != "Executando..." and PROCESS_STATE["status"] != "Pausado":
        return jsonify({"status": "inativo"}), 409
    if PAUSE_REQUESTED.is_set():
        PAUSE_REQUESTED.clear()
        PROCESS_STATE["status"] = "Executando..."
        add_process_log("Execução retomada pelo usuário.")
        return jsonify({"status": "retomado"})
    PAUSE_REQUESTED.set()
    PROCESS_STATE["status"] = "Pausado"
    add_process_log("Execução pausada pelo usuário.", "warning")
    return jsonify({"status": "pausado"})

@app.route("/api/v1/sync/stop", methods=["POST"])
@require_role("editor")
def api_stop_sync():
    if PROCESS_STATE["status"] not in ("Executando...", "Pausado"):
        return jsonify({"status": "inativo"}), 409
    STOP_REQUESTED.set()
    PAUSE_REQUESTED.clear()
    add_process_log("Interrupção solicitada pelo usuário.", "warning")
    return jsonify({"status": "interrupcao_solicitada"})

@app.route("/api/v1/playlists")
@require_role("viewer")
def api_get_playlists():
    manifests = get_output_manifests()
    PROCESS_STATE["manifestos"] = manifests
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
        for path in (m3u_path, xml_path):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass
        deleted.append(os.path.basename(m3u_name))
    PROCESS_STATE["manifestos"] = get_output_manifests()
    add_process_log(f"Removida(s) {len(deleted)} lista(s) publicada(s).", "warning")
    return jsonify({"status": "removido", "deleted": deleted})

@app.route("/api/v1/playlists/<path:m3u_name>", methods=["PATCH"])
@require_role("editor")
def api_rename_playlist(m3u_name):
    old_name = os.path.basename(m3u_name)
    new_label = str((request.json or {}).get("name", "")).strip()
    match = re.fullmatch(r"playlist(?:_[A-Za-z0-9_-]+)?_parte_(\d{2})\.m3u", old_name)
    safe_label = re.sub(r"[^a-zA-Z0-9_-]+", "_", new_label).strip("_-")
    if not match or not safe_label:
        return jsonify({"error": "Nome ou lista inválida"}), 400
    old_xml = os.path.splitext(old_name)[0].replace("playlist_", "epg_") + ".xml"
    new_name = f"playlist_{safe_label}_parte_{match.group(1)}.m3u"
    new_xml = f"epg_{safe_label}_parte_{match.group(1)}.xml"
    old_m3u_path = os.path.join(manager.output_dir, old_name)
    old_xml_path = os.path.join(manager.output_dir, old_xml)
    new_m3u_path = os.path.join(manager.output_dir, new_name)
    new_xml_path = os.path.join(manager.output_dir, new_xml)
    if not os.path.isfile(old_m3u_path) or not os.path.isfile(old_xml_path):
        return jsonify({"error": "Lista ou XML não encontrado"}), 404
    if old_name != new_name and (os.path.exists(new_m3u_path) or os.path.exists(new_xml_path)):
        return jsonify({"error": "Já existe uma lista com esse nome"}), 409
    with open(old_m3u_path, "r", encoding="utf-8", errors="ignore") as playlist_file:
        content = playlist_file.read().replace(f"/epg/{old_xml}", f"/epg/{new_xml}")
    with open(old_m3u_path, "w", encoding="utf-8") as playlist_file:
        playlist_file.write(content)
    os.replace(old_m3u_path, new_m3u_path)
    os.replace(old_xml_path, new_xml_path)
    PROCESS_STATE["manifestos"] = get_output_manifests()
    add_process_log(f"Lista renomeada para {new_name}.", "success")
    return jsonify({"status": "atualizado", "m3u_name": new_name, "xml_name": new_xml})

@app.route("/api/v1/channels", methods=["GET"])
@require_role("viewer")
def api_get_channels():
    country = request.args.get("country")
    category = request.args.get("category")
    status = request.args.get("status")
    return jsonify(manager.db.list_channels(country, category, status, request.args.get("search", ""), request.args.get("sort", "id"), request.args.get("direction", "asc")))

@app.route("/api/v1/users", methods=["GET", "POST"])
@require_role("admin")
def api_users():
    if request.method == "POST":
        data = request.json if request.is_json else request.form
        if not manager.db.create_user(data.get("username", ""), data.get("password", ""), data.get("role", "viewer")):
            return jsonify({"error": "Usuário inválido ou já existente"}), 400
        return jsonify({"status": "criado"}), 201
    return jsonify(manager.db.list_users())

@app.route("/api/v1/users/<int:user_id>", methods=["PATCH"])
@require_role("admin")
def api_update_user(user_id):
    if not manager.db.update_user(user_id, request.json or {}):
        return jsonify({"error": "Usuário não encontrado ou sem alterações"}), 404
    return jsonify({"status": "atualizado"})

@app.route("/api/profile", methods=["PATCH"])
def api_update_profile():
    user = current_user()
    if not user:
        return jsonify({"error": "Não autenticado"}), 401
    values = request.json or {}
    if values.get("username") and values["username"] != user["username"]:
        with manager.db.get_connection() as conn:
            try:
                conn.execute("UPDATE users SET username = ? WHERE id = ?", (str(values["username"]).strip(), user["id"]))
                conn.commit()
            except sqlite3.IntegrityError:
                return jsonify({"error": "Nome de usuário já existe"}), 409
    if values.get("password") or values.get("role"):
        if user["role"] != "admin" and values.get("role"):
            return jsonify({"error": "Somente admin pode alterar papel"}), 403
        manager.db.update_user(user["id"], values)
    return jsonify({"status": "atualizado", "user": manager.db.get_user(user["id"])})

@app.route("/api/admin/restart", methods=["POST"])
@require_role("admin")
def api_admin_restart():
    def restart():
        os.execv(sys.executable, [sys.executable, "-m", "src.app"])
    threading.Timer(0.25, restart).start()
    return jsonify({"status": "reiniciando"})

@app.route("/api/admin/shutdown", methods=["POST"])
@require_role("admin")
def api_admin_shutdown():
    threading.Timer(0.25, os._exit, args=(0,)).start()
    return jsonify({"status": "desligando"})

@app.route("/api/v1/channels/<int:ch_id>", methods=["PATCH"])
@require_role("editor")
def api_update_channel(ch_id):
    if not manager.db.update_channel(ch_id, request.json or {}):
        return jsonify({"error": "Canal nao encontrado ou sem campos validos"}), 404
    return jsonify(next(item for item in manager.db.list_channels() if item["id"] == ch_id))

@app.route("/api/v1/playlists/generate", methods=["POST"])
@require_role("editor")
def api_generate_custom_playlist():
    manifests = manager.generate_custom_playlist(request.json or {})
    PROCESS_STATE["manifestos"] = manifests
    add_process_log(f"Lista personalizada gerada com {len(manifests)} arquivo(s).", "success")
    return jsonify({"status": "gerado", "manifestos": manifests})

@app.route("/api/v1/channels/<int:ch_id>/status", methods=["PATCH"])
@require_role("editor")
def api_toggle_channel_status(ch_id):
    data = request.json or {}
    new_status = data.get("status", "offline")
    with manager.db.get_connection() as conn:
        conn.execute("UPDATE channels SET status = ? WHERE id = ?;", (new_status, ch_id))
        conn.commit()
    return jsonify({"status": "atualizado"})

@app.route("/api/v1/channels/<int:ch_id>/autoremove", methods=["PATCH"])
@require_role("editor")
def api_toggle_autoremove(ch_id):
    data = request.json or {}
    flag = data.get("auto_remove_if_offline", 1)
    with manager.db.get_connection() as conn:
        conn.execute("UPDATE channels SET auto_remove_if_offline = ? WHERE id = ?;", (flag, ch_id))
        conn.commit()
    return jsonify({"status": "atualizado"})

@app.route("/api/v1/sync", methods=["POST"])
@require_role("editor")
def api_trigger_sync():
    if not has_sufficient_disk_space():
        return jsonify({"status": "erro", "error": "Espaço em disco insuficiente. Libere espaço e tente novamente."}), 507
    if PROCESS_STATE["status"] != "Executando..." and not PIPELINE_LOCK.locked():
        thread = threading.Thread(target=execute_pipeline, daemon=True)
        thread.start()
        return jsonify({"status": "iniciado"})
    return jsonify({"status": "ja_em_execucao"})

@app.route("/api/config", methods=["POST"])
@require_role("admin")
def api_save_config():
    data = request.json or {}
    for k, v in data.items():
        manager.config_mgr.update_key(k, v)
    setup_scheduler()
    return jsonify({"status": "atualizado"})

@app.route("/api/config", methods=["GET"])
@require_role("admin")
def api_get_config():
    return jsonify(manager.config_mgr.get_all())

# Servidores estaticos de arquivos M3U e XMLTV
@app.route("/playlist/<filename>")
def serve_playlist(filename):
    return send_from_directory(manager.output_dir, filename, mimetype="application/x-mpegurl")

@app.route("/epg/<filename>")
def serve_epg(filename):
    return send_from_directory(manager.output_dir, filename, mimetype="application/xml")

if __name__ == "__main__":
    cfg = manager.config_mgr.get_all()
    host_key = "PUBLIC_HOST" if PUBLIC_ONLY else "WEB_HOST"
    port_key = "PUBLIC_PORT" if PUBLIC_ONLY else "WEB_PORT"
    app.run(host=cfg[host_key], port=cfg[port_key], debug=False)