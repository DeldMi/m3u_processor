"""Serviços de conectividade e saúde da internet.

Este módulo não conhece Flask: recebe a configuração por injeção e devolve
um resultado serializável, facilitando testes e reutilização pelo scheduler.
"""

import platform
import socket
import subprocess
import time
from urllib.parse import urlparse
from typing import Any, Mapping


def resolve_ping_host(target: str) -> str:
    """Converte IP, domínio ou URL em um host apropriado para teste."""
    value = str(target or "").strip()
    if not value:
        return "1.1.1.1"
    parsed = urlparse(value if "://" in value else f"//{value}")
    host = parsed.hostname or value.split("/", 1)[0]
    return host.strip("[]")


def check_internet_health(config: Mapping[str, Any]) -> dict[str, Any]:
    """Executa um teste ICMP, com fallback TCP/443 quando necessário."""
    target = str(config.get("INTERNET_TEST_TARGET") or "1.1.1.1").strip()
    interval_seconds = max(1, int(config.get("INTERNET_PING_INTERVAL_SECONDS", 5)))
    timeout_seconds = max(0.2, min(float(config.get("INTERNET_PING_TIMEOUT_SECONDS", 2)), 30.0))
    host = resolve_ping_host(target)
    start = time.perf_counter()
    system = platform.system().lower()
    command = (
        ["ping", "-n", "1", "-w", str(int(timeout_seconds * 1000)), host]
        if system == "windows"
        else ["ping", "-c", "1", "-W", str(max(1, int(timeout_seconds))), host]
    )
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds + 2,
            check=False,
        )
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        if result.returncode == 0:
            return {
                "online": True,
                "target": target,
                "host": host,
                "latency_ms": latency_ms,
                "interval_seconds": interval_seconds,
                "timeout_seconds": timeout_seconds,
                "error": "",
            }
        return {
            "online": False,
            "target": target,
            "host": host,
            "latency_ms": latency_ms,
            "interval_seconds": interval_seconds,
            "timeout_seconds": timeout_seconds,
            "error": "Destino sem resposta",
        }
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        try:
            fallback_start = time.perf_counter()
            with socket.create_connection((host, 443), timeout=timeout_seconds):
                latency_ms = round((time.perf_counter() - fallback_start) * 1000, 2)
                return {
                    "online": True,
                    "target": target,
                    "host": host,
                    "latency_ms": latency_ms,
                    "interval_seconds": interval_seconds,
                    "timeout_seconds": timeout_seconds,
                    "error": "Ping ICMP indisponível; conexão TCP/443 confirmada",
                }
        except OSError:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return {
                "online": False,
                "target": target,
                "host": host,
                "latency_ms": latency_ms,
                "interval_seconds": interval_seconds,
                "timeout_seconds": timeout_seconds,
                "error": str(exc),
            }
