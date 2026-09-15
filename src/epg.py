import os
import gzip
import io
import aiohttp
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Set

class EPGManager:
    @staticmethod
    async def fetch_and_extract_epg(url: str, user_agent: str) -> str:
        """Realiza o download de arquivos .xml ou .xml.gz e devolve o XML em texto."""
        headers = {"User-Agent": user_agent}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status == 200:
                        raw_data = await resp.read()
                        if url.endswith(".gz") or raw_data[:2] == b'\x1f\x8b':
                            with gzip.GzipFile(fileobj=io.BytesIO(raw_data)) as gz:
                                return gz.read().decode("utf-8", errors="ignore")
                        return raw_data.decode("utf-8", errors="ignore")
        except Exception:
            pass
        return ""

    @staticmethod
    def slice_epg_for_chunk(master_xml_content: str, chunk_channels: List[Dict[str, Any]], output_xml_path: str):
        """Gera um arquivo XMLTV contendo apenas os canais e programas pertencentes a este lote de 400."""
        if not master_xml_content.strip():
            # Cria um XMLTV basico caso nao haja guia mestre disponivel
            root = ET.Element("tv")
            for ch in chunk_channels:
                tvg_id = ch.get("tvg_id") or ch["name"]
                c_elem = ET.SubElement(root, "channel", id=tvg_id)
                dn = ET.SubElement(c_elem, "display-name")
                dn.text = ch["name"]
            tree = ET.ElementTree(root)
            tree.write(output_xml_path, encoding="utf-8", xml_declaration=True)
            return

        try:
            source_tree = ET.fromstring(master_xml_content)
            target_root = ET.Element("tv")

            # Mapeamento de IDs validos presentes nesta particao de 400 canais
            target_ids: Set[str] = set()
            for ch in chunk_channels:
                if ch.get("tvg_id"):
                    target_ids.add(ch["tvg_id"].lower())
                target_ids.add(ch["name"].strip().lower())

            # Copia nos de canais (<channel>) correspondentes
            for channel_node in source_tree.findall("channel"):
                cid = channel_node.get("id", "").strip().lower()
                display_names = [d.text.strip().lower() for d in channel_node.findall("display-name") if d.text]
                
                if cid in target_ids or any(d in target_ids for d in display_names):
                    target_root.append(channel_node)

            # Copia nos de programas (<programme>) correspondentes
            for prog_node in source_tree.findall("programme"):
                pid = prog_node.get("channel", "").strip().lower()
                if pid in target_ids:
                    target_root.append(prog_node)

            ET.ElementTree(target_root).write(output_xml_path, encoding="utf-8", xml_declaration=True)
        except Exception:
            # Fallback seguro
            root = ET.Element("tv")
            ET.ElementTree(root).write(output_xml_path, encoding="utf-8", xml_declaration=True)