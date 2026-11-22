#!/usr/bin/env python3
"""Puente de soporte Linux para Python 3.8+, solo biblioteca estándar."""
import argparse
import hmac
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BIND = "127.0.0.1"
PORT = 7890
ORIGINS = {
    "https://hegonhernandez-pixel.github.io",
    "https://compresso-lab-local.whitespoonbill5.chatgpt.site",
}
ACTIONS = {
    "status": ["/usr/bin/uname", "-smr"],
    "uptime": ["/usr/bin/uptime", "-p"],
    "disk": ["/usr/bin/df", "-h", "/"],
    "systemctl": ["/usr/bin/systemctl", "show", "--property=Id,ActiveState,SubState",
                  "compresso-memoryd.service", "compresso-metricsd.service",
                  "compresso-supervisord.service", "lemonade-server.service", "anythingllm.service"],
    "swapon": ["/usr/sbin/swapon", "--show=TYPE,SIZE,USED,PRIO", "--bytes"],
    "hal_metrics": ["/usr/local/bin/compressoctl", "metrics"],
}
CONFIG = Path.home() / ".config" / "compressos-factory"
HELPER = "/usr/local/sbin/compresso-factory-services"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())


def save_private(path, data):
    CONFIG.mkdir(mode=0o700, parents=True, exist_ok=True)
    if CONFIG.is_symlink() or CONFIG.stat().st_uid != os.getuid():
        raise ValueError("Directorio de credenciales inseguro")
    CONFIG.chmod(0o700)
    fd, temporary = tempfile.mkstemp(dir=str(CONFIG))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def execute(argv):
    try:
        run = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, timeout=3, check=False,
                             env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"})
        return {"ok": run.returncode == 0, "output": run.stdout[:3000].decode("utf-8", "replace")}
    except (OSError, subprocess.TimeoutExpired):
        return {"ok": False, "code": "unavailable"}


def service(operation):
    return execute(["/usr/bin/sudo", "-n", HELPER, operation])["ok"]


def telemetry(previous):
    fields = Path("/proc/stat").read_text().splitlines()[0].split()
    ticks = [int(part) for part in fields[1:9]]
    total, idle = sum(ticks), sum(ticks[3:5])
    cpu = None
    if previous and total > previous[0]:
        cpu = round(100 * (1 - (idle - previous[1]) / (total - previous[0])), 1)
    mem = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines())
    maximum = int(mem["MemTotal"].split()[0])
    available = int(mem["MemAvailable"].split()[0])
    disk = shutil.disk_usage("/")
    units = execute(ACTIONS["systemctl"])
    return (total, idle), {
        "cpu_percent": cpu, "ram_percent": round(100 * (maximum - available) / maximum, 1),
        "disk_percent": round(100 * (disk.total - disk.free) / disk.total, 1),
        "services": units["output"] if units["ok"] else "No disponible",
    }


def uuid_value(value):
    if not isinstance(value, str):
        raise ValueError("UUID requerido")
    return str(uuid.UUID(value))


