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
            "SCHEDULE_MODE": (config.get("SCHEDULE_MODE", "DISABLED") or "DISABLED").upper(),
            "SCHEDULE_INTERVAL_HOURS": self._safe_int(config.get("SCHEDULE_INTERVAL_HOURS", 12), 12),
            "SCHEDULE_CRON_TIME": config.get("SCHEDULE_CRON_TIME", "03:00"),
            "WEB_HOST": config.get("WEB_HOST", "0.0.0.0"),
            "WEB_PORT": self._safe_int(config.get("WEB_PORT", 5000), 5000)
        }

    def update_key(self, key: str, value: str):
        set_key(self.env_path, key, str(value))