import unittest
from compresso_capability_scan import classify_capabilities

class CapabilityTests(unittest.TestCase):
    def test_creator_image_profile_with_vulkan_and_4gb_vram(self):
        facts = {"ram_gb": 16, "disk_free_gb": 80, "gpu": {"present": True, "vram_gb": 4, "vulkan": True}, "software": {"ffmpeg": True}, "ai": {"lemonade": True}}
        result = classify_capabilities(facts)
        self.assertTrue(result["profiles"]["local_chat"]["ready"])
        self.assertTrue(result["profiles"]["image_generation"]["candidate"])
        self.assertIn("sd-cpp:vulkan", result["profiles"]["image_generation"]["recommended_backends"])

    def test_video_local_is_not_claimed_ready_on_low_vram(self):
        facts = {"ram_gb": 16, "disk_free_gb": 80, "gpu": {"present": True, "vram_gb": 4, "vulkan": True}, "software": {"ffmpeg": True}, "ai": {"lemonade": True}}
        result = classify_capabilities(facts)
        self.assertFalse(result["profiles"]["video_generation"]["ready"])
        self.assertEqual(result["profiles"]["video_generation"]["mode"], "hybrid_or_remote")

    def test_automation_profile_detects_n8n_or_node(self):
        facts = {"ram_gb": 8, "disk_free_gb": 20, "gpu": {"present": False, "vram_gb": 0, "vulkan": False}, "software": {"ffmpeg": False, "node": True, "n8n": False, "docker": False}, "ai": {"lemonade": False}}
        result = classify_capabilities(facts)
        self.assertTrue(result["profiles"]["automation"]["candidate"])

if __name__ == "__main__":
    unittest.main()
