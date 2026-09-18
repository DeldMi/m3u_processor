import os
import tempfile
import unittest

from src.config import ConfigManager
from src.manager import PlaylistManager


class ConfigManagerTests(unittest.TestCase):
    def test_default_values_are_loaded(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = ConfigManager(tmp)
            values = cfg.get_all()
            self.assertEqual(values["MAX_CHANNELS_PER_FILE"], 400)
            self.assertEqual(values["WEB_PORT"], 5000)
            self.assertEqual(values["SCHEDULE_MODE"], "DISABLED")
            self.assertTrue(values["SECRET_KEY"])

    def test_public_config_never_contains_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = ConfigManager(tmp)
            public = cfg.get_public()
            self.assertNotIn("SECRET_KEY", public)
            self.assertNotIn("API_TOKEN", public)
            self.assertNotIn("ADMIN_INITIAL_PASSWORD", public)

    def test_protected_settings_cannot_be_changed_through_public_config_writer(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = ConfigManager(tmp)
            with self.assertRaises(PermissionError):
                cfg.update_key("SECRET_KEY", "secret-value")
            with self.assertRaises(PermissionError):
                cfg.update_key("API_TOKEN", "token-value")


class PlaylistManagerTests(unittest.TestCase):
    def test_load_input_channels_reads_m3u(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = os.path.join(tmp, "input")
            os.makedirs(input_dir, exist_ok=True)
            m3u_path = os.path.join(input_dir, "sample.m3u")
            with open(m3u_path, "w", encoding="utf-8") as f:
                f.write('#EXTM3U\n')
                f.write('#EXTINF:-1 tvg-id="channel1" group-title="Brasil", Canal Teste 1\n')
                f.write('http://example.com/stream1\n')
                f.write('#EXTINF:-1 tvg-id="channel2" group-title="Brasil", Canal Teste 2\n')
                f.write('http://example.com/stream2\n')

            manager = PlaylistManager(tmp)
            try:
                channels = manager.load_input_channels()
                self.assertEqual(len(channels), 2)
                self.assertEqual(channels[0]["name"], "Canal Teste 1")
                self.assertEqual(channels[1]["url"], "http://example.com/stream2")
            finally:
                manager.close()

    def test_partition_generation_works_for_valid_channels(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = PlaylistManager(tmp)
            try:
                channels = [
                    {"name": "Canal A", "url": "http://example.com/a.m3u8", "metadata": "#EXTINF:-1,Canal A", "category": "tv"},
                    {"name": "Canal B", "url": "http://example.com/b.m3u8", "metadata": "#EXTINF:-1,Canal B", "category": "tv"},
                ]
                generated = manager.save_partitioned_playlists(channels)
                self.assertTrue(len(generated) >= 1)
                self.assertTrue(os.path.exists(os.path.join(tmp, "output", generated[0])))
            finally:
                manager.close()


if __name__ == "__main__":
    unittest.main()
