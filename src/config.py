import os
from dotenv import dotenv_values, set_key

class ConfigManager:
    def __init__(self, root_dir: str):
        self.env_path = os.path.join(root_dir, ".env")
        if not os.path.exists(self.env_path):
            with open(self.env_path, "w", encoding="utf-8") as f:
                f.write("# Configuracao Inicial\n")

    def get_all(self) -> dict:
        config = dotenv_values(self.env_path)
        return {
            "MAX_CHANNELS_PER_FILE": int(config.get("MAX_CHANNELS_PER_FILE", 400)),
            "CONCURRENCY_LIMIT": int(config.get("CONCURRENCY_LIMIT", 50)),
            "REQUEST_TIMEOUT": int(config.get("REQUEST_TIMEOUT", 6)),
            "USER_AGENT": config.get("USER_AGENT", "VLC/3.0.18 LibVLC/3.0.18"),
            "REMOTE_M3U_URLS": config.get("REMOTE_M3U_URLS", ""),
            "SCHEDULE_MODE": config.get("SCHEDULE_MODE", "DISABLED").upper(),
            "SCHEDULE_INTERVAL_HOURS": int(config.get("SCHEDULE_INTERVAL_HOURS", 12)),
            "SCHEDULE_CRON_TIME": config.get("SCHEDULE_CRON_TIME", "03:00"),
            "WEB_HOST": config.get("WEB_HOST", "127.0.0.1"),
            "WEB_PORT": int(config.get("WEB_PORT", 5000))
        }

    def update_key(self, key: str, value: str):
        set_key(self.env_path, key, str(value))