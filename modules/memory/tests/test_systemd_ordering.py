import unittest
from pathlib import Path


class SystemdOrderingTests(unittest.TestCase):
    def test_memory_daemon_does_not_order_against_swap_target(self):
        unit = Path(__file__).parents[1] / "systemd" / "compresso-memoryd.service"
        content = unit.read_text()
        self.assertIn("After=local-fs.target systemd-modules-load.service", content)
        self.assertNotIn("Before=swap.target", content)
        self.assertNotIn("After=swap.target", content)

    def test_memory_daemon_remains_enabled_for_multi_user_boot(self):
        unit = Path(__file__).parents[1] / "systemd" / "compresso-memoryd.service"
        content = unit.read_text()
        self.assertIn("[Install]", content)
        self.assertIn("WantedBy=multi-user.target", content)


if __name__ == "__main__":
    unittest.main()
