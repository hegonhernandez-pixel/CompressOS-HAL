#!/usr/bin/env bash
set -euo pipefail

REPO="$(pwd)"
TMP="$(mktemp -d)"
mkdir -p "$TMP/provisioning/linux" "$TMP/modules/memory/scripts" \
  "$TMP/modules/zvga/scripts" "$TMP/tools"

cp provisioning/linux/remote-bootstrap.sh \
  "$TMP/provisioning/linux/remote-bootstrap.sh"

cp provisioning/linux/install-lemonade.sh \
  "$TMP/provisioning/linux/install-lemonade.sh"

touch "$TMP/modules/memory/scripts/install-mint.sh"
touch "$TMP/modules/zvga/CMakeLists.txt"
touch "$TMP/modules/zvga/scripts/test.sh"

python3 - "$TMP/provisioning/linux/remote-bootstrap.sh" <<'PY'
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text()

s = s.replace(
    'bash "$REPO_DIR/modules/zvga/scripts/test.sh"',
    'printf "MOCK zVGA test\\n"'
)

p.write_text(s)
PY

bash -n "$TMP/provisioning/linux/remote-bootstrap.sh"

printf 'Simulación preparada en: %s\n' "$TMP"
printf 'Repositorio original sin modificaciones de ejecución.\n'
