import unittest

from src.parser import M3UParser


class M3UParserTests(unittest.TestCase):
    def test_parses_common_iptv_attributes(self):
        text = '''#EXTM3U
#EXTINF:-1 tvg-id="br1" tvg-name="Canal Brasil" tvg-logo="https://example/logo.png" tvg-chno="12" group-title="Brasil" tvg-language="pt",Canal Brasil
https://example.test/live/1
'''
        channels = M3UParser.parse_text(text, "teste")
        self.assertEqual(len(channels), 1)
        channel = channels[0]
        self.assertEqual(channel["name"], "Canal Brasil")
        self.assertEqual(channel["tvg_id"], "br1")
        self.assertEqual(channel["channel_number"], 12)
        self.assertEqual(channel["group_title"], "Brasil")
        self.assertEqual(channel["language"], "pt")
        self.assertEqual(channel["source"], "teste")

    def test_accepts_single_quoted_attributes_and_ignores_auxiliary_tags(self):
        text = """#EXTM3U
#EXTINF:-1 tvg-id='br2' group-title='Noticias',Notícias
#EXTVLCOPT:http-referrer=https://example.test
https://example.test/live/2
"""
        channels = M3UParser.parse_text(text)
        self.assertEqual(len(channels), 1)
        self.assertEqual(channels[0]["tvg_id"], "br2")
        self.assertEqual(channels[0]["group_title"], "Noticias")
        self.assertEqual(channels[0]["url"], "https://example.test/live/2")


if __name__ == "__main__":
    unittest.main()
