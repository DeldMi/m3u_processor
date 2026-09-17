"""Métricas leves e multiplataforma para o painel operacional."""

from __future__ import annotations

import gc
import os
import platform
import shutil
import threading
import time
from collections import deque
from datetime import datetime
from typing import Any

try:
    import psutil
except ImportError:  # pragma: no cover - instalação mínima
    psutil = None


class ResourceMonitor:
    """Coleta métricas sem manter threads próprias nem caches ilimitados."""

    def __init__(self, history_size: int = 120) -> None:
        self.history = deque(maxlen=max(30, history_size))
        self._lock = threading.Lock()
        self._last = None

    def snapshot(self, base_dir: str, active_run: bool = False) -> dict[str, Any]:
        now = datetime.now().isoformat(timespec="seconds")
        if psutil is not None:
            vm = psutil.virtual_memory()
            process = psutil.Process(os.getpid())
            cpu = psutil.cpu_percent(interval=None)
            process_cpu = process.cpu_percent(interval=None)
            rss = process.memory_info().rss
            threads = process.num_threads()
            disk = shutil.disk_usage(base_dir)
            net = psutil.net_io_counters()
            data = {
                "timestamp": now,
                "platform": platform.platform(),
                "python": platform.python_version(),
                "cpu_percent": round(cpu, 1),
                "process_cpu_percent": round(process_cpu, 1),
                "cpu_count": psutil.cpu_count(logical=True) or 1,
                "ram_total_bytes": vm.total,
                "ram_used_bytes": vm.used,
                "ram_available_bytes": vm.available,
                "ram_percent": round(vm.percent, 1),
                "process_rss_bytes": rss,
                "process_threads": threads,
                "disk_total_bytes": disk.total,
                "disk_used_bytes": disk.used,
                "disk_free_bytes": disk.free,
                "disk_percent": round((disk.used / disk.total) * 100, 1) if disk.total else 0,
                "net_sent_bytes": net.bytes_sent,
                "net_recv_bytes": net.bytes_recv,
                "gc_counts": list(gc.get_count()),
                "active_run": active_run,
            }
        else:
            disk = shutil.disk_usage(base_dir)
            data = {
                "timestamp": now,
                "platform": platform.platform(),
                "python": platform.python_version(),
                "cpu_percent": 0,
                "process_cpu_percent": 0,
                "cpu_count": os.cpu_count() or 1,
                "ram_total_bytes": 0,
                "ram_used_bytes": 0,
                "ram_available_bytes": 0,
                "ram_percent": 0,
                "process_rss_bytes": 0,
                "process_threads": threading.active_count(),
                "disk_total_bytes": disk.total,
                "disk_used_bytes": disk.used,
                "disk_free_bytes": disk.free,
                "disk_percent": round((disk.used / disk.total) * 100, 1) if disk.total else 0,
                "net_sent_bytes": 0,
                "net_recv_bytes": 0,
                "gc_counts": list(gc.get_count()),
                "active_run": active_run,
            }
        with self._lock:
            self.history.append(data)
            self._last = data
        return data

    def payload(self, base_dir: str, active_run: bool = False) -> dict[str, Any]:
        current = self.snapshot(base_dir, active_run)
        with self._lock:
            history = list(self.history)
        return {"current": current, "history": history}

    def diagnose(self, base_dir: str, active_run: bool = False) -> dict[str, Any]:
        payload = self.payload(base_dir, active_run)
        current = payload["current"]
        history = payload["history"]
        warnings = []
        if current["ram_percent"] >= 85:
            warnings.append("Uso de memória acima do limite crítico de 85%.")
        elif current["ram_percent"] >= 70:
            warnings.append("Uso de memória acima do limite de alerta de 70%.")
        if current["disk_percent"] >= 90:
            warnings.append("Armazenamento acima de 90%.")
        if len(history) >= 10:
            old = history[max(0, len(history) - 10)]["process_rss_bytes"]
            new = history[-1]["process_rss_bytes"]
            if old and new > old * 1.20 and not current["active_run"]:
                warnings.append("A memória do processo cresceu mais de 20% durante o período observado.")
        return {"status": "warning" if warnings else "ok", "warnings": warnings, "metrics": current}

    def clear_python_caches(self) -> dict[str, Any]:
        before = self._last["process_rss_bytes"] if self._last else 0
        collected = gc.collect()
        after = psutil.Process(os.getpid()).memory_info().rss if psutil is not None else before
        return {"collected_objects": collected, "rss_before_bytes": before, "rss_after_bytes": after}
