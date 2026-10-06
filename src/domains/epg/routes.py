"""Protected CRUD and synchronization endpoints for XMLTV guides."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from flask import jsonify, request
from src.auth import require_permission
from .service import download_xmltv, normalize_xmltv, save_xmltv


def _source_summary(source):
    return {key: value for key, value in source.items() if key != "file_path"} if source else None


def _request_data():
    if request.mimetype == "multipart/form-data":
        return request.form
    return request.get_json(silent=True) or {}


def register_epg_routes(app, manager):
    @app.route("/api/v1/epg/sources", methods=["GET"])
    @require_permission("epg", "view")
    def list_epg_sources():
        return jsonify(manager.db.list_epg_sources())

    @app.route("/api/v1/epg/channels", methods=["GET"])
    @require_permission("epg", "view")
    def list_epg_channels():
        query = str(request.args.get("search", "")).strip().lower()
        channels = manager.db.list_channels(search=query or None, sort="name")
        return jsonify(channels)

    @app.route("/api/v1/epg/channels/<int:channel_id>", methods=["PATCH"])
    @require_permission("epg", "edit")
    def update_epg_channel(channel_id):
        data = request.get_json(silent=True) or {}
        values = {key: data[key] for key in ("epg_source_id", "epg_channel_id") if key in data}
        if set(values) != {"epg_source_id", "epg_channel_id"}:
            return jsonify({"error": "Informe a fonte EPG e o ID XMLTV do canal."}), 400
        if not manager.db.update_channel(channel_id, values):
            return jsonify({"error": "Canal ou fonte EPG inválida."}), 404
        return jsonify(next((channel for channel in manager.db.list_channels() if channel["id"] == channel_id), {}))

    @app.route("/api/v1/epg/channels/<int:channel_id>/details", methods=["PATCH"])
    @require_permission("channels", "edit")
    def update_epg_channel_details(channel_id):
        data = request.get_json(silent=True) or {}
        allowed = {key: data[key] for key in ("name", "channel_number", "tvg_id", "group_title", "country", "state", "city", "category", "url", "logo") if key in data}
        if not allowed or not manager.db.update_channel(channel_id, allowed):
            return jsonify({"error": "Canal não encontrado ou sem campos válidos."}), 400
        return jsonify(next((channel for channel in manager.db.list_channels() if channel["id"] == channel_id), {}))

    @app.route("/api/v1/epg/programmes", methods=["GET"])
    @require_permission("epg", "view")
    def list_epg_programmes():
        channel_id = request.args.get("channel_id", type=int)
        return jsonify(manager.db.list_epg_programmes(channel_id))

    @app.route("/api/v1/epg/programmes", methods=["POST"])
    @require_permission("epg", "create")
    def create_epg_programme():
        data = request.get_json(silent=True) or {}
        programme_id = manager.db.create_epg_programme(data.get("channel_id"), data)
        if programme_id is None:
            return jsonify({"error": "Informe um canal, título e intervalo de horário válido."}), 400
        return jsonify(next(item for item in manager.db.list_epg_programmes(data.get("channel_id")) if item["id"] == programme_id)), 201

    @app.route("/api/v1/epg/programmes/<int:programme_id>", methods=["PUT"])
    @require_permission("epg", "edit")
    def update_epg_programme(programme_id):
        if not manager.db.update_epg_programme(programme_id, request.get_json(silent=True) or {}):
            return jsonify({"error": "Programação inválida ou não encontrada."}), 400
        return jsonify(next(item for item in manager.db.list_epg_programmes() if item["id"] == programme_id))

    @app.route("/api/v1/epg/programmes/<int:programme_id>", methods=["DELETE"])
    @require_permission("epg", "delete")
    def delete_epg_programme(programme_id):
        if not manager.db.delete_epg_programme(programme_id):
            return jsonify({"error": "Programação não encontrada."}), 404
        return jsonify({"status": "removida", "id": programme_id})

    @app.route("/api/v1/epg/sources", methods=["POST"])
    @require_permission("epg", "create")
    def create_epg_source():
        upload = request.files.get("file")
        data = _request_data()
        name = str(data.get("name", "")).strip()
        source_url = str(data.get("url", "")).strip()
        if not name:
            return jsonify({"error": "Informe o nome da guia."}), 400
        try:
            if upload:
                extension = Path(upload.filename or "").suffix.lower()
                if extension not in {".xml", ".gz"}:
                    return jsonify({"error": "Envie um arquivo .xml ou .gz."}), 400
                content, channel_count = normalize_xmltv(upload.stream.read(50 * 1024 * 1024 + 1), compressed=extension == ".gz")
            else:
                if not source_url:
                    return jsonify({"error": "Informe uma URL XMLTV."}), 400
                content, channel_count = download_xmltv(source_url, manager.config_mgr.get_all()["USER_AGENT"])
            file_path = save_xmltv(manager.base_dir, content)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        source_id = manager.db.create_epg_source(name, source_url, file_path)
        if source_id is None:
            os.remove(file_path)
            return jsonify({"error": "Não foi possível cadastrar a guia."}), 400
        manager.db.update_epg_source(source_id, {"channel_count": channel_count, "synced_at": datetime.now().isoformat(timespec="seconds")})
        return jsonify(_source_summary(manager.db.get_epg_source(source_id))), 201

    @app.route("/api/v1/epg/sources/<int:source_id>", methods=["PUT"])
    @require_permission("epg", "edit")
    def update_epg_source(source_id):
        source = manager.db.get_epg_source(source_id)
        if not source:
            return jsonify({"error": "Guia não encontrada."}), 404
        upload = request.files.get("file")
        data = _request_data()
        name = str(data.get("name", source["name"])).strip()
        source_url = str(data.get("url", source["source_url"])).strip()
        if not name:
            return jsonify({"error": "Informe o nome da guia."}), 400
        changes = {"name": name, "source_url": source_url}
        if upload:
            extension = Path(upload.filename or "").suffix.lower()
            if extension not in {".xml", ".gz"}:
                return jsonify({"error": "Envie um arquivo .xml ou .gz."}), 400
            try:
                content, channel_count = normalize_xmltv(upload.stream.read(50 * 1024 * 1024 + 1), compressed=extension == ".gz")
                changes.update({"file_path": save_xmltv(manager.base_dir, content), "channel_count": channel_count, "synced_at": datetime.now().isoformat(timespec="seconds"), "last_error": ""})
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400
        elif source_url and source_url != source["source_url"]:
            try:
                content, channel_count = download_xmltv(source_url, manager.config_mgr.get_all()["USER_AGENT"])
                changes.update({"file_path": save_xmltv(manager.base_dir, content), "channel_count": channel_count, "synced_at": datetime.now().isoformat(timespec="seconds"), "last_error": ""})
            except ValueError as exc:
                manager.db.update_epg_source(source_id, {"last_error": str(exc)})
                return jsonify({"error": str(exc)}), 400
        manager.db.update_epg_source(source_id, changes)
        new_path = changes.get("file_path")
        old_path = source.get("file_path")
        allowed_dir = os.path.abspath(os.path.join(manager.base_dir, "data", "epg_sources")) + os.sep
        if new_path and old_path and os.path.abspath(old_path).startswith(allowed_dir):
            try:
                os.remove(old_path)
            except OSError:
                pass
        return jsonify(_source_summary(manager.db.get_epg_source(source_id)))

    @app.route("/api/v1/epg/sources/<int:source_id>/sync", methods=["POST"])
    @require_permission("epg", "execute")
    def sync_epg_source(source_id):
        source = manager.db.get_epg_source(source_id)
        if not source:
            return jsonify({"error": "Guia não encontrada."}), 404
        if not source["source_url"]:
            return jsonify({"error": "Esta guia foi enviada como arquivo e não possui URL para sincronizar."}), 400
        try:
            content, channel_count = download_xmltv(source["source_url"], manager.config_mgr.get_all()["USER_AGENT"])
            file_path = save_xmltv(manager.base_dir, content)
        except ValueError as exc:
            manager.db.update_epg_source(source_id, {"last_error": str(exc)})
            return jsonify({"error": str(exc)}), 400
        manager.db.update_epg_source(source_id, {"file_path": file_path, "channel_count": channel_count, "synced_at": datetime.now().isoformat(timespec="seconds"), "last_error": ""})
        old_path = source.get("file_path")
        if old_path and os.path.abspath(old_path).startswith(os.path.abspath(os.path.join(manager.base_dir, "data", "epg_sources")) + os.sep):
            try:
                os.remove(old_path)
            except OSError:
                pass
        return jsonify(_source_summary(manager.db.get_epg_source(source_id)))

    @app.route("/api/v1/epg/sources/<int:source_id>", methods=["DELETE"])
    @require_permission("epg", "delete")
    def delete_epg_source(source_id):
        source = manager.db.get_epg_source(source_id)
        if not source:
            return jsonify({"error": "Guia não encontrada."}), 404
        if not manager.db.delete_epg_source(source_id):
            return jsonify({"error": "Não foi possível remover a guia."}), 500
        source_path = source.get("file_path")
        allowed_dir = os.path.abspath(os.path.join(manager.base_dir, "data", "epg_sources")) + os.sep
        if source_path and os.path.abspath(source_path).startswith(allowed_dir):
            try:
                os.remove(source_path)
            except OSError:
                pass
        return jsonify({"status": "removida", "id": source_id})

    return app