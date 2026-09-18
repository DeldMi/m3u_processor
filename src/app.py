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
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from apscheduler.schedulers.background import BackgroundScheduler
from src.auth import login_user, logout_user, current_user, require_role
from src.config import ConfigManager
from src.core.scheduler import configure_scheduler
from src.domains.health.internet import check_internet_health as _check_internet_health
from src.domains.playlists.service import get_output_manifests as _get_output_manifests
from src.domains.sync.service import execute_health_check as _execute_health_check
from src.domains.sync.service import execute_pipeline as _execute_pipeline
from src.domains.authz.service import create_user as authz_create_user, update_user as authz_update_user, list_public_users, has_permission
from src.domains.monitoring.service import ResourceMonitor
from src.domains.monitoring.routes import register_monitoring_routes
from src.manager import PlaylistManager

BASE_DIR=os.path.abspath(os.path.join(os.path.dirname(__file__),"..")); app=Flask(__name__,template_folder=os.path.join(BASE_DIR,"frontend","templates"),static_folder=os.path.join(BASE_DIR,"frontend","static")); REACT_DIR=os.path.join(BASE_DIR,"frontend","react","dist"); app.secret_key=ConfigManager(BASE_DIR).get_all().get("SECRET_KEY")
manager=PlaylistManager(BASE_DIR);scheduler=BackgroundScheduler(daemon=True);PUBLIC_ONLY=os.getenv("PUBLIC_ONLY","0")=="1"
if not PUBLIC_ONLY:scheduler.start()
PROCESS_STATE={"status":"Ocioso","total_canais":0,"canais_online":0,"canais_offline":0,"manifestos":[],"ultimo_log":"Sistema pronto para execucao.","publication_mode":"NONE"};PROCESS_LOGS=deque(maxlen=250);PAUSE_REQUESTED=threading.Event();STOP_REQUESTED=threading.Event();ACTIVE_RUN_ID=None;NOTIFICATIONS=deque(maxlen=100);RESOURCE_MONITOR=ResourceMonitor(history_size=120);PIPELINE_LOCK=threading.Lock();MIN_FREE_SPACE_BYTES=512*1024*1024
PROCESS_LOGS.extend(manager.db.list_process_events(limit=250)); LAST_RUNS=manager.db.list_process_runs(limit=1)
if LAST_RUNS:
    last=LAST_RUNS[0];PROCESS_STATE.update({"status":last["status"] if last["status"]!="Executando..." else "Interrompido","total_canais":last["total_canais"],"canais_online":last["canais_online"],"canais_offline":last["canais_offline"],"ultimo_log":last["last_message"] or PROCESS_STATE["ultimo_log"]})

def add_notification(level,title,message,source="Execução",path="",details=""):
    NOTIFICATIONS.appendleft({"id":uuid.uuid4().hex,"level":level,"title":title,"message":message,"timestamp":datetime.now().isoformat(timespec="seconds"),"source":source,"path":path,"details":details})

