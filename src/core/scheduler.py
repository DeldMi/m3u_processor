"""Configuração central do APScheduler."""

from datetime import datetime
from typing import Any, Callable


def configure_scheduler(scheduler: Any, manager: Any, sync_job: Callable[[], None], health_job: Callable[[], None]) -> None:
    """Recarrega os jobs a partir da configuração atual do projeto."""
    scheduler.remove_all_jobs()
    cfg = manager.config_mgr.get_all()
    scheduler.add_job(
        health_job,
        "interval",
        seconds=max(15, cfg.get("HEALTH_CHECK_INTERVAL_SECONDS", 60)),
        id="m3u_health_job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(),
    )

    mode = cfg.get("SCHEDULE_MODE", "DISABLED")
    if mode == "INTERVAL":
        scheduler.add_job(
            sync_job,
            "interval",
            hours=max(1, cfg.get("SCHEDULE_INTERVAL_HOURS", 12)),
            id="m3u_sync_job",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
    elif mode == "CRON":
        try:
            hour, minute = cfg.get("SCHEDULE_CRON_TIME", "03:00").split(":")
            scheduler.add_job(
                sync_job,
                "cron",
                hour=int(hour),
                minute=int(minute),
                id="m3u_sync_job",
                replace_existing=True,
                max_instances=1,
                coalesce=True,
            )
        except (ValueError, TypeError):
            # Configuração inválida não deve derrubar o processo principal.
            pass
