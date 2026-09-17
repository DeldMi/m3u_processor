"""Configuração central e não sobreposta do APScheduler.

O health-check pode durar mais que o intervalo configurado quando há muitos
canais. Um ``interval`` com ``max_instances=1`` então gera avisos de execução
ignorada. Para evitar sobreposição real e ruído no log, o health-check é
agendado como uma execução única e agenda a próxima somente depois de terminar.
"""

from datetime import datetime, timedelta
from typing import Any, Callable

HEALTH_JOB_ID = "m3u_health_job"
SYNC_JOB_ID = "m3u_sync_job"


def _schedule_next_health(scheduler: Any, health_job: Callable[[], None], interval_seconds: int) -> None:
    """Agenda a próxima verificação após a execução atual terminar."""
    if not scheduler.running:
        return
    scheduler.add_job(
        _run_health_once,
        "date",
        run_date=datetime.now() + timedelta(seconds=interval_seconds),
        args=[scheduler, health_job, interval_seconds],
        id=HEALTH_JOB_ID,
        replace_existing=True,
    )


def _run_health_once(scheduler: Any, health_job: Callable[[], None], interval_seconds: int) -> None:
    """Executa um health-check e agenda a próxima execução sem overlap."""
    try:
        health_job()
    finally:
        _schedule_next_health(scheduler, health_job, interval_seconds)


def configure_scheduler(scheduler: Any, manager: Any, sync_job: Callable[[], None], health_job: Callable[[], None]) -> None:
    """Recarrega os jobs a partir da configuração atual do projeto."""
    scheduler.remove_all_jobs()
    cfg = manager.config_mgr.get_all()
    health_interval = max(15, int(cfg.get("HEALTH_CHECK_INTERVAL_SECONDS", 60)))

    # A primeira verificação ocorre imediatamente. As seguintes são encadeadas
    # somente após a anterior terminar, evitando max_instances atingido.
    scheduler.add_job(
        _run_health_once,
        "date",
        run_date=datetime.now(),
        args=[scheduler, health_job, health_interval],
        id=HEALTH_JOB_ID,
        replace_existing=True,
    )

    mode = cfg.get("SCHEDULE_MODE", "DISABLED")
    if mode == "INTERVAL":
        scheduler.add_job(
            sync_job,
            "interval",
            hours=max(1, int(cfg.get("SCHEDULE_INTERVAL_HOURS", 12))),
            id=SYNC_JOB_ID,
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
                id=SYNC_JOB_ID,
                replace_existing=True,
                max_instances=1,
                coalesce=True,
            )
        except (ValueError, TypeError):
            # Configuração inválida não deve derrubar o processo principal.
            pass