def add_process_log(message,level="info",run_id=None):
    PROCESS_LOGS.appendleft({"timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"level":level,"message":message})
    try:manager.db.add_process_event(message,level,ACTIVE_RUN_ID if run_id is None else run_id)
    except (OSError,sqlite3.OperationalError):pass
    if level in {"success","warning","error"}:add_notification(level,"Execução",message,source="Execução",path="/")

def has_sufficient_disk_space():return shutil.disk_usage(BASE_DIR).free>=MIN_FREE_SPACE_BYTES
def update_log_state(message):PROCESS_STATE.update({"ultimo_log":message});add_process_log(message)
def check_internet_health():return _check_internet_health(manager.config_mgr.get_all())
def get_output_manifests():return _get_output_manifests(manager)
def execute_health_check():return _execute_health_check(manager=manager,process_state=PROCESS_STATE,pipeline_lock=PIPELINE_LOCK)
def execute_pipeline(publication_mode=None):
    mode=(publication_mode or manager.config_mgr.get_all().get("SYNC_PUBLICATION_MODE","NONE")).upper();return _execute_pipeline(manager=manager,process_state=PROCESS_STATE,process_logs=PROCESS_LOGS,pause_requested=PAUSE_REQUESTED,stop_requested=STOP_REQUESTED,pipeline_lock=PIPELINE_LOCK,state={"active_run_id":ACTIVE_RUN_ID},min_free_space_bytes=MIN_FREE_SPACE_BYTES,update_log=add_process_log,publication_mode=mode)
def setup_scheduler():configure_scheduler(scheduler,manager,execute_pipeline,execute_health_check)
if not PUBLIC_ONLY:setup_scheduler()
register_monitoring_routes(app,manager,PROCESS_STATE,PROCESS_LOGS,NOTIFICATIONS,RESOURCE_MONITOR,add_notification=add_notification)

@app.before_request
def restrict_public_server():
    if PUBLIC_ONLY and not(request.path.startswith("/playlist/") or request.path.startswith("/epg/")):return jsonify({"error":"Apenas links públicos estão disponíveis nesta porta."}),404
@app.context_processor
def inject_user():return dict(user=current_user())
def serve_react_app():
    index=os.path.join(REACT_DIR,"index.html");return send_file(index) if os.path.exists(index) else None

@app.route("/login",methods=["GET","POST"])
def auth_login():
    if request.method=="POST":
        username=request.form.get("username","").strip();password=request.form.get("password","")
        with manager.db.get_connection() as conn:
            user=conn.execute("SELECT * FROM users WHERE username=?",(username,)).fetchone()
            if user and bool(user["active"] if "active" in user.keys() else 1) and user["password_hash"] and check_password_hash(user["password_hash"],password):login_user(dict(user));return redirect(url_for("view_dashboard"))
        return render_template("login.html",error="Credenciais invalidas.")
    return serve_react_app() or render_template("login.html")
@app.route("/logout")
def auth_logout():logout_user();return redirect(url_for("auth_login"))
@app.route("/")
@require_role("viewer")
def view_dashboard():return serve_react_app() or render_template("dashboard.html")
@app.route("/api/me")
def api_me():
    user=current_user()
    return (jsonify({"user":user}),200) if user else (jsonify({"user":None}),401)
@app.route("/app-assets/<path:filename>")
@app.route("/assets/<path:filename>")
def react_assets(filename):return send_from_directory(REACT_DIR,filename)
@app.route("/playlists")
@require_role("viewer")
def view_playlists():return serve_react_app() or render_template("playlists.html")
@app.route("/channels")
@require_role("viewer")
def view_channels():return serve_react_app() or render_template("channels.html")
@app.route("/users")
@require_role("viewer")
def view_users():return serve_react_app() or render_template("users.html",users=list_public_users(manager.db))
@app.route("/settings")
@require_role("viewer")
def view_settings():return serve_react_app() or render_template("settings.html",config=manager.config_mgr.get_public())
@app.route("/settings/<path:subpath>")
@require_role("viewer")
def view_settings_subpath(subpath):return serve_react_app() or render_template("settings.html",config=manager.config_mgr.get_public())

@app.route("/api/status")
@require_role("viewer")
def get_status():
    user=current_user(manager.db);data={"status":PROCESS_STATE["status"]}
    if user and has_permission(manager.db,int(user["id"]),user["role"],"dashboard","view"):data.update({k:PROCESS_STATE[k] for k in ("total_canais","canais_online","canais_offline")})
    if user and has_permission(manager.db,int(user["id"]),user["role"],"channels","view"):
        channels=manager.db.list_channels();data.update({"total_canais":len(channels),"canais_online":sum(c.get("status")=="online" for c in channels),"canais_offline":sum(c.get("status")=="offline" for c in channels),"canais_desconhecidos":sum(c.get("status")=="desconhecido" for c in channels)})
    if user and has_permission(manager.db,int(user["id"]),user["role"],"playlists","view"):data["manifestos"]=get_output_manifests()
    if user and has_permission(manager.db,int(user["id"]),user["role"],"logs","view"):data.update({"ultimo_log":PROCESS_STATE["ultimo_log"],"logs":list(PROCESS_LOGS),"log_count":len(PROCESS_LOGS),"historico":manager.db.list_process_runs(limit=20)})
    if user and has_permission(manager.db,int(user["id"]),user["role"],"sync","view"):data["sync"]={"status":PROCESS_STATE["status"],"active":PROCESS_STATE["status"] in ("Executando...","Pausado")}
    return jsonify(data)

@app.route("/api/v1/internet-health")
@require_role("viewer")
def api_internet_health():return jsonify(check_internet_health())
@app.route("/api/v1/logs")
@require_role("viewer")
def api_get_logs():return jsonify(manager.db.list_process_events(limit=1000))
@app.route("/api/v1/history")
@require_role("viewer")
def api_get_history():return jsonify(manager.db.list_process_runs(limit=100))
@app.route("/api/v1/sync/pause",methods=["POST"])
@require_role("editor")
def api_pause_sync():
    if PROCESS_STATE["status"] not in ("Executando...","Pausado"):return jsonify({"status":"inativo"}),409
    if PAUSE_REQUESTED.is_set():PAUSE_REQUESTED.clear();PROCESS_STATE["status"]="Executando...";return jsonify({"status":"retomado"})
    PAUSE_REQUESTED.set();PROCESS_STATE["status"]="Pausado";return jsonify({"status":"pausado"})
@app.route("/api/v1/sync/stop",methods=["POST"])
@require_role("editor")
def api_stop_sync():
    if PROCESS_STATE["status"] not in ("Executando...","Pausado"):return jsonify({"status":"inativo"}),409
    STOP_REQUESTED.set();PAUSE_REQUESTED.clear();return jsonify({"status":"interrupcao_solicitada"})
@app.route("/api/v1/playlists")
@require_role("viewer")
def api_get_playlists():return jsonify({"status":PROCESS_STATE["status"],"manifestos":get_output_manifests()})
@app.route("/api/v1/channels",methods=["GET"])
@require_role("viewer")
def api_get_channels():
    channels=manager.db.list_channels(request.args.get("country"),request.args.get("category"),request.args.get("status"),request.args.get("search",""),request.args.get("sort","id"),request.args.get("direction","asc"));city=request.args.get("city")
    return jsonify([c for c in channels if not city or city=="todos" or c.get("city")==city])
@app.route("/api/v1/channels/options")
@require_role("viewer")
def api_channel_options():return jsonify(manager.db.channel_filter_options())
@app.route("/api/v1/channels/logo",methods=["POST"])
@require_role("editor")
def api_upload_channel_logo():
    image=request.files.get("image")
    if not image or not image.filename:return jsonify({"error":"Nenhuma imagem foi enviada"}),400
    ext=os.path.splitext(image.filename)[1].lower()
    if ext not in {".png",".jpg",".jpeg",".webp",".gif"}:return jsonify({"error":"Formato de imagem não permitido"}),400
    directory=os.path.join(BASE_DIR,"frontend","static","uploads");os.makedirs(directory,exist_ok=True);filename=f"channel_{uuid.uuid4().hex}_{secure_filename(image.filename)}";image.save(os.path.join(directory,filename));return jsonify({"url":f"/static/uploads/{filename}"})
@app.route("/api/v1/channels/<int:ch_id>",methods=["PATCH"])
@require_role("editor")
def api_update_channel(ch_id):
    if not manager.db.update_channel(ch_id,request.json or {}):return jsonify({"error":"Canal não encontrado ou sem campos válidos"}),404
    return jsonify(next((c for c in manager.db.list_channels() if c["id"]==ch_id),{}))
@app.route("/api/v1/channels/<int:ch_id>/status",methods=["PATCH"])
@require_role("editor")
def api_toggle_channel_status(ch_id):
    status=(request.json or {}).get("status","offline")
    if status not in {"online","offline","desconhecido"}:return jsonify({"error":"Status inválido"}),400
    with manager.db.get_connection() as conn:conn.execute("UPDATE channels SET status=? WHERE id=?",(status,ch_id));conn.commit()
    return jsonify({"status":"atualizado"})
@app.route("/api/v1/channels/<int:ch_id>/autoremove",methods=["PATCH"])
@require_role("editor")
def api_toggle_autoremove(ch_id):
    flag=(request.json or {}).get("auto_remove_if_offline",1)
    if flag not in (0,1,False,True):return jsonify({"error":"Valor inválido"}),400
    with manager.db.get_connection() as conn:conn.execute("UPDATE channels SET auto_remove_if_offline=? WHERE id=?",(int(bool(flag)),ch_id));conn.commit()
    return jsonify({"status":"atualizado"})
@app.route("/api/v1/channels",methods=["POST"])
@require_role("editor")
def create_channel():return jsonify({"error":"Use o domínio de canais para criação."}),405
@app.route("/api/v1/playlists/generate",methods=["POST"])
@require_role("editor")
def api_generate_custom_playlist():
    manifests=manager.generate_custom_playlist(request.json or {});return jsonify({"status":"gerado","manifestos":manifests})
@app.route("/api/v1/sync",methods=["POST"])
@require_role("editor")
def api_trigger_sync():
    if not has_sufficient_disk_space():return jsonify({"status":"erro","error":"Espaço em disco insuficiente."}),507
    if not check_internet_health().get("online"):return jsonify({"status":"bloqueado","error":"Internet indisponível."}),503
    mode=str((request.get_json(silent=True) or {}).get("publication_mode") or manager.config_mgr.get_all().get("SYNC_PUBLICATION_MODE","NONE")).upper()
    if mode not in {"NONE","CREATE","UPDATE","CREATE_UPDATE"}:return jsonify({"error":"Modo de publicação inválido."}),400
    if PROCESS_STATE["status"]!="Executando..." and not PIPELINE_LOCK.locked():threading.Thread(target=execute_pipeline,args=(mode,),daemon=True).start();return jsonify({"status":"iniciado","publication_mode":mode})
    return jsonify({"status":"ja_em_execucao"})
@app.route("/api/config",methods=["GET"])
@require_role("viewer")
def api_get_config():return jsonify(manager.config_mgr.get_public())
@app.route("/api/config",methods=["POST"])
@require_role("admin")
def api_save_config():
    data=request.json or {}
    if not isinstance(data,dict):return jsonify({"error":"Configuração inválida."}),400
    unknown=sorted(set(data)-set(manager.config_mgr.get_all()))
    if unknown:return jsonify({"error":"Configuração desconhecida.","keys":unknown}),400
    try:
        for key,value in data.items():manager.config_mgr.update_key(key,value)
        setup_scheduler()
    except (KeyError,PermissionError,OSError,ValueError) as exc:return jsonify({"error":f"Não foi possível salvar a configuração: {exc}"}),400
    return jsonify({"status":"atualizado"})
@app.route("/api/v1/users",methods=["GET","POST"])
@require_role("admin")
def api_users():
    if request.method=="POST":
        data=dict(request.get_json(silent=True) or request.form);actor=current_user(manager.db)
        if actor and not has_permission(manager.db,int(actor["id"]),actor["role"],"users","admin"):data["role"]="viewer";data.pop("permissions",None)
        user=authz_create_user(manager.db,data)
        return (jsonify(user),201) if user else (jsonify({"error":"Usuário inválido, senha fraca ou login já existente"}),400)
    return jsonify(list_public_users(manager.db))
@app.route("/api/v1/users/<int:user_id>",methods=["PATCH"])
@require_role("admin")
def api_update_user(user_id):
    data=dict(request.get_json(silent=True) or {});actor=current_user(manager.db)
    if actor and not has_permission(manager.db,int(actor["id"]),actor["role"],"users","admin"):data.pop("role",None);data.pop("permissions",None)
    user=authz_update_user(manager.db,user_id,data);return jsonify(user) if user else (jsonify({"error":"Usuário inválido ou sem alterações"}),400)
@app.route("/api/profile",methods=["PATCH"])
def api_update_profile():
    user=current_user()
    if not user:return jsonify({"error":"Não autenticado"}),401
    values=request.json or {}
    if any(k in values for k in ("role","active","permissions")):return jsonify({"error":"Alteração administrativa não permitida."}),403
    allowed={"username","display_name","full_name","email","avatar","phone","description","department","password"};updated=authz_update_user(manager.db,int(user["id"]),{k:v for k,v in values.items() if k in allowed});return jsonify({"status":"atualizado","user":updated}) if updated else (jsonify({"error":"Perfil inválido ou sem alterações"}),400)
@app.route("/api/admin/restart",methods=["POST"])
@require_role("admin")
def api_admin_restart():threading.Timer(.25,lambda:os.execv(sys.executable,[sys.executable,"-m","src.app"])).start();return jsonify({"status":"reiniciando"})
@app.route("/api/admin/shutdown",methods=["POST"])
@require_role("admin")
def api_admin_shutdown():threading.Timer(.25,os._exit,args=(0,)).start();return jsonify({"status":"desligando"})
@app.route("/playlist/<path:filename>")
def serve_playlist(filename):
    name=os.path.basename(filename)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.m3u8?",name):return jsonify({"error":"Arquivo inválido"}),400
    return send_from_directory(manager.output_dir,name,mimetype="application/x-mpegurl")
@app.route("/epg/<path:filename>")
def serve_epg(filename):
    name=os.path.basename(filename)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.xml",name):return jsonify({"error":"Arquivo inválido"}),400
    return send_from_directory(manager.output_dir,name,mimetype="application/xml")
if __name__=="__main__":
    cfg=manager.config_mgr.get_all();key="PUBLIC_HOST" if PUBLIC_ONLY else "WEB_HOST";port="PUBLIC_PORT" if PUBLIC_ONLY else "WEB_PORT";app.run(host=cfg[key],port=cfg[port],debug=False)
