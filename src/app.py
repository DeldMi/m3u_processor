import os
import threading
import asyncio
import glob
import time
from collections import deque
from datetime import datetime
from flask import Flask, render_template, jsonify, request, redirect, url_for, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
from src.manager import PlaylistManager
from src.config import ConfigManager
from src.auth import login_user, logout_user, current_user, require_role
from apscheduler.schedulers.background import BackgroundScheduler

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
app = Flask(__name__, 
            template_folder=os.path.join(BASE_DIR, "frontend", "templates"),
            static_folder=os.path.join(BASE_DIR, "frontend", "static"))

app.secret_key = ConfigManager(BASE_DIR).get_all().get("SECRET_KEY", "m3u_processor_secret_key_fixed")
manager = PlaylistManager(BASE_DIR)
scheduler = BackgroundScheduler(daemon=True)
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
    manager.db.add_process_event(message, level, ACTIVE_RUN_ID)

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
            "m3u_url": f"{cfg['BASE_URL']}/playlist/{m3u_name}",
            "xml_name": xml_name,
            "xml_url": f"{cfg['BASE_URL']}/epg/{xml_name}",
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
    if PROCESS_STATE["status"] == "Executando...":
        return

    STOP_REQUESTED.clear()
    PAUSE_REQUESTED.clear()
    ACTIVE_RUN_ID = manager.db.start_process_run()
    PROCESS_STATE["status"] = "Executando..."
    update_log_state("Iniciando auditoria completa...")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
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
    except Exception as e:
        PROCESS_STATE["status"] = "Erro"
        PROCESS_STATE["ultimo_log"] = f"Falha na execucao: {str(e)}"
        add_process_log(PROCESS_STATE["ultimo_log"], "error")
        manager.db.finish_process_run(ACTIVE_RUN_ID, "Erro", {}, PROCESS_STATE["ultimo_log"])
    finally:
        PAUSE_REQUESTED.clear()
        STOP_REQUESTED.clear()
        ACTIVE_RUN_ID = None
        loop.close()

def setup_scheduler():
    scheduler.remove_all_jobs()
    cfg = manager.config_mgr.get_all()
    mode = cfg.get("SCHEDULE_MODE", "DISABLED")

    if mode == "INTERVAL":
        hours = max(1, cfg.get("SCHEDULE_INTERVAL_HOURS", 12))
        scheduler.add_job(execute_pipeline, 'interval', hours=hours, id="m3u_sync_job")
    elif mode == "CRON":
        try:
            h, m = cfg.get("SCHEDULE_CRON_TIME", "03:00").split(":")
            scheduler.add_job(execute_pipeline, 'cron', hour=int(h), minute=int(m), id="m3u_sync_job")
        except Exception:
            pass

setup_scheduler()

@app.context_processor
def inject_user():
    return dict(user=current_user())

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
    return render_template("dashboard.html")

@app.route("/playlists")
@require_role("viewer")
def view_playlists():
    return render_template("playlists.html")

@app.route("/channels")
@require_role("viewer")
def view_channels():
    return render_template("channels.html")

@app.route("/users")
@require_role("admin")
def view_users():
    with manager.db.get_connection() as conn:
        users = [dict(u) for u in conn.execute("SELECT id, username, role, created_at FROM users;").fetchall()]
    return render_template("users.html", users=users)

@app.route("/settings")
@require_role("admin")
def view_settings():
    return render_template("settings.html", config=manager.config_mgr.get_all())

# --- ENDPOINTS REST & TELEMETRIA ---
@app.route("/api/status")
def get_status():
    data = dict(PROCESS_STATE)
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

@app.route("/api/v1/channels", methods=["GET"])
@require_role("viewer")
def api_get_channels():
    country = request.args.get("country")
    category = request.args.get("category")
    status = request.args.get("status")
    return jsonify(manager.db.list_channels(country, category, status, request.args.get("search", ""), request.args.get("sort", "id"), request.args.get("direction", "asc")))

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
    if PROCESS_STATE["status"] != "Executando...":
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

# Servidores estaticos de arquivos M3U e XMLTV
@app.route("/playlist/<filename>")
def serve_playlist(filename):
    return send_from_directory(manager.output_dir, filename, mimetype="application/x-mpegurl")

@app.route("/epg/<filename>")
def serve_epg(filename):
    return send_from_directory(manager.output_dir, filename, mimetype="application/xml")

if __name__ == "__main__":
    cfg = manager.config_mgr.get_all()
    app.run(host=cfg["WEB_HOST"], port=cfg["WEB_PORT"], debug=False)