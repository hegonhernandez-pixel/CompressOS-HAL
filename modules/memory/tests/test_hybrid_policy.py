import unittest

from compresso_cas.policy import choose_route


class HybridPolicyTests(unittest.TestCase):
    def test_critical_large_read_uses_fast_vram_below_low_watermark(self):
        decision = choose_route("critical", "read", 8 * 1024 * 1024, 40, True)
        self.assertEqual(decision.route, "fast_vram")
        self.assertEqual(decision.reserved_vram_mb, 1024)

    def test_high_vram_pressure_overflows_to_zswap(self):
        decision = choose_route("critical", "read", 8 * 1024 * 1024, 90, True)
        self.assertEqual(decision.route, "zswap")
        self.assertEqual(decision.mode, "overflow")
        self.assertEqual(decision.reserved_vram_mb, 64)

    def test_background_write_is_deferred(self):
        decision = choose_route("background", "write", 4096, 20, True)
        self.assertEqual(decision.route, "nvme_background")

    def test_gpu_unavailable_uses_cpu_fallback_path(self):
        decision = choose_route("critical", "read", 8 * 1024 * 1024, 20, False)
        self.assertEqual(decision.mode, "cpu_fallback")

    def test_hysteresis_band_does_not_allocate_fast_vram(self):
        decision = choose_route("critical", "read", 8 * 1024 * 1024, 72, True)
        self.assertEqual(decision.route, "zswap")


if __name__ == "__main__":
    unittest.main()
