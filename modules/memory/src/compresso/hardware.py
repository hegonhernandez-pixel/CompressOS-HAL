#!/usr/bin/env python3
"""Read-only host, GPU/Vulkan and memory-layer inventory for CompressOS-HAL."""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shlex
import stat
import subprocess
import sys
from pathlib import Path

try:
    from .metrics import collect_metrics
except ImportError:  # direct execution from the installed libexec directory
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from compresso.metrics import collect_metrics


_VIRTUAL_MARKERS = (
    "qemu", "kvm", "virtualbox", "vmware", "xen", "bochs",
    "parallels", "openstack", "bhyve", "amazon ec2", "virtual machine",
)


def _read(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None


def _parse_os_release(path):
    values = {}
    text = _read(path)
    if text is None:
        return values
    for line in text.splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw = line.split("=", 1)
        try:
            parsed = shlex.split(raw, comments=False, posix=True)
            values[key] = parsed[0] if parsed else ""
        except ValueError:
            values[key] = raw.strip().strip('"').strip("'")
    return values


def _cpu_model(path):
    text = _read(path)
    if not text:
        return None
    for prefix in ("model name", "hardware", "processor"):
        for line in text.splitlines():
            if line.lower().startswith(prefix) and ":" in line:
                return line.split(":", 1)[1].strip()
    return None


def _virtualization(sys_root):
    dmi = Path(sys_root) / "class" / "dmi" / "id"
    fields = ("sys_vendor", "product_name", "board_vendor", "board_name", "bios_vendor")
    values = {name: _read(dmi / name) for name in fields}
    indicators = []
    for value in values.values():
        if value:
            lowered = value.lower()
            if any(marker in lowered for marker in _VIRTUAL_MARKERS):
                indicators.append(value)
    hypervisor_type = _read(Path(sys_root) / "hypervisor" / "type")
    if hypervisor_type:
        indicators.append(hypervisor_type)
    return {
        "status": "suspected_virtualized" if indicators else "unknown",
        "indicators": sorted(set(indicators)),
        "dmi": values,
        "note": "No virtualization marker is not proof of physical hardware.",
    }


def _drm_devices(sys_root):
    result = []
    drm_root = Path(sys_root) / "class" / "drm"
    if not drm_root.is_dir():
        return result
    for card in sorted(drm_root.glob("card[0-9]*")):
        if not re.fullmatch(r"card[0-9]+", card.name):
            continue
        device = card / "device"
        if not device.exists():
            continue
        driver_path = device / "driver"
        try:
            driver_target = os.readlink(driver_path)
            driver = Path(driver_target).name
        except OSError:
            driver = driver_path.name if driver_path.exists() else None
        result.append({
            "card": card.name,
            "vendor_id": _read(device / "vendor"),
            "device_id": _read(device / "device"),
            "subsystem_vendor_id": _read(device / "subsystem_vendor"),
            "subsystem_device_id": _read(device / "subsystem_device"),
            "driver": driver,
        })
    return result


def _render_nodes(dev_root):
    result = []
    root = Path(dev_root) / "dri"
    if not root.is_dir():
        return result
    for node in sorted(root.glob("renderD[0-9]*")):
        try:
            info = node.stat()
            result.append({
                "path": str(node),
                "mode": format(stat.S_IMODE(info.st_mode), "04o"),
                "uid": info.st_uid,
                "gid": info.st_gid,
                "readable": os.access(node, os.R_OK),
                "writable": os.access(node, os.W_OK),
            })
        except OSError:
            continue
    return result


def _vulkan_summary(runner):
    try:
        result = runner(
            ["vulkaninfo", "--summary"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except FileNotFoundError:
        return {"available": False, "reason": "vulkaninfo_not_installed", "devices": []}
    except subprocess.TimeoutExpired:
        return {"available": False, "reason": "vulkaninfo_timeout", "devices": []}
    except OSError as exc:
        return {"available": False, "reason": "vulkaninfo_error", "error": str(exc), "devices": []}

    summary = (result.stdout or "").strip()
    error = (result.stderr or "").strip()
    devices = [
        match.strip()
        for match in re.findall(r"^\s*deviceName\s*=\s*(.+?)\s*$", summary, flags=re.MULTILINE)
    ]
    report = {
        "available": result.returncode == 0,
        "returncode": result.returncode,
        "devices": devices,
        "summary": summary[:20000],
    }
    if result.returncode != 0:
        report["reason"] = "vulkaninfo_failed"
        report["error"] = error[:4000]
    return report


def collect_hardware(
    *,
    proc_root="/proc",
    sys_root="/sys",
    dev_root="/dev",
    etc_root="/etc",
    runner=None,
    kernel_release=None,
    machine=None,
):
    """Return a read-only inventory; never writes sysfs, procfs, swap or services."""
    proc = Path(proc_root)
    sys = Path(sys_root)
    os_release = _parse_os_release(Path(etc_root) / "os-release")
    run = runner or subprocess.run
    metrics = collect_metrics(proc_root=proc, sys_root=sys)

    return {
        "schema_version": 1,
        "system": {
            "os": {
                "id": os_release.get("ID"),
                "id_like": os_release.get("ID_LIKE"),
                "name": os_release.get("PRETTY_NAME") or os_release.get("NAME"),
                "version_id": os_release.get("VERSION_ID"),
            },
            "kernel": kernel_release or platform.release(),
            "architecture": machine or platform.machine(),
            "cpu_model": _cpu_model(proc / "cpuinfo"),
            "virtualization": _virtualization(sys),
        },
        "gpu": {
            "drm_devices": _drm_devices(sys),
            "render_nodes": _render_nodes(dev_root),
            "vulkan": _vulkan_summary(run),
        },
        "memory_runtime": {
            "memory_kb": metrics["memory_kb"],
            "vmstat": metrics["vmstat"],
            "active_swaps": metrics["active_swaps"],
            "zram": metrics["zram"],
            "zswap": metrics["zswap"],
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proc-root", default="/proc")
    parser.add_argument("--sys-root", default="/sys")
    parser.add_argument("--dev-root", default="/dev")
    parser.add_argument("--etc-root", default="/etc")
    args = parser.parse_args(argv)
    report = collect_hardware(
        proc_root=args.proc_root,
        sys_root=args.sys_root,
        dev_root=args.dev_root,
        etc_root=args.etc_root,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