class Bridge:
    def __init__(self, args):
        self.args = args
        self.lock = threading.RLock()
        self.exit = threading.Event()
        self.safety_exit = threading.Event()
        self.csrf = secrets.token_urlsafe(24)
        self.device = None
        self.owner_origin = None
        self.last_contact = 0
        self.started_services = False
        self.revision = -1
        self.active = False
        self.ack = None
        self.previous = None
        self.task = None
        self.result = None
        self.allow_service = os.environ.get("FACTORY_ALLOW_SERVICE_CONTROL") == "1"
        self.allow_diagnostics = os.environ.get("FACTORY_ALLOW_REMOTE_DIAGNOSTICS") == "1"
        self.service_consent = False
        self.diagnostics_consent = False

    def rpc(self, method, body):
        headers = {"apikey": self.args.anon_key, "Content-Type": "application/json"}
        if not self.args.anon_key.startswith("sb_publishable_"):
            headers["Authorization"] = "Bearer " + self.args.anon_key
        request = urllib.request.Request(
            self.args.supabase_url + "/rest/v1/rpc/" + method,
            data=json.dumps(body).encode(),
            headers=headers,
            method="POST",
        )
        with OPENER.open(request, timeout=4) as reply:
            data = reply.read(65537)
            if len(data) > 65536:
                raise ValueError("Respuesta demasiado grande")
            return json.loads(data) if data else None

    def settings(self, data):
        old_service = self.service_consent
        self.service_consent = self.allow_service and data.get("service") is True
        self.diagnostics_consent = self.allow_diagnostics and data.get("diagnostics") is True
        if old_service and not self.service_consent:
            if not self.stop_services():
                raise OSError("No se pudo detener el servicio local")
            self.revision = -1
            self.active = False
        if not self.diagnostics_consent:
            self.task, self.result = None, None
        return {"service": self.service_consent, "diagnostics": self.diagnostics_consent}

    def pair(self, data, origin):
        session = uuid_value(data.get("session"))
        token = uuid_value(data.get("token"))
        if self.device and self.device["session"] != session:
            raise ValueError("Desconecta el enlace local existente")
        if self.device and self.owner_origin != origin:
            raise ValueError("El enlace pertenece a otro portal")
        if self.device:
            raise ValueError("Ya hay un enlace local")
        device = {"session": session, "id": str(uuid.uuid4()), "secret": secrets.token_hex(32)}
        self.settings(data)
        path = CONFIG / (device["id"] + ".json")
        save_private(path, dict(device, supabase_url=self.args.supabase_url, origin=origin))
        try:
            self.rpc("factory_pair", dict(p_session=session, p_token=token, p_device=device["id"],
                     p_secret=device["secret"], p_service=self.service_consent,
                     p_diagnostics=self.diagnostics_consent))
        except Exception:
            path.unlink(missing_ok=True)
            raise
        self.device = device
        self.owner_origin = origin
        self.last_contact = time.monotonic()
        self.revision = -1
        return {"device": device["id"], "service": self.service_consent,
                "diagnostics": self.diagnostics_consent}

    def stop_services(self):
        if self.started_services and service("stop"):
            self.started_services = False
        return not self.started_services

    def disconnect(self, notify=True):
        self.active = False
        self.task, self.result = None, None
        self.revision = -1
        stopped = self.stop_services()
        device, self.device = self.device, None
        self.owner_origin = None
        if device:
            try:
                if notify:
                    self.sync(device, revoke=True)
            except (OSError, ValueError):
                pass
            finally:
                (CONFIG / (device["id"] + ".json")).unlink(missing_ok=True)
        return stopped

    def sync(self, device, snapshot=None, revoke=False):
        return self.rpc("factory_agent_sync", {
            "p_device": device["id"], "p_secret": device["secret"],
            "p_service": self.service_consent, "p_diagnostics": self.diagnostics_consent,
            "p_revision": self.revision, "p_ack": self.ack, "p_telemetry": snapshot,
            "p_task": self.task, "p_result": self.result, "p_revoke": revoke,
        })

    def update_control(self, reply):
        desired, revision = reply["desired"], reply["revision"]
        if type(revision) is not int or revision < 0 or desired not in ("active", "paused"):
            raise ValueError("Estado de enlace inválido")
        if revision == self.revision:
            return
        self.ack = "session_only"
        self.active = desired == "active"
        if desired != "active" and self.started_services:
            self.ack = "applied" if self.stop_services() else "unavailable"
        elif desired == "active" and self.service_consent:
            # Track uncertain launches too so the local watchdog can always attempt cleanup.
            self.started_services = True
            self.ack = "applied" if service("start") else "unavailable"
            if self.ack == "unavailable":
                self.stop_services()
                self.active = False
        self.revision = revision

    def cycle(self):
        while not self.exit.wait(3):
            with self.lock:
                if not self.device:
                    continue
                if time.monotonic() - self.last_contact > 20:
                    self.disconnect()
                    continue
                try:
                    snapshot = None
                    if self.active and self.diagnostics_consent:
                        self.previous, snapshot = telemetry(self.previous)
                    reply = self.sync(self.device, snapshot)
                    if reply.get("stopped") is True:
                        self.disconnect(notify=False)
                        continue
                    self.last_contact = time.monotonic()
                    self.update_control(reply)
                    self.task, self.result = None, None
                    task = reply.get("task")
                    if self.active and self.diagnostics_consent and task and task.get("kind") in ACTIONS:
                        self.task = uuid_value(task.get("id"))
                        self.result = execute(ACTIONS[task["kind"]])
                except (OSError, ValueError, KeyError, TypeError, AttributeError):
                    continue

    def watchdog(self):
        while not self.safety_exit.wait(2):
            with self.lock:
                if self.started_services and (not self.device or time.monotonic() - self.last_contact > 20):
                    self.stop_services()


