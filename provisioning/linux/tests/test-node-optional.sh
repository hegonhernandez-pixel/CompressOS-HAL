#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
INSTALLER="$ROOT/provisioning/linux/install-node.sh"
BOOTSTRAP="$ROOT/provisioning/linux/remote-bootstrap.sh"
TEMP="$(mktemp -d)"
trap 'rm -rf "$TEMP"' EXIT
mkdir -p "$TEMP/bin"

cat >"$TEMP/bin/node" <<'EOF'
#!/usr/bin/env bash
echo v24.11.0
EOF
cat >"$TEMP/bin/npm" <<'EOF'
#!/usr/bin/env bash
echo 11.6.0
EOF
chmod +x "$TEMP/bin/node" "$TEMP/bin/npm"

PATH="$TEMP/bin:$PATH" bash "$INSTALLER" 24 >"$TEMP/accepted.log"
grep -Fq 'skipping install' "$TEMP/accepted.log"

if PATH="$TEMP/bin:$PATH" bash "$INSTALLER" 26 >"$TEMP/rejected.log" 2>&1; then
  echo 'FAIL: wrong installed Node.js major was accepted' >&2
  exit 1
fi

if PATH="$TEMP/bin:$PATH" bash "$INSTALLER" 20 >"$TEMP/unsupported.log" 2>&1; then
  echo 'FAIL: unsupported Node.js major was accepted' >&2
  exit 1
fi

grep -Fq -- '--install-node' "$BOOTSTRAP"
grep -Fq 'INSTALL_NODE=0' "$BOOTSTRAP"
grep -Fq 'if [[ "$INSTALL_NODE" -eq 1 ]]' "$BOOTSTRAP"
echo 'PASS: Node.js is optional and rejects unsupported/mismatched majors'
