import unittest
from compresso_capability_scan import classify_capabilities

class CapabilityTests(unittest.TestCase):
    def test_creator_image_profile_with_vulkan_and_4gb_vram(self):
        facts = {"ram_gb": 16, "disk_free_gb": 80, "gpu": {"present": True, "vram_gb": 4, "vulkan": True}, "software": {"ffmpeg": True}, "ai": {"lemonade": True}}
        result = classify_capabilities(facts)
        self.assertTrue(result["profiles"]["local_chat"]["ready"])
        self.assertTrue(result["profiles"]["image_generation"]["candidate"])
        self.assertIn("sd-cpp:vulkan", result["profiles"]["image_generation"]["recommended_backends"])

    def test_installed_sd_vulkan_and_model_override_low_disk_candidate_gate(self):
        facts = {
            "ram_gb": 15.5,
            "disk_free_gb": 1.28,
            "gpu": {"present": True, "vram_gb": 3.98, "vulkan": True},
            "software": {"ffmpeg": False},
            "ai": {
                "lemonade": True,
                "backends": """sd-cpp              cpu         core          native     installed
                    rocm        core          native     installed
                    vulkan      core          native     installed""",
                "downloaded_models": """SD-Turbo                                Yes                4.86       sd-cpp"""
            }
        }
        result = classify_capabilities(facts)
        image = result["profiles"]["image_generation"]
        self.assertTrue(image["installed"])
        self.assertTrue(image["candidate"])
        self.assertIn("low_disk_space", image["warnings"])

    def test_successful_image_validation_marks_ready(self):
        facts = {
            "ram_gb": 15.5,
            "disk_free_gb": 1.28,
            "gpu": {"present": True, "vram_gb": 3.98, "vulkan": True},
            "software": {},
            "ai": {
                "lemonade": True,
                "backends": "sd-cpp vulkan installed",
                "downloaded_models": "SD-Turbo Yes 4.86 sd-cpp"
            },
            "validation": {"image_generation": True},
        }
        image = classify_capabilities(facts)["profiles"]["image_generation"]
        self.assertTrue(image["validated"])
        self.assertTrue(image["ready"])

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
