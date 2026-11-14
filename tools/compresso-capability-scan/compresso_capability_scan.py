#!/usr/bin/env python3
import argparse
import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

def run(cmd, timeout=8):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return {"ok": p.returncode == 0, "code": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
    except Exception as exc:
        return {"ok": False, "code": None, "stdout": "", "stderr": str(exc)}

def which(name):
    return shutil.which(name) is not None

def bytes_to_gb(value):
    try:
        return round(int(value) / (1024**3), 2)
    except Exception:
        return 0.0

def read_text(path):
    try:
        return Path(path).read_text(errors="replace").strip()
    except Exception:
        return ""

def detect_os():
    data = {"system": platform.system(), "release": platform.release(), "machine": platform.machine(), "python": platform.python_version()}
    if platform.system() == "Linux":
        os_release = {}
        for line in read_text("/etc/os-release").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                os_release[k] = v.strip().strip('"')
        data["distribution"] = os_release.get("PRETTY_NAME") or os_release.get("NAME")
        data["id"] = os_release.get("ID")
        data["version_id"] = os_release.get("VERSION_ID")
    elif platform.system() == "Windows":
        data["distribution"] = platform.platform()
    return data

def detect_cpu():
    info = {"logical_cores": os.cpu_count() or 0, "physical_cores": None, "model": None, "max_mhz": None}
    if platform.system() == "Linux":
        r = run(["lscpu"])
        if r["ok"]:
            for line in r["stdout"].splitlines():
                key, _, val = line.partition(":")
                key, val = key.strip(), val.strip()
                if key == "Model name":
                    info["model"] = val
                elif key == "CPU(s)":
                    try: info["logical_cores"] = int(val)
                    except: pass
                elif key == "Core(s) per socket":
                    try:
                        cores = int(val)
                        sockets = 1
                        sm = re.search(r"Socket\(s\):\s+(\d+)", r["stdout"])
                        if sm: sockets = int(sm.group(1))
                        info["physical_cores"] = cores * sockets
                    except: pass
                elif key == "CPU max MHz":
                    try: info["max_mhz"] = float(val)
                    except: pass
        if not info["model"]:
            for line in read_text("/proc/cpuinfo").splitlines():
                if "model name" in line.lower() and ":" in line:
                    info["model"] = line.split(":",1)[1].strip()
                    break
    else:
        info["model"] = platform.processor() or None
    return info

def detect_memory():
    out = {"total_gb": 0.0, "available_gb": None, "swap_total_gb": None, "speed_mt_s": [], "zram": [], "zswap": None}
    if platform.system() == "Linux":
        mem = {}
        for line in read_text("/proc/meminfo").splitlines():
            if ":" in line:
                k, v = line.split(":",1)
                m = re.search(r"(\d+)", v)
                if m: mem[k] = int(m.group(1)) * 1024
        out["total_gb"] = bytes_to_gb(mem.get("MemTotal", 0))
        out["available_gb"] = bytes_to_gb(mem.get("MemAvailable", 0))
        out["swap_total_gb"] = bytes_to_gb(mem.get("SwapTotal", 0))
        for z in sorted(Path("/sys/block").glob("zram*")):
            out["zram"].append({"device": str(z.name), "size_gb": bytes_to_gb(read_text(z / "disksize") or 0), "algorithm": read_text(z / "comp_algorithm")})
        zs = read_text("/sys/module/zswap/parameters/enabled")
        if zs:
            out["zswap"] = zs
        dm = run(["sudo", "-n", "dmidecode", "--type", "memory"], timeout=5) if which("sudo") and which("dmidecode") else {"ok":False,"stdout":""}
        if dm["ok"]:
            speeds = []
            for m in re.finditer(r"(?:Configured Memory Speed|Speed):\s*(\d+)\s*MT/s", dm["stdout"]):
                speeds.append(int(m.group(1)))
            out["speed_mt_s"] = sorted(set(speeds))
    return out

def detect_storage():
    u = shutil.disk_usage(Path("/"))
    return {"root_total_gb": round(u.total/(1024**3),2), "root_free_gb": round(u.free/(1024**3),2), "root_used_gb": round(u.used/(1024**3),2)}

def detect_gpu():
    result = {"present": False, "devices": [], "vram_gb": 0.0, "vulkan": False, "vulkan_summary": None, "shader_tools": {}}
    if platform.system() == "Linux":
        if which("lspci"):
            r = run(["lspci", "-nnk"])
            if r["ok"]:
                blocks = r["stdout"].split("\n\n")
                for block in blocks:
                    if re.search(r"(VGA compatible controller|Display controller|3D controller)", block, re.I):
                        result["devices"].append(block)
        result["present"] = bool(result["devices"])
        for p in Path("/sys/class/drm").glob("card*/device/mem_info_vram_total"):
            v = read_text(p)
            if v.isdigit():
                result["vram_gb"] = max(result["vram_gb"], bytes_to_gb(v))
        if which("nvidia-smi"):
            r = run(["nvidia-smi", "--query-gpu=memory.total,name,driver_version", "--format=csv,noheader,nounits"])
            if r["ok"]:
                for line in r["stdout"].splitlines():
                    parts = [x.strip() for x in line.split(",")]
                    if parts and parts[0].isdigit():
                        result["vram_gb"] = max(result["vram_gb"], round(int(parts[0])/1024,2))
                        result["present"] = True
        if which("vulkaninfo"):
            v = run(["vulkaninfo", "--summary"], timeout=12)
            result["vulkan"] = v["ok"] and ("GPU" in v["stdout"] or "deviceName" in v["stdout"] or "Vulkan Instance Version" in v["stdout"])
            result["vulkan_summary"] = v["stdout"][-12000:] if v["stdout"] else v["stderr"][-4000:]
    result["shader_tools"] = {"glslc": which("glslc"), "glslangValidator": which("glslangValidator"), "spirv-val": which("spirv-val")}
    return result

def detect_audio():
    tools = {n: which(n) for n in ["ffmpeg", "pw-cli", "pactl", "arecord", "sox"]}
    servers = []
    if which("pactl"):
        r = run(["pactl", "info"])
        if r["ok"]:
            servers.append("PulseAudio/PipeWire-Pulse")
    if which("pw-cli"):
        servers.append("PipeWire")
    return {"tools": tools, "audio_stack": sorted(set(servers)), "capture_candidate": any(tools.values())}

def detect_software():
    names = ["ffmpeg","obs","kdenlive","shotcut","blender","node","npm","n8n","docker","podman","python3","git","curl","ssh","tailscale","lemonade","ollama","vulkaninfo","cmake"]
    found = {n: which(n) for n in names}
    found.update({
        "davinci_resolve": any(Path(p).exists() for p in ["/opt/resolve/bin/resolve", "/usr/bin/resolve"]),
        "comfyui_hint": any(Path.home().glob("**/ComfyUI")) if os.environ.get("COMPRESSO_DEEP_SCAN") == "1" else False,
    })
    return found

def detect_lemonade():
    out = {"lemonade": which("lemonade"), "status": None, "backends": None, "downloaded_models": None}
    if out["lemonade"]:
        s = run(["lemonade", "status", "--json"], timeout=10)
        if s["ok"]:
            try: out["status"] = json.loads(s["stdout"])
            except Exception: out["status"] = s["stdout"]
        b = run(["lemonade", "backends"], timeout=15)
        out["backends"] = b["stdout"] if b["stdout"] else b["stderr"]
        m = run(["lemonade", "list", "--downloaded"], timeout=20)
        out["downloaded_models"] = m["stdout"] if m["stdout"] else m["stderr"]
    return out

def classify_capabilities(facts):
    ram = float(facts.get("ram_gb") or facts.get("memory",{}).get("total_gb") or 0)
    disk = float(facts.get("disk_free_gb") or facts.get("storage",{}).get("root_free_gb") or 0)
    gpu = facts.get("gpu",{})
    software = facts.get("software",{})
    ai = facts.get("ai",{})
    vulkan = bool(gpu.get("vulkan"))
    vram = float(gpu.get("vram_gb") or 0)
    lemonade = bool(ai.get("lemonade"))
    chat_ready = lemonade and ram >= 8
    image_candidate = vulkan and ram >= 8 and disk >= 10
    video_local = vulkan and vram >= 8 and ram >= 24 and disk >= 30
    audio_candidate = bool(software.get("ffmpeg")) or lemonade
    automation_candidate = bool(software.get("n8n") or software.get("node") or software.get("docker") or software.get("python3"))
    return {"profiles": {
        "local_chat": {"ready": chat_ready, "candidate": ram >= 8, "reason": "Lemonade + >=8 GB RAM" if chat_ready else "Requires a local AI runtime and sufficient RAM", "recommended_backends": ["llamacpp:vulkan"] if vulkan else ["llamacpp:cpu"]},
        "image_generation": {"ready": False, "candidate": image_candidate, "reason": "Vulkan-capable GPU and sufficient disk/RAM detected" if image_candidate else "Needs Vulkan-capable GPU plus storage/RAM validation", "recommended_backends": ["sd-cpp:vulkan"] if vulkan else ["sd-cpp:cpu"], "note": "Candidate means worth testing; actual model fit depends on VRAM/RAM/model size."},
        "video_generation": {"ready": video_local, "candidate": vulkan and ram >= 16, "mode": "local_candidate" if video_local else "hybrid_or_remote", "reason": "Local video is hardware/model dependent; low VRAM should use remote or hybrid processing."},
        "audio_transcription": {"ready": False, "candidate": audio_candidate, "recommended_backends": ["whispercpp:vulkan"] if vulkan else ["moonshine:cpu", "whispercpp:cpu"]},
        "automation": {"ready": bool(software.get("n8n")), "candidate": automation_candidate, "recommended_stack": ["n8n", "MCP", "Python", "Node.js"]},
    }}

def build_report():
    report = {"os": detect_os(), "cpu": detect_cpu(), "memory": detect_memory(), "storage": detect_storage(), "gpu": detect_gpu(), "audio": detect_audio(), "software": detect_software(), "ai": detect_lemonade()}
    report["assessment"] = classify_capabilities({"memory": report["memory"], "storage": report["storage"], "gpu": report["gpu"], "software": report["software"], "ai": {"lemonade": report["ai"]["lemonade"]}})
    return report

def markdown(report):
    p = report["assessment"]["profiles"]
    lines = ["# CompressOS Capability Scan","",f"- OS: {report['os'].get('distribution') or report['os'].get('system')}",f"- CPU: {report['cpu'].get('model') or 'unknown'}",f"- Logical cores: {report['cpu'].get('logical_cores')}",f"- RAM: {report['memory'].get('total_gb')} GB",f"- Root free disk: {report['storage'].get('root_free_gb')} GB",f"- Vulkan: {'yes' if report['gpu'].get('vulkan') else 'no'}",f"- VRAM detected: {report['gpu'].get('vram_gb')} GB","","## Candidate profiles"]
    for name, info in p.items():
        lines.append(f"- {name}: ready={info.get('ready')} candidate={info.get('candidate')} {info.get('mode','')}")
    lines += ["", "## Installed software"]
    for k,v in sorted(report["software"].items()):
        lines.append(f"- {k}: {'yes' if v else 'no'}")
    return "\n".join(lines) + "\n"

def main():
    ap = argparse.ArgumentParser(description="Read-only CompressOS hardware/software capability scanner")
    ap.add_argument("--json", dest="json_path", default="compresso-scan.json")
    ap.add_argument("--report", dest="report_path", default="compresso-scan.md")
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()
    report = build_report()
    Path(args.json_path).write_text(json.dumps(report, ensure_ascii=False, indent=2))
    Path(args.report_path).write_text(markdown(report))
    if args.stdout:
        print(markdown(report))
    else:
        print(f"JSON: {Path(args.json_path).resolve()}")
        print(f"Report: {Path(args.report_path).resolve()}")

if __name__ == "__main__":
    main()
