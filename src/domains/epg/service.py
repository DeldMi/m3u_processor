"""Download, validation and composition of XMLTV sources."""
from __future__ import annotations

import gzip
import io
import os
import re
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

MAX_COMPRESSED_BYTES = 50 * 1024 * 1024
MAX_XML_BYTES = 250 * 1024 * 1024


def normalize_xmltv(content: bytes, compressed: bool = False) -> tuple[bytes, int]:
    if len(content) > MAX_COMPRESSED_BYTES:
        raise ValueError("O arquivo EPG excede o limite de 50 MB.")
    if compressed or content[:2] == b"\x1f\x8b":
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(content)) as stream:
                content = stream.read(MAX_XML_BYTES + 1)
        except (OSError, EOFError) as exc:
            raise ValueError("O arquivo gzip/XMLTV está inválido.") from exc
    if len(content) > MAX_XML_BYTES:
        raise ValueError("O XMLTV descompactado excede o limite de 250 MB.")
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise ValueError("O conteúdo enviado não é um XML válido.") from exc
    if root.tag.rsplit("}", 1)[-1].lower() != "tv":
        raise ValueError("O XML informado não possui uma raiz XMLTV <tv>.")
    return content, sum(1 for child in root if child.tag.rsplit("}", 1)[-1] == "channel")


def download_xmltv(url: str, user_agent: str) -> tuple[bytes, int]:
    url = str(url).strip()
    if not re.match(r"^https?://", url, re.IGNORECASE):
        raise ValueError("Informe uma URL HTTP ou HTTPS válida.")
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            content = response.read(MAX_COMPRESSED_BYTES + 1)
    except Exception as exc:
        raise ValueError(f"Não foi possível baixar o XMLTV: {exc}") from exc
    return normalize_xmltv(content, compressed=url.lower().split("?", 1)[0].endswith(".gz"))


def save_xmltv(base_dir: str, content: bytes) -> str:
    directory = Path(base_dir) / "data" / "epg_sources"
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.xml"
    destination = directory / filename
    temporary = destination.with_suffix(".tmp")
    temporary.write_bytes(content)
    os.replace(temporary, destination)
    return str(destination)


def compose_xmltv(channels: list[dict], sources: dict[int, str], programmes: list[dict] | None = None) -> str:
    targets_by_source: dict[int, set[str]] = {}
    source_ids = set()
    channel_ids: dict[int, str] = {}
    for index, channel in enumerate(channels):
        channel_key = int(channel.get("id") or -(index + 1))
        output_id = str((channel.get("epg_channel_id") if channel.get("epg_source_id") else "") or channel.get("tvg_id") or channel.get("name") or "").strip()
        if output_id:
            channel_ids[channel_key] = output_id
        source_id = channel.get("epg_source_id")
        if source_id:
            source_id = int(source_id)
            source_ids.add(source_id)
            target_ids = targets_by_source.setdefault(source_id, set())
        else:
            continue
        for value in (channel.get("epg_channel_id"), channel.get("tvg_id"), channel.get("name")):
            normalized = str(value or "").strip().lower()
            if normalized:
                target_ids.add(normalized)

    output = ET.Element("tv")
    added_channels = set()
    for source_id in sorted(source_ids):
        path = sources.get(source_id)
        target_ids = targets_by_source[source_id]
        if not path or not os.path.isfile(path):
            continue
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError):
            continue
        for node in root:
            tag = node.tag.rsplit("}", 1)[-1]
            if tag == "channel":
                channel_id = str(node.get("id", "")).strip().lower()
                display_names = {str(item.text or "").strip().lower() for item in node if item.tag.rsplit("}", 1)[-1] == "display-name"}
                if channel_id in target_ids or display_names.intersection(target_ids):
                    if channel_id not in added_channels:
                        output.append(node)
                        added_channels.add(channel_id)
            elif tag == "programme" and str(node.get("channel", "")).strip().lower() in target_ids:
                output.append(node)
    for index, channel in enumerate(channels):
        channel_id = channel_ids.get(int(channel.get("id") or -(index + 1)))
        if channel_id and channel_id.lower() not in added_channels:
            node = ET.SubElement(output, "channel", {"id": channel_id})
            ET.SubElement(node, "display-name").text = str(channel.get("name") or channel_id)
            added_channels.add(channel_id.lower())
    now = datetime.now().astimezone()
    horizon = now + timedelta(days=8)
    for programme in programmes or []:
        xmltv_id = channel_ids.get(int(programme.get("channel_id", 0)))
        if not xmltv_id:
            continue
        try:
            start = datetime.fromisoformat(str(programme["start_at"]))
            end = datetime.fromisoformat(str(programme["end_at"]))
            recurrence = str(programme.get("recurrence", "once"))
            weekdays = {int(day) for day in programme.get("weekdays", [])}
        except (KeyError, TypeError, ValueError):
            continue
        occurrences = []
        if recurrence == "once":
            if end.astimezone() >= now and start.astimezone() < horizon:
                occurrences.append((start, end))
        else:
            day = max(now.date() - timedelta(days=1), start.date())
            while start.date() <= day <= horizon.date():
                if recurrence == "daily" or day.weekday() in weekdays:
                    occurrence_start = start + timedelta(days=(day - start.date()).days)
                    occurrence_end = end + timedelta(days=(day - start.date()).days)
                    if occurrence_end.astimezone() >= now and occurrence_start.astimezone() < horizon:
                        occurrences.append((occurrence_start, occurrence_end))
                day += timedelta(days=1)
        for start_time, end_time in occurrences:
            start_utc = start_time.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S +0000")
            end_utc = end_time.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S +0000")
            node = ET.SubElement(output, "programme", {"start": start_utc, "stop": end_utc, "channel": xmltv_id})
            ET.SubElement(node, "title", {"lang": "pt"}).text = str(programme.get("title", ""))
            for field, tag in (("description", "desc"), ("category", "category")):
                value = str(programme.get(field, "") or "").strip()
                if value:
                    ET.SubElement(node, tag).text = value
            season = str(programme.get("season", "") or "").strip()
            episode = str(programme.get("episode", "") or "").strip()
            if season or episode:
                ET.SubElement(node, "episode-num", {"system": "onscreen"}).text = f"S{season} E{episode}".strip()
            rating = str(programme.get("rating", "") or "").strip()
            if rating:
                ET.SubElement(ET.SubElement(node, "rating"), "value").text = rating
            image = str(programme.get("image", "") or "").strip()
            if image:
                ET.SubElement(node, "icon", {"src": image})
    return ET.tostring(output, encoding="unicode")
