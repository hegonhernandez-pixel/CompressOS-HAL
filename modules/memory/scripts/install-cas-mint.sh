#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi
for command_name in python3 systemctl install; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "Missing required command: $command_name" >&2
    exit 1
  }
done
python3 -c 'import sqlite3' || {
  echo "Python 3 SQLite support is required." >&2
  exit 1
}

echo "[1/4] Running CAS regression tests..."
PYTHONPATH="$ROOT/src" python3 -m unittest discover -s "$ROOT/tests" -p 'test_cas_registry.py' -v
python3 -m py_compile "$ROOT/scripts/compresso-cas" "$ROOT/scripts/compresso-auditd"

echo "[2/4] Installing user-space CAS tools..."
install -d -m 0755 /usr/lib/compresso/compresso_cas /usr/bin /etc/compresso /var/lib/compresso/cas
install -m 0644 "$ROOT"/src/compresso_cas/*.py /usr/lib/compresso/compresso_cas/
install -m 0755 "$ROOT/scripts/compresso-cas" /usr/bin/compresso-cas
install -m 0755 "$ROOT/scripts/compresso-auditd" /usr/bin/compresso-auditd

echo "[3/4] Installing rules without overwriting existing configuration..."
for config in daemon-audit.conf daemon-hybrid.conf aot-rules.conf boot-index.conf; do
  if [[ ! -e "/etc/compresso/$config" ]]; then
    install -m 0644 "$ROOT/config/$config" "/etc/compresso/$config"
  else
    echo "Preserving existing /etc/compresso/$config"
  fi
done
install -m 0644 "$ROOT/systemd/compresso-auditd.service" /etc/systemd/system/compresso-auditd.service

echo "[4/4] Enabling the low-priority auditor..."
systemctl daemon-reload
systemctl enable compresso-auditd.service
if systemctl is-active --quiet compresso-auditd.service; then
  systemctl restart compresso-auditd.service
else
  systemctl start compresso-auditd.service
fi

echo "CAS tools installed. No swap, kernel, zswap or GPU sysfs settings were changed."
systemctl --no-pager --full status compresso-auditd.service || true
