import os
import glob
import json
import asyncio
import logging
import aiohttp
from datetime import datetime
from typing import List, Dict, Any, Tuple
from src.parser import M3UParser
from src.checker import test_stream, create_unverified_ssl_context
from src.epg import EPGManager
from src.config import ConfigManager

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

    async def _fetch_remote_m3u(self, session: aiohttp.ClientSession, url: str) -> List[Dict[str, Any]]:
        cfg = self.config_mgr.get_all()
        try:
            async with session.get(url, headers={"User-Agent": cfg["USER_AGENT"]}, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 200:
                    text = await resp.text(errors="ignore")
                    return M3UParser.parse_text(text, source_identifier=url)
        except Exception:
            pass
        return []

    async def load_all_channels(self) -> List[Dict[str, Any]]:
        """Carrega dados locais (input/ e output/ existente) e remotos com deduplicacao deterministica."""
        all_channels = []
        seen_urls = set()

        def ingest(channels_list):
            for ch in channels_list:
                clean_url = ch["url"].strip()
                if clean_url and clean_url not in seen_urls:
                    seen_urls.add(clean_url)
                    all_channels.append(ch)

        # 1. Carrega canais ja existentes em output/ para revalidacao (expurgo de canais caidos)
        for fpath in glob.glob(os.path.join(self.output_dir, "*.m3u")):
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                ingest(M3UParser.parse_text(f.read(), source_identifier="output_existente"))

        # 2. Carrega arquivos novos na pasta input/
        for ext in ("*.m3u", "*.m3u8", "*.txt"):
            for fpath in glob.glob(os.path.join(self.input_dir, ext)):
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    ingest(M3UParser.parse_text(f.read(), source_identifier=os.path.basename(fpath)))

        # 3. Carrega listas remotas cadastradas no .env
        cfg = self.config_mgr.get_all()
        remote_urls = [u.strip() for u in cfg["REMOTE_M3U_URLS"].split(";") if u.strip().startswith("http")]
        if remote_urls:
            connector = aiohttp.TCPConnector(ssl=create_unverified_ssl_context(), ttl_dns_cache=300)
            async with aiohttp.ClientSession(connector=connector) as session:
                tasks = [self._fetch_remote_m3u(session, u) for u in remote_urls]
                results = await asyncio.gather(*tasks)
                for res in results:
                    ingest(res)

        return all_channels

    async def validate_channels(self, channels: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        cfg = self.config_mgr.get_all()
        concurrency = cfg["CONCURRENCY_LIMIT"]
        timeout = cfg["REQUEST_TIMEOUT"]
        user_agent = cfg["USER_AGENT"]

        semaphore = asyncio.Semaphore(concurrency)
        valid_channels, invalid_channels = [], []

        connector = aiohttp.TCPConnector(
            ssl=create_unverified_ssl_context(),
            limit=concurrency,
            ttl_dns_cache=300,
            force_close=True
        )

        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [test_stream(session, ch, semaphore, user_agent, timeout) for ch in channels]
            results = await asyncio.gather(*tasks)

            for channel, is_valid, latency, status in results:
                info = {**channel, "latency_ms": latency, "http_status": status}
                if is_valid:
                    valid_channels.append(info)
                else:
                    invalid_channels.append(info)

        return valid_channels, invalid_channels

    async def process_and_partition(self, valid_channels: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Divide em lotes de no maximo 400 canais e gera os arquivos .m3u e .xml equivalentes."""
        cfg = self.config_mgr.get_all()
        max_limit = cfg["MAX_CHANNELS_PER_FILE"]
        base_url = cfg["BASE_URL"]

        # Limpeza total dos arquivos anteriores para remocao garantida dos inativos
        for f in glob.glob(os.path.join(self.output_dir, "*.*")):
            try:
                os.remove(f)
            except OSError:
                pass

        # Ingestao dos EPGs mestres cadastrados (iptv-epg.org)
        epg_urls = [u.strip() for u in cfg["EPG_URLS"].split(";") if u.strip().startswith("http")]
        master_epg_data = ""
        for e_url in epg_urls:
            raw_xml = await EPGManager.fetch_and_extract_epg(e_url, cfg["USER_AGENT"])
            if raw_xml:
                master_epg_data = raw_xml  # Consolida no EPG mestre
                break

        created_manifests = []
        chunks = [valid_channels[i:i + max_limit] for i in range(0, len(valid_channels), max_limit)]

        for idx, chunk in enumerate(chunks, start=1):
            m3u_name = f"playlist_parte_{idx:02d}.m3u"
            xml_name = f"epg_parte_{idx:02d}.xml"

            m3u_path = os.path.join(self.output_dir, m3u_name)
            xml_path = os.path.join(self.output_dir, xml_name)

            epg_public_url = f"{base_url}/epg/{xml_name}"
            m3u_public_url = f"{base_url}/playlist/{m3u_name}"

            # 1. Gera o XML de guia correspondente a este bloco de canais
            EPGManager.slice_epg_for_chunk(master_epg_data, chunk, xml_path)

            # 2. Gera o arquivo M3U apontando para o seu EPG respectivo
            with open(m3u_path, "w", encoding="utf-8") as f:
                f.write(f'#EXTM3U url-tvg="{epg_public_url}"\n')
                for ch in chunk:
                    f.write(f"{ch['metadata']}\n")
                    f.write(f"{ch['url']}\n")

            created_manifests.append({
                "m3u_name": m3u_name,
                "m3u_url": m3u_public_url,
                "xml_name": xml_name,
                "xml_url": epg_public_url,
                "total_canais": len(chunk)
            })

        return created_manifests

    def generate_audit_log(self, total: int, valid: List[Dict[str, Any]], invalid: List[Dict[str, Any]], manifests: List[Dict[str, str]]) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(self.logs_dir, f"auditoria_{timestamp}.json")

        report = {
            "timestamp": datetime.now().isoformat(),
            "configuracoes": self.config_mgr.get_all(),
            "metricas": {
                "total_extraido": total,
                "total_operante": len(valid),
                "total_removido_ou_inoperante": len(invalid),
                "taxa_disponibilidade_pct": round((len(valid) / total * 100), 2) if total > 0 else 0
            },
            "arquivos_gerados": manifests,
            "detalhes_operantes": [{"nome": c["name"], "url": c["url"], "latencia_ms": c["latency_ms"]} for c in valid],
            "detalhes_removidos": [{"nome": c["name"], "url": c["url"], "status_http": c["http_status"]} for c in invalid]
        }

        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4, ensure_ascii=False)

        return log_path