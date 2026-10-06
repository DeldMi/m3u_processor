import gzip
import os
import tempfile
import unittest
from flask import Flask

from src.db import Database
from src.domains.epg.routes import _request_data
from src.domains.epg.service import compose_xmltv, normalize_xmltv


class EpgManagementTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(os.path.join(self.tmp.name, "data", "app.db"))

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_xmltv_validation_accepts_xml_and_gzip(self):
        xml = b'<tv><channel id="news"><display-name>News</display-name></channel></tv>'
        self.assertEqual(normalize_xmltv(xml)[1], 1)
        self.assertEqual(normalize_xmltv(gzip.compress(xml), compressed=True)[1], 1)

    def test_xmltv_validation_rejects_non_tv_root(self):
        with self.assertRaises(ValueError):
            normalize_xmltv(b"<root />")

    def test_epg_request_data_reads_form_without_file_upload(self):
        app = Flask(__name__)
        with app.test_request_context("/api/v1/epg/sources", method="POST", data={"name": "Guia URL", "url": "https://example.test/guide.xml"}, content_type="multipart/form-data"):
            self.assertEqual(_request_data()["name"], "Guia URL")
            self.assertEqual(_request_data()["url"], "https://example.test/guide.xml")

    def test_channel_epg_assignment_persists_and_clears_when_source_deleted(self):
        source_id = self.db.create_epg_source("Guia nacional", "https://example.test/guide.xml", "guide.xml")
        channel_id = self.db.create_channel({"name": "News", "url": "https://example.test/live.m3u8"})
        self.assertTrue(self.db.update_channel(channel_id, {"epg_source_id": source_id, "epg_channel_id": "news"}))
        self.assertEqual(self.db.list_epg_sources()[0]["assigned_channels"], 1)
        self.assertTrue(self.db.delete_epg_source(source_id))
        channel = next(item for item in self.db.list_channels() if item["id"] == channel_id)
        self.assertIsNone(channel["epg_source_id"])
        self.assertEqual(channel["epg_channel_id"], "")

    def test_xmltv_composition_includes_only_assigned_channel_programmes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "guide.xml")
            with open(path, "w", encoding="utf-8") as guide:
                guide.write('<tv><channel id="news"><display-name>News</display-name></channel><channel id="sports"/><programme channel="news"/><programme channel="sports"/></tv>')
            result = compose_xmltv([{"id": 1, "epg_source_id": 1, "epg_channel_id": "news", "name": "News"}], {1: path})
            self.assertIn('id="news"', result)
            self.assertIn('channel="news"', result)
            self.assertNotIn('id="sports"', result)
            self.assertNotIn('channel="sports"', result)

    def test_programme_crud_and_weekday_recurrence(self):
        channel_id = self.db.create_channel({"name": "News", "url": "https://example.test/news.m3u8", "tvg_id": "news"})
        values = {"title": "Jornal", "description": "Resumo diário", "category": "Notícias", "start_at": "2026-10-06T20:00", "end_at": "2026-10-06T21:00", "recurrence": "weekly", "weekdays": [0, 2, 4], "season": "1", "episode": "2", "rating": "10", "image": "https://example.test/news.png"}
        programme_id = self.db.create_epg_programme(channel_id, values)
        self.assertIsNotNone(programme_id)
        programme = self.db.list_epg_programmes(channel_id)[0]
        self.assertEqual(programme["weekdays"], [0, 2, 4])
        self.assertEqual(programme["title"], "Jornal")
        values["title"] = "Jornal atualizado"
        self.assertTrue(self.db.update_epg_programme(programme_id, values))
        self.assertEqual(self.db.list_epg_programmes(channel_id)[0]["title"], "Jornal atualizado")
        self.assertTrue(self.db.delete_epg_programme(programme_id))
        self.assertEqual(self.db.list_epg_programmes(channel_id), [])

    def test_invalid_programme_time_and_weekly_recurrence_are_rejected(self):
        channel_id = self.db.create_channel({"name": "News", "url": "https://example.test/other.m3u8"})
        invalid = {"title": "Invalid", "start_at": "2026-10-06T21:00", "end_at": "2026-10-06T20:00", "recurrence": "once", "weekdays": []}
        self.assertIsNone(self.db.create_epg_programme(channel_id, invalid))
        invalid["end_at"] = "2026-10-06T22:00"
        invalid["recurrence"] = "weekly"
        self.assertIsNone(self.db.create_epg_programme(channel_id, invalid))

    def test_manual_programmes_are_written_to_xmltv(self):
        channel = {"id": 1, "name": "News", "tvg_id": "news"}
        programme = {"channel_id": 1, "title": "Jornal", "description": "Resumo", "category": "Notícias", "start_at": "2026-10-06T20:00", "end_at": "2026-10-06T21:00", "recurrence": "once", "weekdays": [], "season": "", "episode": "", "rating": "", "image": ""}
        result = compose_xmltv([channel], {}, [programme])
        self.assertIn('<programme ', result)
        self.assertIn('channel="news"', result)
        self.assertIn("Jornal", result)


if __name__ == "__main__":
    unittest.main()