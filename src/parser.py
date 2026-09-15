import re
from typing import List, Dict, Any

class M3UParser:
    @staticmethod
    def parse_text(content: str, source_identifier: str = "Desconhecido") -> List[Dict[str, Any]]:
        channels = []
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        current_metadata = None

        for line in lines:
            if line.startswith("#EXTM3U"):
                continue
            elif line.startswith("#EXTINF:"):
                current_metadata = line
            elif not line.startswith("#"):
                url = line
                name = "Canal Desconhecido"
                tvg_id = ""
                logo = ""

                if current_metadata:
                    # Extrai atributos tvg-id e o nome apos a virgula
                    id_match = re.search(r'tvg-id="([^"]*)"', current_metadata, re.IGNORECASE)
                    if id_match:
                        tvg_id = id_match.group(1).strip()
                    logo_match = re.search(r'tvg-logo="([^"]*)"', current_metadata, re.IGNORECASE)
                    if logo_match:
                        logo = logo_match.group(1).strip()
                    name_match = re.search(r",([^,]+)$", current_metadata)
                    if name_match:
                        name = name_match.group(1).strip()
                else:
                    current_metadata = f'#EXTINF:-1 tvg-id="{name}",{name}'

                channels.append({
                    "metadata": current_metadata,
                    "name": name,
                    "tvg_id": tvg_id,
                    "logo": logo,
                    "url": url,
                    "source": source_identifier
                })
                current_metadata = None

        return channels