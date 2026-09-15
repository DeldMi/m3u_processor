import os
import glob
import json
import asyncio
import logging
import aiohttp
from datetime import datetime
from typing import List, Dict, Any, Tuple
from src.parser import M3UParser
from src.checker import test_stream
from src.config import ConfigManager

# Silencia mensagens de erro de DNS de dominios inexistentes/mortos no terminal
logging.getLogger("aiohttp.connector").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

class PlaylistManager:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.input_dir = os.path.join(base_dir, "input")
        self.output_dir = os.path.join(base_dir, "output")
        self.logs_dir = os.path.join(base_dir, "logs")
        self.config_mgr = ConfigManager(base_dir)
        self._ensure_directories()

    def _ensure_directories(self):
        for path in [self.input_dir, self.output_dir, self.logs_dir]:
            os.makedirs(path, exist_ok=True)

    async def _fetch_remote_url(self, session: aiohttp.ClientSession, url: str) -> List[Dict[str, Any]]:
        try:
            cfg = self.config_mgr.get_all()
            headers = {"User-Agent": cfg["USER_AGENT"]}
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    text = await resp.text(errors="ignore")
                    return M3UParser.parse_text(text, source_identifier=url)
        except Exception:
            pass
        return []

    async def load_all_channels(self) -> List[Dict[str, Any]]:
        all_channels = []
        seen_urls = set()

        for ext in ("*.m3u", "*.m3u8", "*.txt"):
            for file_path in glob.glob(os.path.join(self.input_dir, ext)):
                for enc in ("utf-8", "latin-1", "cp1252"):
                    try:
                        with open(file_path, "r", encoding=enc) as f:
                            content = f.read()
                        extracted = M3UParser.parse_text(content, source_identifier=os.path.basename(file_path))
                        for ch in extracted:
                            if ch["url"] not in seen_urls:
                                seen_urls.add(ch["url"])
                                all_channels.append(ch)
                        break
                    except UnicodeDecodeError:
                        continue

        cfg = self.config_mgr.get_all()
        remote_str = cfg.get("REMOTE_M3U_URLS", "").strip()
        remote_urls = [u.strip() for u in remote_str.split(";") if u.strip().startswith("http")]

        if remote_urls:
            connector = aiohttp.TCPConnector(ssl=False, ttl_dns_cache=300)
            async with aiohttp.ClientSession(connector=connector) as session:
                tasks = [self._fetch_remote_url(session, u) for u in remote_urls]
                results = await asyncio.gather(*tasks)
                for channel_list in results:
                    for ch in channel_list:
                        if ch["url"] not in seen_urls:
                            seen_urls.add(ch["url"])
                            all_channels.append(ch)

        return all_channels

    async def validate_channels(self, channels: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        cfg = self.config_mgr.get_all()
        concurrency = cfg["CONCURRENCY_LIMIT"]
        timeout = cfg["REQUEST_TIMEOUT"]
        user_agent = cfg["USER_AGENT"]

        semaphore = asyncio.Semaphore(concurrency)
        valid_channels, invalid_channels = [], []

        # ttl_dns_cache evita requisicoes DNS repetidas para os mesmos servidores
        connector = aiohttp.TCPConnector(
            ssl=False, 
            limit=concurrency, 
            ttl_dns_cache=300,
            force_close=True,
            enable_cleanup_closed=True
        )

        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [test_stream(session, ch, semaphore, user_agent, timeout) for ch in channels]
            results = await asyncio.gather(*tasks, return_exceptions=False)

            for channel, is_valid, latency, status in results:
                info = {**channel, "latency_ms": latency, "http_status": status}
                if is_valid:
                    valid_channels.append(info)
                else:
                    invalid_channels.append(info)

        return valid_channels, invalid_channels

    def save_partitioned_playlists(self, channels: List[Dict[str, Any]]) -> List[str]:
        cfg = self.config_mgr.get_all()
        max_limit = cfg["MAX_CHANNELS_PER_FILE"]

        for f in glob.glob(os.path.join(self.output_dir, "*.m3u")):
            os.remove(f)

        created_files = []
        chunks = [channels[i:i + max_limit] for i in range(0, len(channels), max_limit)]

        for idx, chunk in enumerate(chunks, start=1):
            file_name = f"playlist_parte_{idx:02d}.m3u"
            file_path = os.path.join(self.output_dir, file_name)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for ch in chunk:
                    f.write(f"{ch['metadata']}\n")
                    f.write(f"{ch['url']}\n")
            created_files.append(file_name)

        return created_files

    def generate_audit_log(self, total: int, valid: List[Dict[str, Any]], invalid: List[Dict[str, Any]], output_files: List[str]) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(self.logs_dir, f"auditoria_{timestamp}.json")

        report = {
            "timestamp": datetime.now().isoformat(),
            "configuracoes": self.config_mgr.get_all(),
            "metricas": {
                "total_extraido": total,
                "total_operante": len(valid),
                "total_inoperante": len(invalid),
                "taxa_disponibilidade_pct": round((len(valid) / total * 100), 2) if total > 0 else 0
            },
            "arquivos_gerados": output_files,
            "detalhes_operantes": [{"nome": c["name"], "url": c["url"], "latencia_ms": c["latency_ms"]} for c in valid],
            "detalhes_inoperantes": [{"nome": c["name"], "url": c["url"], "status_code": c["http_status"]} for c in invalid]
        }

        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4, ensure_ascii=False)

        return log_path