#!/usr/bin/env bash
set -euo pipefail

SCRIPT="provisioning/linux/remote-bootstrap.sh"

python3 - "$SCRIPT" <<'PY'
from pathlib import Path
import re
import sys

s = Path(sys.argv[1]).read_text()

match = re.search(
    r'^\s*--install-ai-stack\)\s*\n(.*?)^\s*shift\s*;;',
    s,
    re.MULTILINE | re.DOTALL
)

assert match, "No existe --install-ai-stack"

body = match.group(1)

for variable in ("INSTALL_HAL", "INSTALL_LEMONADE", "BUILD_ZVGA"):
    assert re.search(rf'^\s*{variable}=1\s*$', body, re.MULTILINE), variable

assert "ENABLE_MEMORY=1" not in body, "Activación automática de memoria"

print("PASS: perfil AI Stack selecciona los tres módulos")
PY
