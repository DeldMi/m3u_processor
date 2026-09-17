import tempfile
import unittest
from src.domains.monitoring.service import ResourceMonitor

class ResourceMonitorTests(unittest.TestCase):
    def test_snapshot_has_core_metrics(self):
        with tempfile.TemporaryDirectory() as root:
            data = ResourceMonitor(30).snapshot(root)
            self.assertIn("cpu_percent", data)
            self.assertIn("ram_percent", data)
            self.assertIn("process_rss_bytes", data)
            self.assertIn("disk_free_bytes", data)

    def test_history_is_bounded(self):
        with tempfile.TemporaryDirectory() as root:
            monitor = ResourceMonitor(30)
            for _ in range(50):
                monitor.snapshot(root)
            self.assertLessEqual(len(monitor.history), 30)

if __name__ == "__main__":
    unittest.main()
