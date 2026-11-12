import os
import stat
import tempfile
import unittest
from pathlib import Path

from compresso.profilectl import (
    ProfileConfigError,
    list_profiles,
    set_profile,
    show_profile,
)


class CompressoctlProfileTests(unittest.TestCase):
    def make_config(self, root, content=None):
        path = Path(root) / "memory.conf"
        path.write_text(
            content or (
                "# CompressOS-HAL test config\n"
                "PROFILE=zram-fast\n"
                "ALGORITHM=lz4\n"
                "BACKING_SWAP=/swapfile\n"
            )
        )
        path.chmod(0o640)
        return path

    def test_profile_list_exposes_only_supported_profiles(self):
        self.assertEqual(
            [item["name"] for item in list_profiles()],
            ["zram-fast", "zswap-first", "hybrid-exp"],
        )

    def test_show_reports_persistent_profile_without_mutating_config(self):
        with tempfile.TemporaryDirectory() as root:
            path = self.make_config(root)
            before = path.read_bytes()
            result = show_profile(path)
            self.assertEqual(result["profile"], "zram-fast")
            self.assertFalse(result["applied"])
            self.assertEqual(result["effect"], "configuration-only")
            self.assertEqual(path.read_bytes(), before)

    def test_set_updates_only_profile_and_preserves_file_mode(self):
        with tempfile.TemporaryDirectory() as root:
            path = self.make_config(root)
            before_lines = path.read_text().splitlines()
            result = set_profile(path, "zswap-first")
            after_lines = path.read_text().splitlines()
            self.assertEqual(result["profile"], "zswap-first")
            self.assertTrue(result["changed"])
            self.assertFalse(result["applied"])
            self.assertEqual(
                [line for line in after_lines if not line.startswith("PROFILE=")],
                [line for line in before_lines if not line.startswith("PROFILE=")],
            )
            self.assertIn("PROFILE=zswap-first", after_lines)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)

    def test_set_rejects_profile_incompatible_with_existing_backing_swap(self):
        with tempfile.TemporaryDirectory() as root:
            path = self.make_config(root)
            before = path.read_bytes()
            with self.assertRaises(ProfileConfigError):
                set_profile(path, "hybrid-exp")
            self.assertEqual(path.read_bytes(), before)

    def test_set_rejects_zswap_first_without_explicit_backing_swap(self):
        with tempfile.TemporaryDirectory() as root:
            path = self.make_config(
                root,
                "PROFILE=zram-fast\nALGORITHM=lz4\nBACKING_SWAP=\n",
            )
            before = path.read_bytes()
            with self.assertRaises(ProfileConfigError):
                set_profile(path, "zswap-first")
            self.assertEqual(path.read_bytes(), before)

    def test_set_rejects_unknown_profile_without_writing(self):
        with tempfile.TemporaryDirectory() as root:
            path = self.make_config(root)
            before = path.read_bytes()
            with self.assertRaises(ProfileConfigError):
                set_profile(path, "unsafe-profile")
            self.assertEqual(path.read_bytes(), before)

    def test_set_refuses_symlink_config(self):
        with tempfile.TemporaryDirectory() as root:
            target = self.make_config(root)
            link = Path(root) / "linked.conf"
            link.symlink_to(target)
            before = target.read_bytes()
            with self.assertRaises(ProfileConfigError):
                set_profile(link, "zswap-first")
            self.assertEqual(target.read_bytes(), before)

    def test_set_refuses_duplicate_profile_keys(self):
        with tempfile.TemporaryDirectory() as root:
            path = self.make_config(root, "PROFILE=zram-fast\nPROFILE=zswap-first\n")
            before = path.read_bytes()
            with self.assertRaises(ProfileConfigError):
                set_profile(path, "hybrid-exp")
            self.assertEqual(path.read_bytes(), before)

    def test_installer_and_cli_wire_profile_helper(self):
        root = Path(__file__).parents[1]
        cli = (root / "scripts" / "compressoctl").read_text()
        installer = (root / "scripts" / "install-mint.sh").read_text()
        self.assertIn("profile)", cli)
        self.assertIn('profilectl.py" /usr/libexec/compresso/profilectl.py', installer)
        self.assertIn('if [[ -L /etc/compresso/memory.conf ]]', installer)
        self.assertIn('Preservando configuración existente', installer)


if __name__ == "__main__":
    unittest.main()
