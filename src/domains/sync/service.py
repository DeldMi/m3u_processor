"""Serviço de execução do pipeline de sincronização M3U."""

import asyncio
import os
import shutil
import sqlite3
import threading
import time
from collections import deque
from datetime import datetime
from typing import Any, Callable


class PipelineInterrupted(Exception):
    """Sinaliza cancelamento solicitado pelo usuário."""


def execute_pipeline(
    *,
    manager: Any,
    process_state: dict[str, Any],
    process_logs: deque,
    pause_requested: threading.Event,
    stop_requested: threading.Event,
    pipeline_lock: threading.Lock,
    state: dict[str, Any],
    min_free_space_bytes: int,
    update_log: Callable[[str, str, int | None], None],
    publication_mode: str = "NONE",
) -> None:
    """Executa o pipeline completo sem acoplar a lógica ao Flask."""
    if process_state["status"] == "Executando..." or not pipeline_lock.acquire(blocking=False):
        return

    active_run_id = None
    loop = None

    def checkpoint(_stage: str) -> None:
        if stop_requested.is_set():
            raise PipelineInterrupted("Execução interrompida pelo usuário.")
        while pause_requested.is_set() and not stop_requested.is_set():
            process_state["status"] = "Pausado"
            time.sleep(0.2)
        if stop_requested.is_set():
            raise PipelineInterrupted("Execução interrompida pelo usuário.")
        if process_state["status"] == "Pausado":
            process_state["status"] = "Executando..."
            update_log("Execução retomada.", "info", active_run_id)

    try:
        if shutil.disk_usage(manager.base_dir).free < min_free_space_bytes:
            process_state["status"] = "Erro"
            process_state["ultimo_log"] = "Espaço em disco insuficiente para executar a sincronização."
            return

        stop_requested.clear()
        pause_requested.clear()
        active_run_id = manager.db.start_process_run()
        state["active_run_id"] = active_run_id
        process_state["status"] = "Executando..."
        update_log("Iniciando auditoria completa...", "info", active_run_id)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            manager.sync_and_audit(progress_callback=lambda message: update_log(message, "info", active_run_id), control_callback=checkpoint, publication_mode=publication_mode)
        )

        process_state["total_canais"] = result.get("total", 0)
        process_state["canais_online"] = result.get("online", 0)
        process_state["canais_offline"] = result.get("offline", 0)
        process_state["manifestos"] = result.get("partitions", [])
        process_state["status"] = "Concluido"
        process_state["ultimo_log"] = (
            f"Sucesso! {result.get('online', 0)} canais operantes salvos em "
            f"{len(result.get('partitions', []))} lista(s). Log: {result.get('log_file')}"
        )
        update_log(process_state["ultimo_log"], "success", active_run_id)
        manager.db.finish_process_run(active_run_id, "Concluido", result, process_state["ultimo_log"])
    except PipelineInterrupted as exc:
        process_state["status"] = "Interrompido"
        process_state["ultimo_log"] = str(exc)
        update_log(process_state["ultimo_log"], "warning", active_run_id)
        manager.db.finish_process_run(active_run_id, "Interrompido", {}, process_state["ultimo_log"])
    except (OSError, sqlite3.OperationalError) as exc:
        process_state["status"] = "Erro"
        process_state["ultimo_log"] = "Falha de armazenamento durante a execução. Libere espaço em disco e tente novamente."
        if "database or disk is full" not in str(exc).lower() and "no space left" not in str(exc).lower():
            process_state["ultimo_log"] = f"Falha de armazenamento: {exc}"
        update_log(process_state["ultimo_log"], "error", active_run_id)
        if active_run_id is not None:
            try:
                manager.db.finish_process_run(active_run_id, "Erro", {}, process_state["ultimo_log"])
            except (OSError, sqlite3.OperationalError):
                pass
    except Exception as exc:
        process_state["status"] = "Erro"
        process_state["ultimo_log"] = f"Falha na execucao: {exc}"
        update_log(process_state["ultimo_log"], "error", active_run_id)
        manager.db.finish_process_run(active_run_id, "Erro", {}, process_state["ultimo_log"])
    finally:
        pause_requested.clear()
        stop_requested.clear()
        state["active_run_id"] = None
        if loop is not None:
            loop.close()
        pipeline_lock.release()


def execute_health_check(*, manager: Any, process_state: dict[str, Any], pipeline_lock: threading.Lock) -> None:
    """Atualiza a saúde dos canais sem regenerar playlists."""
    if pipeline_lock.locked() or shutil.disk_usage(manager.base_dir).free < 512 * 1024 * 1024:
        return
    try:
        result = asyncio.run(manager.refresh_channel_health())
        process_state["total_canais"] = result["total"]
        process_state["canais_online"] = result["online"]
        process_state["canais_offline"] = result["offline"]
        process_state["ultimo_log"] = f"Saúde atualizada: {result['online']} online, {result['offline']} offline."
    except (OSError, sqlite3.OperationalError):
        return
