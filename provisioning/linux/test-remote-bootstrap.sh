#!/usr/bin/env bash
set -euo pipefail
SCRIPT="$(cd "$(dirname "$0")" && pwd)/remote-bootstrap.sh"

grep -Fq 'APPLY=0' "$SCRIPT"
grep -Fq 'ENABLE_MEMORY=0' "$SCRIPT"
grep -Fq -- '--apply' "$SCRIPT"
grep -Fq -- '--enable-memory' "$SCRIPT"
grep -Fq 'memoryd.py --dry-run' "$SCRIPT"
grep -Fq 'systemctl enable --now compresso-memoryd.service' "$SCRIPT"
grep -Fq 'install-lemonade.sh' "$SCRIPT"
grep -Fq 'lemonade backends --all' "$(dirname "$SCRIPT")/install-lemonade.sh"
grep -Fq 'cmake --build' "$SCRIPT"
grep -Fq 'COMPRESSO_VULKAN_HELPER=' "$SCRIPT"

bash -n "$SCRIPT"
printf 'remote bootstrap static safety checks: OK\n'
