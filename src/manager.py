import os
import glob
import json
import asyncio
import logging
import re
import aiohttp
from datetime import datetime
from typing import List, Dict, Any, Tuple
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from src.parser import M3UParser
from src.classifier import StreamClassifier
from src.checker import test_stream, create_ssl_context
from src.epg import EPGManager
from src.config import ConfigManager
from src.db import Database

# Silencia logs ruidosos de DNS no terminal
logging.getLogger("aiohttp.connector").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)


class PlaylistManager:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.input_dir = os.path.join(base_dir, "input")
        self.output_dir = os.path.join(base_dir, "output")
        self.logs_dir = os.path.join(base_dir, "logs")
        self.db = Database(os.path.join(base_dir, "data", "app.db"))
        self.config_mgr = ConfigManager(base_dir)
        self._ensure_directories()

    def _ensure_directories(self):
        for path in [self.input_dir, self.output_dir, self.logs_dir, os.path.join(self.base_dir, "data")]:
            os.makedirs(path, exist_ok=True)

    def close(self):
        try:
            self.db.close()
        except Exception:
            pass

    @staticmethod
    def _redact_url(url: str) -> str:
        """Remove credenciais comuns de URLs antes de gravá-las em auditorias."""
        try:
            parts = urlsplit(url)
            username = "" if not parts.username else "***"
            netloc = parts.hostname or ""
            if parts.port:
                netloc += f":{parts.port}"
            if username:
                netloc = f"{username}@{netloc}"
            query = []
            for key, value in parse_qsl(parts.query, keep_blank_values=True):
                if key.lower() in {"password", "pass", "pwd", "token", "auth", "authorization", "username", "user", "key"}:
                    value = "***"
                query.append((key, value))
            return urlunsplit((parts.scheme, netloc, parts.path, urlencode(query), parts.fragment))
        except Exception:
            return "[URL_REDACTED]"

    def load_input_channels(self) -> List[Dict[str, Any]]:
        return asyncio.run(self.load_all_sources())

    async def validate_all_channels(self, channels: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        if not channels:
            return [], []
        cfg = self.config_mgr.get_all()
        concurrency = max(1, int(cfg["CONCURRENCY_LIMIT"]))
        semaphore = asyncio.Semaphore(concurrency)
        connector = aiohttp.TCPConnector(
            ssl=create_ssl_context(bool(cfg.get("ALLOW_INSECURE_TLS", False))),
            limit=concurrency,
            ttl_dns_cache=300,
        )
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [test_stream(session, ch, semaphore, cfg["USER_AGENT"], cfg["REQUEST_TIMEOUT"]) for ch in channels]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        valid, invalid = [], []
        for channel, result in zip(channels, results):
            if isinstance(result, Exception):
                invalid.append({**channel, "latency_ms": 0, "http_status": 0, "check_error": str(result)})
                continue
            _, is_valid, latency, status_code = result
            target = valid if is_valid else invalid
            target.append({**channel, "latency_ms": latency, "http_status": status_code})
        return valid, invalid

    async def refresh_channel_health(self) -> Dict[str, int]:
        channels = self.db.list_channels()
        if not channels:
            return {"total": 0, "online": 0, "offline": 0}
        valid, invalid = await self.validate_all_channels(channels)
        for channel in valid:
            self.db.update_channel_status(channel["url"], "online", channel.get("latency_ms", 0), channel.get("http_status", 0))
        for channel in invalid:
            self.db.update_channel_status(channel["url"], "offline", channel.get("latency_ms", 0), channel.get("http_status", 0))
        return {"total": len(channels), "online": len(valid), "offline": len(invalid)}

    def save_partitioned_playlists(self, channels: List[Dict[str, Any]]) -> List[str]:
        if not channels:
            return []
        manifests = asyncio.run(self._generate_output_partitions([c for c in channels if c.get("category") == "tv"]))
        return [m["m3u_name"] for m in manifests]

    def generate_audit_log(self, total: int, valid: List[Dict[str, Any]], invalid: List[Dict[str, Any]], created: List[str]) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        log_path = os.path.join(self.logs_dir, f"auditoria_{timestamp}.json")
        report = {
            "timestamp": datetime.now().isoformat(),
            "metricas": {
                "total_extraido": total,
                "total_operante": len(valid),
                "total_inoperante": len(invalid),
                "arquivos_gerados": created,
            },
            "canais_operantes": [
                {"nome": c.get("name", "Canal Desconhecido"), "url": self._redact_url(c.get("url", ""))}
                for c in valid
            ],
            "canais_inoperantes": [
                {"nome": c.get("name", "Canal Desconhecido"), "url": self._redact_url(c.get("url", ""))}
                for c in invalid
            ],
        }
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return log_path

    async def _fetch_remote_m3u(self, session: aiohttp.ClientSession, url: str) -> List[Dict[str, Any]]:
        cfg = self.config_mgr.get_all()
        try:
            headers = {"User-Agent": cfg["USER_AGENT"]}
            timeout = aiohttp.ClientTimeout(total=max(5, int(cfg["REQUEST_TIMEOUT"])))
            async with session.get(url, headers=headers, timeout=timeout) as resp:
                if resp.status == 200:
                    text = await resp.text(errors="ignore")
                    return M3UParser.parse_text(text, source_identifier=url)
        except Exception:
            pass
        return []

    async def load_all_sources(self) -> List[Dict[str, Any]]:
        all_channels = []
        seen_urls = set()

        def add_channels(channel_list):
            for ch in channel_list:
                clean_url = str(ch.get("url", "")).strip()
                if clean_url and clean_url not in seen_urls:
                    seen_urls.add(clean_url)
                    all_channels.append(ch)

        for fpath in glob.glob(os.path.join(self.output_dir, "*.m3u")):
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    add_channels(M3UParser.parse_text(f.read(), source_identifier="output_existente"))
            except (OSError, UnicodeError):
                pass

        for ext in ("*.m3u", "*.m3u8", "*.txt"):
            for fpath in glob.glob(os.path.join(self.input_dir, ext)):
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        add_channels(M3UParser.parse_text(f.read(), source_identifier=os.path.basename(fpath)))
                except (OSError, UnicodeError):
                    pass

        cfg = self.config_mgr.get_all()
        remote_urls = [u.strip() for u in cfg.get("REMOTE_M3U_URLS", "").split(";") if u.strip().lower().startswith(("http://", "https://"))]
        if remote_urls:
            connector = aiohttp.TCPConnector(ssl=create_ssl_context(bool(cfg.get("ALLOW_INSECURE_TLS", False))), ttl_dns_cache=300)
            async with aiohttp.ClientSession(connector=connector) as session:
                results = await asyncio.gather(*(self._fetch_remote_m3u(session, u) for u in remote_urls), return_exceptions=True)
                for res in results:
                    if not isinstance(res, Exception):
                        add_channels(res)

        return all_channels

    async def _generate_output_partitions(self, channels: List[Dict[str, Any]], profile: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        cfg = self.config_mgr.get_all()
        profile = profile or {}
        max_limit = max(1, int(profile.get("limit") or cfg["MAX_CHANNELS_PER_FILE"]))
        base_url = str(cfg["PUBLIC_BASE_URL"]).rstrip("/")
        selected = [channel for channel in channels if self._matches_playlist_profile(channel, profile)]
        sort_field = profile.get("sort", "id")
        reverse = str(profile.get("direction", "asc")).lower() == "desc"
        selected.sort(key=lambda channel: str(channel.get(sort_field, "")).lower(), reverse=reverse)

        if not profile.get("preserve_existing"):
            # Não apaga antes de sabermos que há conteúdo válido para publicar.
            # O chamador deve preferir um diretório temporário/atomic replace para
            # publicação; aqui removemos apenas arquivos gerados pelo aplicativo.
            for f in glob.glob(os.path.join(self.output_dir, "playlist*.m3u")) + glob.glob(os.path.join(self.output_dir, "epg*.xml")):
                try:
                    os.remove(f)
                except OSError:
                    pass

        manifests = []
        playlist_name = str(profile.get("name", "")).strip()
        safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", playlist_name).strip("_-")
        file_prefix = f"_{safe_name}" if safe_name else ""
        chunks = [selected[i:i + max_limit] for i in range(0, len(selected), max_limit)]

        for idx, chunk in enumerate(chunks, start=1):
            m3u_name = f"playlist{file_prefix}_parte_{idx:02d}.m3u"
            xml_name = f"epg{file_prefix}_parte_{idx:02d}.xml"
            m3u_path = os.path.join(self.output_dir, m3u_name)
            xml_path = os.path.join(self.output_dir, xml_name)
            EPGManager.slice_epg_for_chunk("", chunk, xml_path)
            temp_m3u = m3u_path + ".tmp"
            try:
                with open(temp_m3u, "w", encoding="utf-8") as f:
                    f.write(f'#EXTM3U url-tvg="{base_url}/epg/{xml_name}"\n')
                    for ch in chunk:
                        meta = ch.get("metadata") or f'#EXTINF:-1 tvg-id="{ch.get("tvg_id", ch.get("name", ""))}",{ch.get("name", "Canal Desconhecido")}'
                        channel_number = ch.get("channel_number")
                        if channel_number is not None:
                            meta = re.sub(r'\s+tvg-chno="[^"]*"', "", meta, flags=re.IGNORECASE)
                            extinf_prefix, extinf_rest = meta.split(",", 1) if "," in meta else (meta, ch.get("name", "Canal Desconhecido"))
                            meta = f'{extinf_prefix} tvg-chno="{int(channel_number)}",{extinf_rest}'
                        f.write(f'{meta}\n{ch["url"]}\n')
                os.replace(temp_m3u, m3u_path)
            except Exception:
                try:
                    if os.path.exists(temp_m3u):
                        os.remove(temp_m3u)
                except OSError:
                    pass
                raise
            manifests.append({"m3u_name": m3u_name, "m3u_url": f"{base_url}/playlist/{m3u_name}", "xml_name": xml_name, "xml_url": f"{base_url}/epg/{xml_name}", "total": len(chunk)})
        return manifests

    @staticmethod
    def _matches_playlist_profile(channel: Dict[str, Any], profile: Dict[str, Any]) -> bool:
        ids = profile.get("ids")
        if ids:
            try:
                accepted_ids = {int(value) for value in ids}
            except (TypeError, ValueError):
                return False
            if channel.get("id") not in accepted_ids:
                return False
        for field in ("country", "state", "city", "category", "status", "group_title"):
            values = profile.get(field)
            if values and values != "todos":
                accepted = values if isinstance(values, list) else [values]
                if str(channel.get(field, "")) not in [str(value) for value in accepted]:
                    return False
        search = str(profile.get("search", "")).strip().lower()
        if search and search not in " ".join(str(channel.get(field, "")) for field in ("name", "url", "group_title", "tvg_id")).lower():
            return False
        return True

    def generate_custom_playlist(self, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        channels = self.db.list_channels()
        return asyncio.run(self._generate_output_partitions(channels, {**profile, "preserve_existing": True}))

    async def sync_and_audit(self, progress_callback=None, control_callback=None, publication_mode: str = "NONE") -> Dict[str, Any]:
        if control_callback:
            control_callback("inicio")
        cfg = self.config_mgr.get_all()
        user_agent = cfg["USER_AGENT"]
        timeout = cfg["REQUEST_TIMEOUT"]
        concurrency = max(1, int(cfg["CONCURRENCY_LIMIT"]))
        max_limit = max(1, int(cfg["MAX_CHANNELS_PER_FILE"]))
        base_url = cfg["PUBLIC_BASE_URL"]

        if progress_callback:
            progress_callback("Lendo e deduplicando canais locais e remotos...")

        raw_channels = await self.load_all_sources()
        if control_callback:
            control_callback("fontes carregadas")
        total_raw = len(raw_channels)

        for ch in raw_channels:
            ch.setdefault("metadata", f'#EXTINF:-1 tvg-id="{ch.get("tvg_id", ch.get("name", ""))}",{ch.get("name", "Canal Desconhecido")}')
            ch.setdefault("group_title", "")
            ch.setdefault("tvg_id", "")
            ch.setdefault("auto_remove_if_offline", 1)
            meta = StreamClassifier.classify(ch["name"], ch.get("group_title", ""), ch["url"])
            ch.update(meta)
            ch.setdefault("country", "Outros")
            ch.setdefault("state", "Nacional/Geral")
            ch.setdefault("city", "Geral")
            self.db.upsert_channel(ch)

        channels_to_test = self.db.list_channels()
        total_channels = len(channels_to_test)
        if total_channels == 0:
            return {"total": 0, "online": 0, "offline": 0, "partitions": []}

        if progress_callback:
            progress_callback(f"Testando {total_channels} canais unicos (concorrencia: {concurrency})...")

        valid_list, invalid_list = await self.validate_all_channels(channels_to_test)
        if control_callback:
            control_callback("verificação concluída")

        for channel in valid_list:
            self.db.update_channel_status(channel["url"], "online", channel.get("latency_ms", 0), channel.get("http_status", 0))
        for channel in invalid_list:
            self.db.update_channel_status(channel["url"], "offline", channel.get("latency_ms", 0), channel.get("http_status", 0))

        if progress_callback:
            progress_callback("Mantendo canais inoperantes no banco para revalidação...")

        publication_mode = (publication_mode or "NONE").upper()
        active_channels = [c for c in self.db.list_channels() if c["status"] == "online"]
        if publication_mode == "NONE":
            if progress_callback:
                progress_callback("Auditoria concluída sem criar ou atualizar links públicos.")
            log_path = self.generate_audit_log(total_channels, valid_list, invalid_list, [])
            return {"total": total_channels, "online": len(valid_list), "offline": len(invalid_list), "partitions": [], "log_file": os.path.basename(log_path), "publication_mode": publication_mode}

        if progress_callback:
            progress_callback(f"Gerando playlists para {len(active_channels)} canais operantes...")
        manifests = await self._generate_output_partitions(active_channels, {"limit": max_limit, "preserve_existing": False})
        created = [m["m3u_name"] for m in manifests]
        log_path = self.generate_audit_log(total_channels, valid_list, invalid_list, created)
        if control_callback:
            control_callback("concluído")
        return {"total": total_channels, "online": len(valid_list), "offline": len(invalid_list), "partitions": manifests, "log_file": os.path.basename(log_path), "publication_mode": publication_mode, "total_raw": total_raw}
