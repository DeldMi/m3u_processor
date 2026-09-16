import os
from dotenv import dotenv_values, set_key

class ConfigManager:
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.env_path = os.path.join(root_dir, ".env")
        if not os.path.exists(self.env_path):
            with open(self.env_path, "w", encoding="utf-8") as f:
                f.write("# Configuracao Inicial\n")

    @staticmethod
    def _safe_int(value, default):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def get_all(self) -> dict:
        config = dotenv_values(self.env_path)
        return {
            "SECRET_KEY": config.get("SECRET_KEY", "m3u_processor_secret_key_fixed"),
            "API_TOKEN": config.get("API_TOKEN", ""),
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
            "PUBLIC_PORT": self._safe_int(os.getenv("PUBLIC_PORT", config.get("PUBLIC_PORT", 8080)), 8080)
        }

    def update_key(self, key: str, value: str):
        set_key(self.env_path, key, str(value))