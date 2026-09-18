import re
from typing import List, Dict, Any


class M3UParser:
    """Parser tolerante para M3U/M3U8 com metadados IPTV comuns."""

    _ATTR_RE = re.compile(r'''([A-Za-z0-9_-]+)\\s*=\\s*(?:"([^"]*)"|'([^']*)'|([^\\s,]+))''')

    @classmethod
    def _attributes(cls, metadata: str) -> Dict[str, str]:
        values: Dict[str, str] = {}
        for match in cls._ATTR_RE.finditer(metadata or ""):
            values[match.group(1).lower()] = next((group for group in match.groups()[1:] if group is not None), "").strip()
        return values

    @staticmethod
    def _number(value: str) -> int | None:
        try:
            # Alguns provedores enviam 12.0 como número do canal.
            return int(float(value.strip()))
        except (TypeError, ValueError, AttributeError):
            return None

    @classmethod
    def parse_text(cls, content: str, source_identifier: str = "Desconhecido") -> List[Dict[str, Any]]:
        channels: List[Dict[str, Any]] = []
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        current_metadata: str | None = None

        for line in lines:
            if line.startswith("#EXTM3U"):
                continue
            if line.startswith("#EXTINF:"):
                current_metadata = line
                continue
            if line.startswith("#"):
                # Extensões M3U como #EXTVLCOPT são metadados auxiliares;
                # não devem virar URL nem quebrar a entrada atual.
                continue

            url = line.strip()
            if not url:
                continue

            metadata = current_metadata or ""
            attrs = cls._attributes(metadata)
            name = "Canal Desconhecido"
            if "," in metadata:
                name = metadata.rsplit(",", 1)[1].strip() or name
            tvg_name = attrs.get("tvg-name", "").strip()
            if not name or name == "Canal Desconhecido":
                name = tvg_name or name

            channel_number = cls._number(attrs.get("tvg-chno", ""))
            # Alguns arquivos usam tvg-id/tvg-name, enquanto outros dependem
            # apenas do nome. Mantemos os dois para compatibilidade.
            tvg_id = attrs.get("tvg-id", "").strip()
            group_title = attrs.get("group-title", "").strip()
            logo = attrs.get("tvg-logo", "").strip()

            channels.append({
                "metadata": metadata or f'#EXTINF:-1 tvg-id="{tvg_id or name}",{name}',
                "name": name,
                "tvg_id": tvg_id,
                "tvg_name": tvg_name,
                "channel_number": channel_number,
                "logo": logo,
                "group_title": group_title,
                "language": attrs.get("tvg-language", "").strip(),
                "country": attrs.get("tvg-country", "").strip(),
                "radio": attrs.get("radio", "").strip().lower() in {"1", "true", "yes"},
                "url": url,
                "source": source_identifier,
                "attributes": attrs,
            })
            current_metadata = None

        return channels
