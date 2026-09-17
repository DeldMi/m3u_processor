"""Rotas de monitoramento, diagnóstico e notificações operacionais."""

from __future__ import annotations

from flask import jsonify

from src.auth import require_role, current_user
from src.domains.authz.service import has_permission
from .service import ResourceMonitor


def register_monitoring_routes(app, manager, process_state, process_logs, notifications, monitor: ResourceMonitor):
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
        notifications.append({"level": "success", "title": "Memória limpa", "message": f"Coleta executada: {result['collected_objects']} objetos.", "timestamp": __import__("datetime").datetime.now().isoformat(timespec="seconds")})
        return jsonify(result)

    @app.route("/api/v1/notifications")
    @require_role("viewer")
    def get_notifications():
        return jsonify(list(notifications))

    return monitor
