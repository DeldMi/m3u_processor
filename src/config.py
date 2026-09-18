import os
import secrets
from dotenv import dotenv_values, set_key


class ConfigManager:
    """Leitor/escritor central de configuração do aplicativo."""

    # Estes valores jamais devem ser devolvidos ao frontend.
    SECRET_KEYS = frozenset({"SECRET_KEY", "API_TOKEN", "ADMIN_INITIAL_PASSWORD"})

    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.env_path = os.path.join(root_dir, ".env")
        if not os.path.exists(self.env_path):
            with open(self.env_path, "w", encoding="utf-8") as f:
                f.write("# Configuracao Inicial\n")
        self._ensure_secret("SECRET_KEY", 48)

    def _ensure_secret(self, key: str, byte_length: int):
        """Garante segredo persistente para evitar fallback público/fixo."""
        config = dotenv_values(self.env_path)
        value = str(config.get(key) or "").strip()
        if not value:
            set_key(self.env_path, key, secrets.token_urlsafe(byte_length))
            try:
                os.chmod(self.env_path, 0o600)
            except OSError:
                # chmod pode não existir/ser aplicável em alguns ambientes Windows.
                pass

    @staticmethod
    def _safe_int(value, default):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def get_all(self) -> dict:
        config = dotenv_values(self.env_path)
        return {
            "SECRET_KEY": config.get("SECRET_KEY", ""),
            "API_TOKEN": config.get("API_TOKEN", ""),
            "ADMIN_INITIAL_PASSWORD": config.get("ADMIN_INITIAL_PASSWORD", ""),
            "ALLOW_INSECURE_TLS": str(config.get("ALLOW_INSECURE_TLS", "0")).strip().lower() in {"1", "true", "yes"},
            "MAX_CHANNELS_PER_FILE": self._safe_int(config.get("MAX_CHANNELS_PER_FILE", 400), 400),
            "CONCURRENCY_LIMIT": self._safe_int(config.get("CONCURRENCY_LIMIT", 50), 50),
            "REQUEST_TIMEOUT": self._safe_int(config.get("REQUEST_TIMEOUT", 6), 6),
            "USER_AGENT": config.get("USER_AGENT", "VLC/3.0.18 LibVLC/3.0.18"),
            "REMOTE_M3U_URLS": config.get("REMOTE_M3U_URLS", ""),
            "EPG_URLS": config.get("EPG_URLS", "https://iptv-epg.org/files/brazil.xml.gz"),
            "BASE_URL": (config.get("BASE_URL", "http://127.0.0.1:5000") or "http://127.0.0.1:5000").rstrip("/"),
            "PUBLIC_BASE_URL": (config.get("PUBLIC_BASE_URL", "http://127.0.0.1:8080") or "http://127.0.0.1:8080").rstrip("/"),
            "SCHEDULE_MODE": (config.get("SCHEDULE_MODE", "DISABLED") or "DISABLED").upper(),
            "SCHEDULE_INTERVAL_HOURS": self._safe_int(config.get("SCHEDULE_INTERVAL_HOURS", 12), 12),
            "SCHEDULE_CRON_TIME": config.get("SCHEDULE_CRON_TIME", "03:00"),
            "HEALTH_CHECK_INTERVAL_SECONDS": self._safe_int(config.get("HEALTH_CHECK_INTERVAL_SECONDS", 60), 60),
            "SYNC_PUBLICATION_MODE": (config.get("SYNC_PUBLICATION_MODE", "NONE") or "NONE").upper(),
            "RESOURCE_HISTORY_SIZE": self._safe_int(config.get("RESOURCE_HISTORY_SIZE", 120), 120),
            "RAM_ALERT_PERCENT": self._safe_int(config.get("RAM_ALERT_PERCENT", 70), 70),
            "RAM_CRITICAL_PERCENT": self._safe_int(config.get("RAM_CRITICAL_PERCENT", 85), 85),
            "DISK_ALERT_PERCENT": self._safe_int(config.get("DISK_ALERT_PERCENT", 80), 80),
            "DISK_CRITICAL_PERCENT": self._safe_int(config.get("DISK_CRITICAL_PERCENT", 90), 90),
            "INTERNET_TEST_TARGET": config.get("INTERNET_TEST_TARGET", "https://1.1.1.1"),
            "INTERNET_PING_INTERVAL_SECONDS": self._safe_int(config.get("INTERNET_PING_INTERVAL_SECONDS", 5), 5),
            "INTERNET_PING_TIMEOUT_SECONDS": self._safe_int(config.get("INTERNET_PING_TIMEOUT_SECONDS", 2), 2),
            "AUTO_UPDATE_XTEVE": config.get("AUTO_UPDATE_XTEVE", "0"),
            "NUMBER_OF_TUNERS": self._safe_int(config.get("NUMBER_OF_TUNERS", 1), 1),
            "EPG_SOURCE": config.get("EPG_SOURCE", "XEPG"),
            "API_INTERFACE_ENABLED": config.get("API_INTERFACE_ENABLED", "1"),
            "FILE_UPDATE_SCHEDULE": config.get("FILE_UPDATE_SCHEDULE", ""),
            "UPDATE_FILES_ON_STARTUP": config.get("UPDATE_FILES_ON_STARTUP", "0"),
            "TEMP_FILES_LOCATION": config.get("TEMP_FILES_LOCATION", ""),
            "IMAGE_CACHING": config.get("IMAGE_CACHING", "1"),
            "REPLACE_MISSING_PROGRAM_IMAGES": config.get("REPLACE_MISSING_PROGRAM_IMAGES", "1"),
            "STREAM_BUFFER_ENABLED": config.get("STREAM_BUFFER_ENABLED", "0"),
            "UDPPROXY_ADDRESS": config.get("UDPPROXY_ADDRESS", ""),
            "BUFFER_SIZE_MB": self._safe_int(config.get("BUFFER_SIZE_MB", 32), 32),
            "CLIENT_CONNECTION_TIMEOUT_MS": self._safe_int(config.get("CLIENT_CONNECTION_TIMEOUT_MS", 5000), 5000),
            "FFMPEG_BINARY_PATH": config.get("FFMPEG_BINARY_PATH", ""),
            "FFMPEG_OPTIONS": config.get("FFMPEG_OPTIONS", ""),
            "VLC_BINARY_PATH": config.get("VLC_BINARY_PATH", ""),
            "VLC_OPTIONS": config.get("VLC_OPTIONS", ""),
            "BACKUP_LOCATION": config.get("BACKUP_LOCATION", ""),
            "BACKUPS_TO_KEEP": self._safe_int(config.get("BACKUPS_TO_KEEP", 5), 5),
            "WEB_AUTHENTICATION": config.get("WEB_AUTHENTICATION", "1"),
            "WEB_HOST": os.getenv("WEB_HOST", config.get("WEB_HOST", "0.0.0.0")),
            "WEB_PORT": self._safe_int(os.getenv("WEB_PORT", config.get("WEB_PORT", 5000)), 5000),
            "PUBLIC_HOST": os.getenv("PUBLIC_HOST", config.get("PUBLIC_HOST", "0.0.0.0")),
            "PUBLIC_PORT": self._safe_int(os.getenv("PUBLIC_PORT", config.get("PUBLIC_PORT", 8080)), 8080),
            # Compatibilidade com o gerenciamento de temas existente.
            "CUSTOM_THEMES": config.get("CUSTOM_THEMES", "[]"),
        }

    def get_public(self) -> dict:
        """Retorna somente configurações que podem ser exibidas pela SPA."""
        return {key: value for key, value in self.get_all().items() if key not in self.SECRET_KEYS}

    def update_key(self, key: str, value: str):
        # Segredos são mantidos fora da API pública. Fluxos internos de setup
        # podem gravá-los diretamente no .env quando necessário.
        if key in self.SECRET_KEYS:
            raise PermissionError(f"Configuração protegida: {key}")
        if key not in self.get_all():
            raise KeyError(f"Configuração desconhecida: {key}")
        set_key(self.env_path, key, str(value))
