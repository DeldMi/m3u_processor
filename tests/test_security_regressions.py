import os
import tempfile
import unittest

from src.config import ConfigManager
from src.manager import PlaylistManager


class SecurityRegressionTests(unittest.TestCase):
    def test_secret_key_is_generated_and_not_public(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = ConfigManager(tmp)
            self.assertTrue(cfg.get_all()["SECRET_KEY"])
            self.assertNotIn("SECRET_KEY", cfg.get_public())

    def test_audit_redacts_url_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = PlaylistManager(tmp)
            try:
                path = manager.generate_audit_log(
                    1,
                    [{"name": "Canal", "url": "http://user:password@example.test/live?token=secret"}],
                    [],
                    [],
                )
                with open(path, "r", encoding="utf-8") as handle:
                    content = handle.read()
                self.assertNotIn("password", content)
                self.assertNotIn("secret", content)
                self.assertIn("***", content)
            finally:
                manager.close()


if __name__ == "__main__":
    unittest.main()
