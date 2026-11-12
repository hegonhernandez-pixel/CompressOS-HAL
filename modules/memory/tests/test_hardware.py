import subprocess
import tempfile
import unittest
from pathlib import Path

from compresso.hardware import collect_hardware


class HardwareProbeTests(unittest.TestCase):
    def make_tree(self, root, *, virtualized=False):
        root = Path(root)
        proc = root / "proc"
        sys = root / "sys"
        dev = root / "dev"
        etc = root / "etc"
        (proc / "pressure").mkdir(parents=True)
        (proc / "cpuinfo").write_text(
            "processor : 0\nmodel name : Example CPU 8-Core\n"
        )
        (proc / "meminfo").write_text(
            "MemTotal: 16384000 kB\nMemAvailable: 8192000 kB\n"
            "SwapTotal: 8192000 kB\nSwapFree: 4096000 kB\n"
        )
        (proc / "vmstat").write_text("pswpin 2\npswpout 3\npgfault 4\npgmajfault 5\n")
        (proc / "pressure" / "memory").write_text(
            "some avg10=0.00 avg60=0.00 avg300=0.00 total=0\n"
            "full avg10=0.00 avg60=0.00 avg300=0.00 total=0\n"
        )
        (proc / "swaps").write_text(
            "Filename Type Size Used Priority\n/dev/zram0 partition 4096000 128 100\n"
            "/dev/nvme0n1p4 partition 4096000 0 -2\n"
        )
        etc.mkdir()
        (etc / "os-release").write_text(
            'ID=linuxmint\nID_LIKE="ubuntu debian"\nPRETTY_NAME="Linux Mint 22.3 Zena"\nVERSION_ID="22.3"\n'
        )
        dmi = sys / "class" / "dmi" / "id"
        dmi.mkdir(parents=True)
        (dmi / "sys_vendor").write_text("QEMU" if virtualized else "System Manufacturer")
        (dmi / "product_name").write_text("Standard PC (Q35 + ICH9, 2009)" if virtualized else "System Product Name")
        gpu = sys / "class" / "drm" / "card0" / "device"
        gpu.mkdir(parents=True)
        (gpu / "vendor").write_text("0x10de\n")
        (gpu / "device").write_text("0x2684\n")
        (gpu / "driver").symlink_to("/sys/bus/pci/drivers/nvidia")
        render = dev / "dri"
        render.mkdir(parents=True)
        (render / "renderD128").write_bytes(b"")
        zram = sys / "block" / "zram0"
        zram.mkdir(parents=True)
        (zram / "comp_algorithm").write_text("lzo [lz4] lzo-rle\n")
        (zram / "disksize").write_text("8589934592\n")
        (zram / "mem_limit").write_text("3435973836\n")
        (zram / "mm_stat").write_text("4096 8192 16384 4 5 6 7 8 9\n")
        zswap = sys / "module" / "zswap" / "parameters"
        zswap.mkdir(parents=True)
        (zswap / "enabled").write_text("N\n")
        (zswap / "max_pool_percent").write_text("20\n")
        return proc, sys, dev, etc

    def fake_vulkan(self, *args, **kwargs):
        self.assertEqual(args[0], ["vulkaninfo", "--summary"])
        return subprocess.CompletedProcess(
            args[0], 0,
            "Devices:\nGPU0:\n  deviceName = NVIDIA GeForce RTX 4090\n",
            "",
        )

    def test_collects_os_gpu_driver_vulkan_and_live_memory_layers(self):
        with tempfile.TemporaryDirectory() as root:
            proc, sys, dev, etc = self.make_tree(root)
            report = collect_hardware(
                proc_root=proc, sys_root=sys, dev_root=dev, etc_root=etc,
                runner=self.fake_vulkan, kernel_release="6.14.0-test", machine="x86_64",
            )

        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["system"]["os"]["id"], "linuxmint")
        self.assertEqual(report["system"]["os"]["id_like"], "ubuntu debian")
        self.assertEqual(report["system"]["cpu_model"], "Example CPU 8-Core")
        self.assertEqual(report["system"]["kernel"], "6.14.0-test")
        self.assertEqual(report["system"]["architecture"], "x86_64")
        self.assertEqual(report["gpu"]["drm_devices"][0]["vendor_id"], "0x10de")
        self.assertEqual(report["gpu"]["drm_devices"][0]["driver"], "nvidia")
        self.assertEqual(report["gpu"]["vulkan"]["devices"], ["NVIDIA GeForce RTX 4090"])
        self.assertTrue(report["gpu"]["vulkan"]["available"])
        self.assertEqual(report["memory_runtime"]["zram"]["zram0"]["disksize_bytes"], 8589934592)
        self.assertEqual(report["memory_runtime"]["zswap"]["enabled"], "N")
        self.assertEqual(len(report["memory_runtime"]["active_swaps"]), 2)
        self.assertEqual(report["system"]["virtualization"]["status"], "unknown")

    def test_virtual_machine_markers_are_reported_without_calling_it_physical(self):
        with tempfile.TemporaryDirectory() as root:
            proc, sys, dev, etc = self.make_tree(root, virtualized=True)
            report = collect_hardware(
                proc_root=proc, sys_root=sys, dev_root=dev, etc_root=etc,
                runner=self.fake_vulkan, kernel_release="test", machine="x86_64",
            )
        self.assertEqual(report["system"]["virtualization"]["status"], "suspected_virtualized")
        self.assertIn("QEMU", report["system"]["virtualization"]["indicators"])

    def test_missing_vulkan_tool_is_a_reported_capability_gap(self):
        with tempfile.TemporaryDirectory() as root:
            proc, sys, dev, etc = self.make_tree(root)
            def missing(*args, **kwargs):
                raise FileNotFoundError("vulkaninfo")
            report = collect_hardware(
                proc_root=proc, sys_root=sys, dev_root=dev, etc_root=etc,
                runner=missing, kernel_release="test", machine="x86_64",
            )
        self.assertFalse(report["gpu"]["vulkan"]["available"])
        self.assertEqual(report["gpu"]["vulkan"]["reason"], "vulkaninfo_not_installed")

    def test_vulkan_timeout_is_not_reported_as_a_success(self):
        with tempfile.TemporaryDirectory() as root:
            proc, sys, dev, etc = self.make_tree(root)
            def timeout(*args, **kwargs):
                raise subprocess.TimeoutExpired(["vulkaninfo", "--summary"], 10)
            report = collect_hardware(
                proc_root=proc, sys_root=sys, dev_root=dev, etc_root=etc,
                runner=timeout, kernel_release="test", machine="x86_64",
            )
        self.assertFalse(report["gpu"]["vulkan"]["available"])
        self.assertEqual(report["gpu"]["vulkan"]["reason"], "vulkaninfo_timeout")


    def test_hardware_command_is_installed_and_exposed_by_compressoctl(self):
        root = Path(__file__).parents[1]
        cli = (root / "scripts" / "compressoctl").read_text()
        installer = (root / "scripts" / "install-mint.sh").read_text()
        self.assertIn('hardware)', cli)
        self.assertIn('hardware.py" /usr/libexec/compresso/hardware.py', installer)


    def test_probe_does_not_modify_proc_sys_or_device_fixtures(self):
        with tempfile.TemporaryDirectory() as root:
            proc, sys, dev, etc = self.make_tree(root)
            base = Path(root)
            before = {
                str(path.relative_to(base)): path.read_bytes()
                for path in base.rglob("*") if path.is_file() and not path.is_symlink()
            }
            collect_hardware(
                proc_root=proc, sys_root=sys, dev_root=dev, etc_root=etc,
                runner=self.fake_vulkan, kernel_release="test", machine="x86_64",
            )
            after = {
                str(path.relative_to(base)): path.read_bytes()
                for path in base.rglob("*") if path.is_file() and not path.is_symlink()
            }
        self.assertEqual(after, before)

    def test_vulkan_command_failure_is_reported_not_hidden(self):
        with tempfile.TemporaryDirectory() as root:
            proc, sys, dev, etc = self.make_tree(root)
            def failed(*args, **kwargs):
                return subprocess.CompletedProcess(args[0], 1, "", "no Vulkan ICD")
            report = collect_hardware(
                proc_root=proc, sys_root=sys, dev_root=dev, etc_root=etc,
                runner=failed, kernel_release="test", machine="x86_64",
            )
        self.assertFalse(report["gpu"]["vulkan"]["available"])
        self.assertEqual(report["gpu"]["vulkan"]["reason"], "vulkaninfo_failed")
        self.assertEqual(report["gpu"]["vulkan"]["error"], "no Vulkan ICD")


if __name__ == "__main__":
    unittest.main()
