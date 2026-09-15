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
                name = "Canal Sem Nome"
                if current_metadata:
                    match_name = re.search(r",([^,]+)$", current_metadata)
                    if match_name:
                        name = match_name.group(1).strip()
                else:
                    current_metadata = f'#EXTINF:-1 tvg-id="" tvg-name="{name}",{name}'

                channels.append({
                    "metadata": current_metadata,
                    "name": name,
                    "url": url,
                    "source": source_identifier
                })
                current_metadata = None

        return channels