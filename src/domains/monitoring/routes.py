"""Rotas de monitoramento, diagnóstico e notificações operacionais."""
from __future__ import annotations
from datetime import datetime
from flask import jsonify, request
from src.auth import require_role, current_user
from src.domains.authz.service import has_permission
from .service import ResourceMonitor

def register_monitoring_routes(app, manager, process_state, process_logs, notifications, monitor: ResourceMonitor, add_notification=None):
    def allowed(resource: str, action: str = "view") -> bool:
        user=current_user(manager.db); return bool(user and has_permission(manager.db,int(user["id"]),user["role"],resource,action))
    @app.route("/api/v1/resources")
    @require_role("viewer")
    def resources(): return jsonify(monitor.payload(manager.base_dir,process_state["status"] in ("Executando...","Pausado")))
    @app.route("/api/v1/resources/diagnostics")
    @require_role("viewer")
    def resource_diagnostics(): return jsonify(monitor.diagnose(manager.base_dir,process_state["status"] in ("Executando...","Pausado")))
    @app.route("/api/v1/resources/gc",methods=["POST"])
    @require_role("admin")
    def resource_gc():
        result=monitor.clear_python_caches(); notice=add_notification or (lambda level,title,message,source="Execução",path="",details="":notifications.append({"id":f"{datetime.now().timestamp()}-memory","level":level,"title":title,"message":message,"timestamp":datetime.now().isoformat(timespec="seconds"),"source":source,"path":path,"details":details}))
        notice("success","Memória limpa",f"Coleta executada: {result['collected_objects']} objetos.",source="Manutenção",path="/settings/resources"); return jsonify(result)
    @app.route("/api/v1/notifications")
    @require_role("viewer")
    def get_notifications(): return jsonify(list(notifications))
    @app.route("/api/v1/channels",methods=["POST"])
    @require_role("editor")
    def create_channel():
        data=dict(request.get_json(silent=True) or {})
        channel_id=manager.db.create_channel(data)
        if channel_id is None: return jsonify({"error":"Canal inválido ou URL já cadastrada."}),400
        message=f"Canal '{data.get('name','')}' criado manualmente."; process_logs.appendleft({"timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"level":"success","message":message})
        if add_notification: add_notification("success","Canal criado",message,source="Canais",path="/channels")
        return jsonify(next(c for c in manager.db.list_channels() if c["id"]==channel_id)),201
    @app.route("/api/v1/channels/<int:channel_id>",methods=["DELETE"])
    @require_role("editor")
    def delete_channel(channel_id):
        if not manager.db.delete_channel(channel_id): return jsonify({"error":"Canal não encontrado."}),404
        message=f"Canal #{channel_id} removido manualmente."; process_logs.appendleft({"timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"level":"warning","message":message})
        if add_notification: add_notification("warning","Canal removido",message,source="Canais",path="/channels")
        return jsonify({"status":"removido","id":channel_id})
    return monitor
