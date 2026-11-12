#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi
if command -v systemctl >/dev/null 2>&1; then
  systemctl disable --now compresso-auditd.service 2>/dev/null || true
fi
rm -f /etc/systemd/system/compresso-auditd.service
rm -f /usr/bin/compresso-cas /usr/bin/compresso-auditd
rm -rf /usr/lib/compresso/compresso_cas
systemctl daemon-reload 2>/dev/null || true
echo "CAS executables and service removed."
echo "Preserved /etc/compresso configuration and /var/lib/compresso/cas data."
