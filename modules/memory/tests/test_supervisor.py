import os
import subprocess
import sys
import unittest
from pathlib import Path

from compresso.supervisor import inspect_health


def snapshot(active, zram_devices=("zram0",), zswap_enabled="N", comp_algorithm="[lz4] lzo-rle lzo"):
    return {
        "memory_kb": {"MemTotal": 4096, "MemAvailable": 2048},
        "active_swaps": [{"filename": item} for item in active],
        "zram": {name: {"disksize_bytes": 1024, "comp_algorithm": comp_algorithm} for name in zram_devices},
        "zswap": {"enabled": zswap_enabled},
    }


class SupervisorTests(unittest.TestCase):
    def test_installed_style_supervisor_script_has_standalone_help(self):
        script = Path(__file__).resolve().parents[1] / "src" / "compresso" / "supervisor.py"
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        completed = subprocess.run(
            [sys.executable, str(script), "--help"],
            capture_output=True, text=True, env=env, timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--config", completed.stdout)

    def test_zram_fast_is_healthy_when_configured_device_is_active_and_zswap_off(self):
        report = inspect_health({"PROFILE": "zram-fast", "DEVICE": "/dev/zram0"},
                                 snapshot(["/dev/zram0"]))
        self.assertEqual(report["status"], "healthy")
        self.assertEqual(report["issues"], [])


    def test_unexpected_active_zram_algorithm_is_reported_as_warning(self):
        cfg = {
            "PROFILE": "zram-fast",
            "DEVICE": "/dev/zram0",
            "ALGORITHM": "lz4",
            "FALLBACK_ALGORITHMS": "lzo-rle,lzo",
        }
        report = inspect_health(
            cfg,
            snapshot(["/dev/zram0"], comp_algorithm="[zstd] lz4 lzo-rle"),
        )
        self.assertEqual(report["status"], "warning")
        self.assertIn("zram_algorithm_mismatch", [item["code"] for item in report["issues"]])

    def test_configured_fallback_algorithm_is_accepted(self):
        cfg = {
            "PROFILE": "zram-fast",
            "DEVICE": "/dev/zram0",
            "ALGORITHM": "zstd",
            "FALLBACK_ALGORITHMS": "lzo-rle,lzo",
        }
        report = inspect_health(
            cfg,
            snapshot(["/dev/zram0"], comp_algorithm="[lzo-rle] lzo lz4"),
        )
        self.assertEqual(report["status"], "healthy")
        self.assertNotIn("zram_algorithm_mismatch", [item["code"] for item in report["issues"]])

    def test_missing_configured_zram_swap_is_critical(self):
        report = inspect_health({"PROFILE": "zram-fast", "DEVICE": "/dev/zram0"},
                                 snapshot(["/dev/sda2"]))
        self.assertEqual(report["status"], "critical")
        self.assertIn("configured_zram_not_active", [x["code"] for x in report["issues"]])

    def test_zswap_first_requires_enabled_zswap_and_backing_swap(self):
        cfg = {"PROFILE": "zswap-first", "DEVICE": "/dev/zram0", "BACKING_SWAP": "/swapfile"}
        report = inspect_health(cfg, snapshot(["/swapfile"], zswap_enabled="Y"))
        self.assertEqual(report["status"], "healthy")
        bad = inspect_health(cfg, snapshot(["/swapfile"], zswap_enabled="N"))
        self.assertEqual(bad["status"], "critical")

    def test_hybrid_requires_both_zram_and_zswap(self):
        cfg = {"PROFILE": "hybrid-exp", "DEVICE": "/dev/zram0"}
        report = inspect_health(cfg, snapshot(["/dev/zram0"], zswap_enabled="Y"))
        self.assertEqual(report["status"], "healthy")
        bad = inspect_health(cfg, snapshot(["/dev/zram0"], zswap_enabled="N"))
        self.assertEqual(bad["status"], "critical")

    def test_zswap_fast_warns_if_zswap_remains_enabled(self):
        report = inspect_health({"PROFILE": "zram-fast", "DEVICE": "/dev/zram0"},
                                 snapshot(["/dev/zram0"], zswap_enabled="Y"))
        self.assertEqual(report["status"], "warning")
        self.assertIn("zswap_should_be_disabled", [x["code"] for x in report["issues"]])

    def test_multiple_zram_swap_devices_are_reported_as_warning(self):
        report = inspect_health({"PROFILE": "zram-fast", "DEVICE": "/dev/zram0"},
                                 snapshot(["/dev/zram0", "/dev/zram1"]))
        self.assertEqual(report["status"], "warning")
        self.assertIn("multiple_zram_swaps", [x["code"] for x in report["issues"]])

    def test_no_swap_active_is_critical(self):
        report = inspect_health({"PROFILE": "zram-fast", "DEVICE": "/dev/zram0"},
                                 snapshot([]))
        self.assertEqual(report["status"], "critical")
        self.assertIn("no_active_swap", [x["code"] for x in report["issues"]])

    def test_missing_zswap_telemetry_is_unknown_not_disabled(self):
        cfg = {"PROFILE": "zswap-first", "DEVICE": "/dev/zram0", "BACKING_SWAP": "/swapfile"}
        report = inspect_health(cfg, snapshot(["/swapfile"], zswap_enabled=None))
        codes = [item["code"] for item in report["issues"]]
        self.assertEqual(report["status"], "warning")
        self.assertIsNone(report["zswap_enabled"])
        self.assertEqual(report["zswap_state"], "unknown")
        self.assertIn("zswap_state_unknown", codes)
        self.assertNotIn("zswap_disabled", codes)

    def test_unrecognized_zswap_value_is_not_treated_as_disabled(self):
        cfg = {"PROFILE": "hybrid-exp", "DEVICE": "/dev/zram0"}
        report = inspect_health(cfg, snapshot(["/dev/zram0"], zswap_enabled="maybe"))
        codes = [item["code"] for item in report["issues"]]
        self.assertEqual(report["status"], "warning")
        self.assertEqual(report["zswap_state"], "unknown")
        self.assertIn("zswap_state_unknown", codes)
        self.assertNotIn("hybrid_zswap_disabled", codes)


if __name__ == "__main__":
    unittest.main()
