import os
import glob
import json
import asyncio
import logging
import aiohttp
from datetime import datetime
from typing import List, Dict, Any, Tuple
from src.parser import M3UParser
from src.classifier import StreamClassifier
from src.checker import test_stream, create_unverified_ssl_context
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

    def load_input_channels(self) -> List[Dict[str, Any]]:
        return asyncio.run(self.load_all_sources())

    async def validate_all_channels(self, channels: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        if not channels:
            return [], []
        cfg = self.config_mgr.get_all()
        semaphore = asyncio.Semaphore(max(1, cfg["CONCURRENCY_LIMIT"]))
        connector = aiohttp.TCPConnector(ssl=create_unverified_ssl_context(), limit=max(1, cfg["CONCURRENCY_LIMIT"]), ttl_dns_cache=300)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [test_stream(session, ch, semaphore, cfg["USER_AGENT"], cfg["REQUEST_TIMEOUT"]) for ch in channels]
            results = await asyncio.gather(*tasks)

        valid, invalid = [], []
        for channel, is_valid, latency, status_code in results:
            if is_valid:
                valid.append({**channel, "latency_ms": latency, "http_status": status_code})
            else:
                invalid.append({**channel, "latency_ms": latency, "http_status": status_code})
        return valid, invalid

    def save_partitioned_playlists(self, channels: List[Dict[str, Any]]) -> List[str]:
        if not channels:
            return []
        manifests = asyncio.run(self._generate_output_partitions([c for c in channels if c.get("category") == "tv"]))
        return [m["m3u_name"] for m in manifests]

    def generate_audit_log(self, total: int, valid: List[Dict[str, Any]], invalid: List[Dict[str, Any]], created: List[str]) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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
                {"nome": c.get("name", "Canal Desconhecido"), "url": c.get("url", "")}
                for c in valid
            ],
            "canais_inoperantes": [
                {"nome": c.get("name", "Canal Desconhecido"), "url": c.get("url", "")}
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
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=25)) as resp:
                if resp.status == 200:
                    text = await resp.text(errors="ignore")
                    return M3UParser.parse_text(text, source_identifier=url)
        except Exception:
            pass
        return []

    async def load_all_sources(self) -> List[Dict[str, Any]]:
        """
        Coleta e deduplica canais de todas as origens:
        1. Pasta output/ (canais ja processados anteriormente, para reauditoria)
        2. Pasta input/ (novos arquivos .m3u, .m3u8, .txt)
        3. URLs remotas cadastradas no .env (REMOTE_M3U_URLS)
        """
        all_channels = []
        seen_urls = set()

        def add_channels(channel_list):
            for ch in channel_list:
                clean_url = ch["url"].strip()
                if clean_url and clean_url not in seen_urls:
                    seen_urls.add(clean_url)
                    all_channels.append(ch)

        # 1. Arquivos ja existentes em output/ para revalidacao
        for fpath in glob.glob(os.path.join(self.output_dir, "*.m3u")):
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    add_channels(M3UParser.parse_text(f.read(), source_identifier="output_existente"))
            except Exception:
                pass

        # 2. Arquivos novos em input/
        for ext in ("*.m3u", "*.m3u8", "*.txt"):
            for fpath in glob.glob(os.path.join(self.input_dir, ext)):
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        add_channels(M3UParser.parse_text(f.read(), source_identifier=os.path.basename(fpath)))
                except Exception:
                    pass

        # 3. Listas remotas via HTTP/HTTPS
        cfg = self.config_mgr.get_all()
        remote_urls = [u.strip() for u in cfg.get("REMOTE_M3U_URLS", "").split(";") if u.strip().startswith("http")]
        if remote_urls:
            connector = aiohttp.TCPConnector(ssl=create_unverified_ssl_context(), ttl_dns_cache=300)
            async with aiohttp.ClientSession(connector=connector) as session:
                tasks = [self._fetch_remote_m3u(session, u) for u in remote_urls]
                results = await asyncio.gather(*tasks)
                for res in results:
                    add_channels(res)

        return all_channels

    async def _generate_output_partitions(self, channels: List[Dict[str, Any]], profile: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        cfg = self.config_mgr.get_all()
        profile = profile or {}
        max_limit = max(1, int(profile.get("limit") or cfg["MAX_CHANNELS_PER_FILE"]))
        base_url = cfg["BASE_URL"]
        selected = [channel for channel in channels if self._matches_playlist_profile(channel, profile)]
        sort_field = profile.get("sort", "id")
        reverse = profile.get("direction", "asc").lower() == "desc"
        selected.sort(key=lambda channel: str(channel.get(sort_field, "")).lower(), reverse=reverse)

        for f in glob.glob(os.path.join(self.output_dir, "*.*")):
            try:
                os.remove(f)
            except OSError:
                pass

        manifests = []
        chunks = [selected[i:i + max_limit] for i in range(0, len(selected), max_limit)]

        for idx, chunk in enumerate(chunks, start=1):
            m3u_name = f"playlist_parte_{idx:02d}.m3u"
            xml_name = f"epg_parte_{idx:02d}.xml"
            m3u_path = os.path.join(self.output_dir, m3u_name)
            xml_path = os.path.join(self.output_dir, xml_name)

            EPGManager.slice_epg_for_chunk("", chunk, xml_path)

            with open(m3u_path, "w", encoding="utf-8") as f:
                f.write(f'#EXTM3U url-tvg="{base_url}/epg/{xml_name}"\n')
                for ch in chunk:
                    meta = ch.get("metadata") or f'#EXTINF:-1 tvg-id="{ch.get("tvg_id", ch.get("name", ""))}",{ch.get("name", "Canal Desconhecido")}'
                    f.write(f'{meta}\n{ch["url"]}\n')

            manifests.append({
                "m3u_name": m3u_name,
                "m3u_url": f"{base_url}/playlist/{m3u_name}",
                "xml_name": xml_name,
                "xml_url": f"{base_url}/epg/{xml_name}",
                "total": len(chunk)
            })

        return manifests

    @staticmethod
    def _matches_playlist_profile(channel: Dict[str, Any], profile: Dict[str, Any]) -> bool:
        ids = profile.get("ids")
        if ids and channel.get("id") not in [int(value) for value in ids]:
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
        return asyncio.run(self._generate_output_partitions(channels, profile))

    async def sync_and_audit(self, progress_callback=None, control_callback=None) -> Dict[str, Any]:
        if control_callback:
            control_callback("inicio")
        cfg = self.config_mgr.get_all()
        user_agent = cfg["USER_AGENT"]
        timeout = cfg["REQUEST_TIMEOUT"]
        concurrency = cfg["CONCURRENCY_LIMIT"]
        max_limit = cfg["MAX_CHANNELS_PER_FILE"]
        base_url = cfg["BASE_URL"]

        if progress_callback:
            progress_callback("Lendo e deduplicando canais locais e remotos...")

        # 1. Ingestao e classificacao taxonômica
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

        # 2. Resgate de todos os canais para teste assincrono
        channels_to_test = self.db.list_channels()
        total_channels = len(channels_to_test)

        if total_channels == 0:
            return {"total": 0, "online": 0, "offline": 0, "partitions": []}

        if progress_callback:
            progress_callback(f"Testando {total_channels} canais unicos (concorrencia: {concurrency})...")

        semaphore = asyncio.Semaphore(concurrency)
        connector = aiohttp.TCPConnector(
            ssl=create_unverified_ssl_context(),
            limit=concurrency,
            ttl_dns_cache=300,
            force_close=True
        )

        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [test_stream(session, ch, semaphore, user_agent, timeout) for ch in channels_to_test]
            results = await asyncio.gather(*tasks)

        if control_callback:
            control_callback("verificação concluída")

        valid_list = []
        invalid_list = []

        for channel, is_valid, latency, status_code in results:
            status_str = "online" if is_valid else "offline"
            self.db.update_channel_status(channel["url"], status_str, latency, status_code)
            ch_info = {**channel, "latency_ms": latency, "http_status": status_code}
            if is_valid:
                valid_list.append(ch_info)
            else:
                invalid_list.append(ch_info)

        # 3. Expurgo dos canais fora do ar que possuem auto_remove_if_offline ativo
        if progress_callback:
            progress_callback("Removendo canais inoperantes do banco...")
        self.db.delete_purged_channels()

        # 4. Particionamento em lotes de no maximo 400 canais
        # IMPORTANTE: Inclui TODOS os canais operantes (sem descartar por categoria)
        active_channels = [c for c in self.db.list_channels() if c["status"] == "online"]

        if control_callback:
            control_callback("preparando listas")

        if progress_callback:
            progress_callback(f"Particionando {len(active_channels)} canais ativos (limite: {max_limit}/lista)...")

        # Limpa arquivos antigos da pasta output/
        for f in glob.glob(os.path.join(self.output_dir, "*.*")):
            try:
                os.remove(f)
            except OSError:
                pass

        # Ingestao do EPG mestre cadastrado
        epg_urls = [u.strip() for u in cfg.get("EPG_URLS", "").split(";") if u.strip().startswith("http")]
        master_epg_data = ""
        for e_url in epg_urls:
            raw_xml = await EPGManager.fetch_and_extract_epg(e_url, user_agent)
            if raw_xml:
                master_epg_data = raw_xml
                break

        created_manifests = []
        chunks = [active_channels[i:i + max_limit] for i in range(0, len(active_channels), max_limit)]

        for idx, chunk in enumerate(chunks, start=1):
            if control_callback:
                control_callback(f"gerando lista {idx}")
            m3u_name = f"playlist_parte_{idx:02d}.m3u"
            xml_name = f"epg_parte_{idx:02d}.xml"

            m3u_path = os.path.join(self.output_dir, m3u_name)
            xml_path = os.path.join(self.output_dir, xml_name)

            epg_public_url = f"{base_url}/epg/{xml_name}"
            m3u_public_url = f"{base_url}/playlist/{m3u_name}"

            # Gera XML do EPG para o lote
            EPGManager.slice_epg_for_chunk(master_epg_data, chunk, xml_path)

            # Gera M3U correspondente
            with open(m3u_path, "w", encoding="utf-8") as f:
                f.write(f'#EXTM3U url-tvg="{epg_public_url}"\n')
                for ch in chunk:
                    f.write(f'{ch["metadata"]}\n{ch["url"]}\n')

            created_manifests.append({
                "m3u_name": m3u_name,
                "m3u_url": m3u_public_url,
                "xml_name": xml_name,
                "xml_url": epg_public_url,
                "total": len(chunk)
            })

        # 5. Gravacao obrigatoria do relatorio de auditoria JSON em logs/
        log_path = self.generate_audit_log(total_channels, valid_list, invalid_list, created_manifests)

        return {
            "total": total_channels,
            "online": len(valid_list),
            "offline": len(invalid_list),
            "partitions": created_manifests,
            "log_file": os.path.basename(log_path)
        }

    def generate_audit_log(self, total: int, valid: List[Dict[str, Any]], invalid: List[Dict[str, Any]], manifests: List[Dict[str, Any]]) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(self.logs_dir, f"auditoria_{timestamp}.json")

        report = {
            "timestamp": datetime.now().isoformat(),
            "configuracoes": self.config_mgr.get_all(),
            "metricas": {
                "total_extraido": total,
                "total_operante": len(valid),
                "total_inoperante_removido": len(invalid),
                "taxa_disponibilidade_pct": round((len(valid) / total * 100), 2) if total > 0 else 0
            },
            "arquivos_gerados": manifests,
            "canais_operantes": [{"nome": c["name"], "url": c["url"], "latencia_ms": c.get("latency_ms", 0)} for c in valid],
            "canais_removidos": [{"nome": c["name"], "url": c["url"], "http_status": c.get("http_status", 0)} for c in invalid]
        }

        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4, ensure_ascii=False)

        return log_path