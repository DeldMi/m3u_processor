"""Rotas de monitoramento, diagnóstico e notificações operacionais."""

from __future__ import annotations

from datetime import datetime
from flask import jsonify

from src.auth import require_role, current_user
from src.domains.authz.service import has_permission
from .service import ResourceMonitor


def register_monitoring_routes(app, manager, process_state, process_logs, notifications, monitor: ResourceMonitor):
    notice_state = {"key": ""}

    def allowed(resource: str, action: str = "view") -> bool:
        user = current_user(manager.db)
        return bool(user and has_permission(manager.db, int(user["id"]), user["role"], resource, action))

    @app.route("/api/v1/resources")
    @require_role("viewer")
    def resources():
        return jsonify(monitor.payload(manager.base_dir, process_state["status"] in ("Executando...", "Pausado")))

    @app.route("/api/v1/resources/diagnostics")
    @require_role("viewer")
    def resource_diagnostics():
        return jsonify(monitor.diagnose(manager.base_dir, process_state["status"] in ("Executando...", "Pausado")))

    @app.route("/api/v1/resources/gc", methods=["POST"])
    @require_role("admin")
    def resource_gc():
        result = monitor.clear_python_caches()
        notifications.append({"level": "success", "title": "Memória limpa", "message": f"Coleta executada: {result['collected_objects']} objetos.", "timestamp": datetime.now().isoformat(timespec="seconds")})
        return jsonify(result)

    @app.route("/api/v1/notifications")
    @require_role("viewer")
    def get_notifications():
        last_log = str(process_state.get("ultimo_log") or "").strip()
        key = f"{process_state.get('status')}|{last_log}"
        if last_log and key != notice_state["key"]:
            notice_state["key"] = key
            offline = process_state.get("internet_online") is False and "Internet" in last_log
            level = "warning" if offline else ("error" if process_state.get("status") == "Erro" else "success")
            notifications.append({"level": level, "title": "Health Check" if offline or "Saúde" in last_log else "Execução", "message": last_log, "timestamp": datetime.now().isoformat(timespec="seconds")})
        return jsonify(list(notifications))

    return monitor
