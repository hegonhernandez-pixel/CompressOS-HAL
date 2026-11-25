#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path
import re

s = Path("provisioning/linux/remote-bootstrap.sh").read_text()

checks = {
    "HAL": (
        'if [[ "$INSTALL_HAL" -eq 1 ]]; then',
        '  install_memory'
    ),
    "Lemonade": (
        'if [[ "$INSTALL_LEMONADE" -eq 1 ]]; then',
        '  bash "$REPO_DIR/provisioning/linux/install-lemonade.sh"'
    ),
    "zVGA": (
        'if [[ "$BUILD_ZVGA" -eq 1 ]]; then',
        '  install_zvga_deps'
    ),
}

for name, (condition, action) in checks.items():
    assert condition in s, f"{name}: falta condición"
    assert action in s, f"{name}: falta ejecución"
    print(f"PASS: {name} tiene selección independiente")

assert re.search(
    r'No modules selected\. Nothing to install\."\s*\n\s*exit 0',
    s
), "Falta protección sin módulos"

print("PASS: protección contra instalación vacía")
PY
