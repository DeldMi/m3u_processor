"""Rotas de monitoramento, diagnóstico, canais e notificações operacionais."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime
from flask import jsonify, request
from werkzeug.utils import secure_filename
from src.auth import require_role, current_user, require_permission
from src.domains.authz.service import has_permission
from .service import ResourceMonitor


def register_monitoring_routes(app, manager, process_state, process_logs, notifications, monitor: ResourceMonitor, add_notification=None):
    def allowed(resource: str, action: str = "view") -> bool:
        user = current_user(manager.db)
        return bool(user and has_permission(manager.db, int(user["id"]), user["role"], resource, action))

    @app.route("/api/v1/resources")
    @require_permission("health", "view")
    def resources():
        return jsonify(monitor.payload(manager.base_dir, process_state["status"] in ("Executando...", "Pausado")))

    @app.route("/api/v1/resources/diagnostics")
    @require_permission("health", "view")
    def resource_diagnostics():
        return jsonify(monitor.diagnose(manager.base_dir, process_state["status"] in ("Executando...", "Pausado")))

    @app.route("/api/v1/resources/gc", methods=["POST"])
    @require_permission("maintenance", "execute")
    def resource_gc():
        result = monitor.clear_python_caches()
        if add_notification:
            add_notification("success", "Memória limpa", f"Coleta executada: {result['collected_objects']} objetos.", source="Manutenção", path="/settings/resources")
        return jsonify(result)

    @app.route("/api/v1/notifications")
    @require_permission("dashboard", "view")
    def get_notifications():
        return jsonify(list(notifications))

    def read_themes():
        try:
            themes = json.loads(str(manager.config_mgr.get_all().get("CUSTOM_THEMES", "[]")))
            return themes if isinstance(themes, list) else []
        except (TypeError, ValueError):
            return []

    @app.route("/api/v1/themes")
    @require_permission("settings", "view")
    def get_themes():
        return jsonify(read_themes())

    def normalize_theme(theme):
        keys=("bg","surface","line","ink","muted","accent","success","danger","menu","login","fontFamily","fontSize","headingScale","siteName","logo","title","h1","h2","h3")
        return {k:str(theme.get(k,"")) for k in keys}

    @app.route("/api/v1/themes", methods=["POST"])
    @require_permission("settings", "admin")
    def create_theme():
        data=request.get_json(silent=True) or {}
        name=str(data.get("name","")).strip()
        theme=data.get("theme")
        if not name or not isinstance(theme,dict): return jsonify({"error":"Nome e tema são obrigatórios."}),400
        theme=normalize_theme(theme)
        theme.update({"id":f"custom-{int(time.time()*1000)}","name":name,"description":str(data.get("description","")).strip()})
        themes=read_themes();themes.append(theme)
        manager.config_mgr.update_key("CUSTOM_THEMES",json.dumps(themes,ensure_ascii=False))
        return jsonify(theme),201

    @app.route("/api/v1/themes/<theme_id>", methods=["PUT"])
    @require_permission("settings", "admin")
    def update_theme(theme_id):
        data=request.get_json(silent=True) or {}
        name=str(data.get("name","")).strip()
        theme=data.get("theme")
        if not name or not isinstance(theme,dict): return jsonify({"error":"Nome e tema são obrigatórios."}),400
        themes=read_themes();found=False
        for item in themes:
            if str(item.get("id"))==theme_id:
                item.update(normalize_theme(theme));item.update({"id":theme_id,"name":name,"description":str(data.get("description","")).strip()});found=True;break
        if not found:return jsonify({"error":"Tema não encontrado."}),404
        manager.config_mgr.update_key("CUSTOM_THEMES",json.dumps(themes,ensure_ascii=False))
        return jsonify(next(item for item in themes if str(item.get("id"))==theme_id))

    @app.route("/api/v1/themes/<theme_id>", methods=["DELETE"])
    @require_permission("settings", "admin")
    def delete_theme(theme_id):
        themes=read_themes();new=[t for t in themes if str(t.get("id"))!=theme_id]
        if len(new)==len(themes):return jsonify({"error":"Tema não encontrado."}),404
        manager.config_mgr.update_key("CUSTOM_THEMES",json.dumps(new,ensure_ascii=False))
        return jsonify({"status":"removido"})

    @app.route("/api/v1/channels", methods=["POST"])
    @require_permission("channels", "create")
    def create_channel():
        data=dict(request.get_json(silent=True) or {})
        channel_id=manager.db.create_channel(data)
        if channel_id is None:return jsonify({"error":"Canal inválido ou URL já cadastrada."}),400
        message=f"Canal '{data.get('name','')}' criado manualmente."
        process_logs.appendleft({"timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"level":"success","message":message})
        if add_notification:add_notification("success","Canal criado",message,source="Canais",path="/channels")
        return jsonify(next(c for c in manager.db.list_channels() if c["id"]==channel_id)),201

    @app.route("/api/v1/channels/<int:channel_id>", methods=["DELETE"])
    @require_permission("channels", "delete")
    def delete_channel(channel_id):
        if not manager.db.delete_channel(channel_id):return jsonify({"error":"Canal não encontrado."}),404
        message=f"Canal #{channel_id} removido manualmente."
        process_logs.appendleft({"timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"level":"warning","message":message})
        if add_notification:add_notification("warning","Canal removido",message,source="Canais",path="/channels")
        return jsonify({"status":"removido","id":channel_id})

    @app.route("/api/v1/users/avatar", methods=["POST"])
    @require_permission("users", "edit")
    def upload_user_avatar():
        image=request.files.get("image")
        if not image or not image.filename:return jsonify({"error":"Nenhuma imagem foi enviada."}),400
        ext=os.path.splitext(image.filename)[1].lower()
        if ext not in {".png",".jpg",".jpeg",".webp",".gif"}:return jsonify({"error":"Formato de imagem não permitido."}),400
        directory=os.path.join(manager.base_dir,"frontend","static","uploads","avatars")
        os.makedirs(directory,exist_ok=True)
        filename=f"avatar_{int(time.time()*1000)}_{secure_filename(image.filename)}"
        image.save(os.path.join(directory,filename))
        return jsonify({"url":f"/static/uploads/avatars/{filename}"})

    return monitor