def handler(bridge, allowed):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def log_message(self, *_args):
            pass

        def valid_origin(self):
            origin = self.headers.get("Origin")
            host = self.headers.get("Host")
            return origin if origin in allowed and host == f"{BIND}:{PORT}" else None

        def response(self, code, payload, origin=None):
            body = json.dumps(payload).encode() if payload is not None else b""
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            if origin:
                self.send_header("Vary", "Origin")
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Factory-CSRF")
                if self.headers.get("Access-Control-Request-Private-Network") == "true":
                    self.send_header("Access-Control-Allow-Private-Network", "true")
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):
            origin = self.valid_origin()
            self.response(204 if origin else 403, None, origin)

        def do_POST(self):
            origin = self.valid_origin()
            csrf = self.headers.get("X-Factory-CSRF", "").encode()
            if not origin or not hmac.compare_digest(csrf, bridge.csrf.encode()):
                return self.response(403, {"error": "Origen o código local inválido"}, origin)
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0]
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if content_type != "application/json" or not 0 < length <= 2048:
                    raise ValueError("JSON requerido")
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError("JSON inválido")
                with bridge.lock:
                    if self.path == "/pair":
                        result = bridge.pair(data, origin)
                    elif origin != bridge.owner_origin or not bridge.device:
                        return self.response(409, {"error": "No hay enlace local para este portal"}, origin)
                    elif self.path == "/consent":
                        result = bridge.settings(data)
                    elif self.path == "/disconnect":
                        result = {"stopped": bridge.disconnect()}
                    else:
                        return self.response(404, {"error": "Ruta desconocida"}, origin)
                self.response(200, result, origin)
            except urllib.error.HTTPError as exc:
                self.response(409, {"error": f"Supabase rechazó la solicitud ({exc.code})"}, origin)
            except (ValueError, OSError) as exc:
                self.response(400, {"error": str(exc)[:200]}, origin)

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--supabase-url", default=os.environ.get("SUPABASE_URL", ""))
    parser.add_argument("--anon-key", default=os.environ.get("SUPABASE_ANON_KEY", ""))
    parser.add_argument("--site", help="Origen adicional de un ChatGPT Site")
    parser.add_argument("--origin", help="Origen HTTP de desarrollo local explícito")
    args = parser.parse_args()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        parser.error("Ejecuta el agente como tu usuario Linux")
    args.supabase_url = args.supabase_url.rstrip("/")
    if not re.fullmatch(r"https://[a-z0-9]+\.supabase\.co", args.supabase_url):
        parser.error("Configura la URL HTTPS del proyecto Supabase nuevo")
    if not re.fullmatch(r"(sb_publishable_[A-Za-z0-9_-]+|[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)", args.anon_key):
        parser.error("Configura la clave pública de Supabase")
    if not args.anon_key.startswith("sb_publishable_"):
        import base64
        try:
            payload = args.anon_key.split(".")[1]
            role = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))).get("role")
        except (ValueError, AttributeError):
            role = None
        if role != "anon":
            parser.error("La clave JWT debe tener el rol anon")
    allowed = set(ORIGINS)
    if args.site:
        if not re.fullmatch(r"https://[a-z0-9-]+\.[a-z0-9-]+\.chatgpt\.site/?", args.site):
            parser.error("Origen de ChatGPT Site inválido")
        allowed.add(args.site.rstrip("/"))
    if args.origin:
        if not re.fullmatch(r"http://(127\.0\.0\.1|localhost):[0-9]+", args.origin):
            parser.error("El origen de desarrollo debe ser loopback")
        allowed.add(args.origin)
    bridge = Bridge(args)
    with ThreadingHTTPServer((BIND, PORT), handler(bridge, allowed)) as server:
        server.timeout = 0.5
        signal.signal(signal.SIGTERM, lambda *_: bridge.exit.set())
        worker = threading.Thread(target=bridge.cycle, daemon=True)
        watcher = threading.Thread(target=bridge.watchdog, daemon=True)
        worker.start()
        watcher.start()
        print("Puente local en http://127.0.0.1:7890", flush=True)
        print("Código local (solo para el formulario del portal): " + bridge.csrf, flush=True)
        try:
            while not bridge.exit.is_set():
                server.handle_request()
        except KeyboardInterrupt:
            pass
        finally:
            bridge.exit.set()
            with bridge.lock:
                if not bridge.disconnect():
                    print("No se pudieron detener los servicios. Revísalos localmente.", file=sys.stderr)
            bridge.safety_exit.set()


if __name__ == "__main__":
    main()
