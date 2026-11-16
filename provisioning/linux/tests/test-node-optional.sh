#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
INSTALLER="$ROOT/provisioning/linux/install-node.sh"
BOOTSTRAP="$ROOT/provisioning/linux/remote-bootstrap.sh"

TEMP="$(mktemp -d)"
trap 'rm -rf "$TEMP"' EXIT
mkdir -p "$TEMP/bin" "$TEMP/existing"

# Si el instalador intenta usar Internet, la prueba falla.
cat >"$TEMP/bin/curl" <<'EOF'
#!/usr/bin/env bash
echo "FAIL: acceso a Internet durante la prueba" >&2
exit 99
EOF
chmod +x "$TEMP/bin/curl"

# Una instalación existente debe bloquearse sin descargar nada.
if COMPRESSO_NODE_DIR="$TEMP/existing" \
   PATH="$TEMP/bin:$PATH" \
   bash "$INSTALLER" 24 >"$TEMP/existing.log" 2>&1; then
  echo "FAIL: sobrescribió una instalación existente" >&2
  exit 1
fi

grep -Fq 'destino existente' "$TEMP/existing.log"

# Una versión no admitida debe rechazarse sin descargar.
if COMPRESSO_NODE_DIR="$TEMP/new" \
   PATH="$TEMP/bin:$PATH" \
   bash "$INSTALLER" 20 >"$TEMP/unsupported.log" 2>&1; then
  echo "FAIL: aceptó una versión no admitida" >&2
  exit 1
fi

grep -Fq 'versión no admitida' "$TEMP/unsupported.log"

# El bootstrap debe mantener Node.js como opción explícita.
grep -Fq -- '--install-node' "$BOOTSTRAP"
grep -Fq 'INSTALL_NODE=0' "$BOOTSTRAP"
grep -Fq 'if [[ "$INSTALL_NODE" -eq 1 ]]' "$BOOTSTRAP"


# Pruebas funcionales sin Internet.
mkdir -p "$TEMP/mockbin"

cat >"$TEMP/mockbin/curl" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail

for arg in "$@"; do
  case "$arg" in
    */index.json)
      printf '%s\n' '[{"version":"v24.1.0","lts":"Mock","files":["linux-x64"]}]'
      exit 0
      ;;
  esac
done

while (($#)); do
  if [[ "$1" == "-o" ]]; then
    shift
    OUTPUT="$1"
  fi
  shift
done

if [[ "$OUTPUT" == */SHASUMS256.txt ]]; then
  printf '%s\n' '0000000000000000000000000000000000000000000000000000000000000000  node-v24.1.0-linux-x64.tar.xz' >"$OUTPUT"
else
  printf 'mock archive\n' >"$OUTPUT"
fi
MOCK

cat >"$TEMP/mockbin/sha256sum" <<'MOCK'
#!/usr/bin/env bash
exit 0
MOCK

cat >"$TEMP/mockbin/tar" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail

if [[ "${MOCK_TAR_FAIL:-0}" == 1 ]]; then
  exit 1
fi

while (($#)); do
  if [[ "$1" == "-C" ]]; then
    shift
    DEST="$1"
  fi
  shift
done

mkdir -p "$DEST/bin"

printf '#!/bin/sh\necho v24.1.0\n' >"$DEST/bin/node"
printf '#!/bin/sh\necho 11.0.0\n' >"$DEST/bin/npm"

chmod +x "$DEST/bin/node" "$DEST/bin/npm"
MOCK

chmod +x "$TEMP/mockbin/"*

# El índice JSON simulado solo ofrece x64.
# Ejecutar las pruebas funcionales en esa arquitectura.
if [[ "$(uname -m)" == "x86_64" ]]; then
  if ! COMPRESSO_NODE_DIR="$TEMP/success" \
      PATH="$TEMP/mockbin:$PATH" \
      bash "$INSTALLER" 24 >"$TEMP/success.log" 2>&1; then
    cat "$TEMP/success.log" >&2
    exit 1
  fi

  test -x "$TEMP/success/bin/node"
  test -x "$TEMP/success/bin/npm"

  if COMPRESSO_NODE_DIR="$TEMP/failure" \
      MOCK_TAR_FAIL=1 \
      PATH="$TEMP/mockbin:$PATH" \
      bash "$INSTALLER" 24 >"$TEMP/failure.log" 2>&1; then
    echo "FAIL: extracción fallida aceptada" >&2
    exit 1
  fi

  test ! -e "$TEMP/failure"

  echo "PASS: instalación simulada y recuperación ante fallos"
fi


echo "PASS: Node.js opcional, destino protegido y sin descargas"
