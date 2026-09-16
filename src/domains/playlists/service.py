"""Serviços de publicação e descoberta de playlists geradas."""

import glob
import os
from typing import Any


def get_output_manifests(manager: Any) -> list[dict[str, Any]]:
    """Lê os arquivos publicados e monta os links públicos M3U/XMLTV."""
    cfg = manager.config_mgr.get_all()
    manifests: list[dict[str, Any]] = []
    for m3u_path in sorted(glob.glob(os.path.join(manager.output_dir, "*.m3u"))):
        m3u_name = os.path.basename(m3u_path)
        xml_name = os.path.splitext(m3u_name)[0].replace("playlist_", "epg_") + ".xml"
        xml_path = os.path.join(manager.output_dir, xml_name)
        try:
            with open(m3u_path, "r", encoding="utf-8", errors="ignore") as playlist_file:
                total = sum(1 for line in playlist_file if line.startswith("#EXTINF:"))
        except OSError:
            total = 0
        manifests.append(
            {
                "m3u_name": m3u_name,
                "m3u_url": f"{cfg['PUBLIC_BASE_URL']}/playlist/{m3u_name}",
                "xml_name": xml_name,
                "xml_url": f"{cfg['PUBLIC_BASE_URL']}/epg/{xml_name}",
                "total": total,
                "xml_exists": os.path.exists(xml_path),
            }
        )
    return manifests
