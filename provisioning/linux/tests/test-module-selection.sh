#!/usr/bin/env bash
set -euo pipefail

SCRIPT="provisioning/linux/remote-bootstrap.sh"

# --apply no debe instalar HAL automáticamente.
if grep -Eq '^install_memory$' "$SCRIPT"; then
    echo "FAIL: HAL se instala sin selección explícita"
    exit 1
fi

# Lemonade debe requerir selección explícita.
grep -Fq 'INSTALL_LEMONADE' "$SCRIPT"

# zVGA debe requerir selección explícita.
grep -Fq 'BUILD_ZVGA' "$SCRIPT"

echo "PASS: selección explícita de módulos"
