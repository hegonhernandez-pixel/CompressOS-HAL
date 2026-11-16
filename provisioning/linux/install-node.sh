#!/usr/bin/env bash
set -euo pipefail

NODE_MAJOR="${1:-24}"
INSTALL_DIR="${COMPRESSO_NODE_DIR:-$HOME/.local/share/compresso/node}"
BASE_URL="https://nodejs.org/dist"

case "$NODE_MAJOR" in
  22|24|26) ;;
  *) echo "ERROR: versión no admitida: $NODE_MAJOR" >&2; exit 1 ;;
esac

if [[ -e "$INSTALL_DIR" || -L "$INSTALL_DIR" ]]; then
  echo "ERROR: destino existente: $INSTALL_DIR" >&2
  exit 1
fi

for cmd in curl python3 tar sha256sum; do
  command -v "$cmd" >/dev/null ||
    { echo "ERROR: falta $cmd" >&2; exit 1; }
done

ARCH="$(uname -m)"
case "$ARCH" in
  x86_64) ARCH="x64" ;;
  aarch64) ARCH="arm64" ;;
  *) echo "ERROR: arquitectura no compatible" >&2; exit 1 ;;
esac

# Obtener la versión más reciente de la rama solicitada.
VERSION="$(
  curl -fsSL --retry 2 "$BASE_URL/index.json" |
  python3 -c '
import json,sys
major=int(sys.argv[1])
arch=sys.argv[2]
releases=json.load(sys.stdin)
matches=[
    r["version"] for r in releases
    if r["version"].startswith(f"v{major}.")
    and r.get("lts")
    and f"linux-{arch}" in r.get("files", [])
]
if not matches:
    sys.exit("No se encontró una versión LTS compatible")
print(matches[0])
' "$NODE_MAJOR" "$ARCH"
)"

FILE="node-${VERSION}-linux-${ARCH}.tar.xz"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Descargando Node.js $VERSION..."
curl -fL --retry 2 -o "$TMP/$FILE" \
  "$BASE_URL/$VERSION/$FILE"

curl -fL --retry 2 -o "$TMP/SHASUMS256.txt" \
  "$BASE_URL/$VERSION/SHASUMS256.txt"

echo "Verificando SHA-256..."
(
  cd "$TMP"
  grep -F "  $FILE" SHASUMS256.txt |
    sha256sum -c -
)

# Extraer en un directorio temporal y publicar al finalizar.
if [[ -e "$INSTALL_DIR" || -L "$INSTALL_DIR" ]]; then
  echo "ERROR: destino existente: $INSTALL_DIR" >&2
  exit 1
fi

mkdir -p "$(dirname "$INSTALL_DIR")"
STAGING="$(mktemp -d "$(dirname "$INSTALL_DIR")/.node-staging.XXXXXXXX")"
trap 'rm -rf "$TMP" "$STAGING"' EXIT

tar -xJf "$TMP/$FILE" -C "$STAGING" --strip-components=1

test -x "$STAGING/bin/node"
test -x "$STAGING/bin/npm"

if [[ -e "$INSTALL_DIR" || -L "$INSTALL_DIR" ]]; then
  echo "ERROR: destino ocupado durante la instalación" >&2
  exit 1
fi

mv -T --no-clobber "$STAGING" "$INSTALL_DIR"

echo "Node.js instalado en $INSTALL_DIR"
"$INSTALL_DIR/bin/node" --version
PATH="$INSTALL_DIR/bin:$PATH" "$INSTALL_DIR/bin/npm" --version

echo "Para utilizarlo temporalmente:"
echo "export PATH=\"$INSTALL_DIR/bin:\$PATH\""
