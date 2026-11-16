#!/usr/bin/env bash
set -euo pipefail

# This script is invoked only after the operator selects --install-node and --apply.
# Keep the chosen major on a maintained LTS line; do not curl | bash.
NODE_MAJOR="${1:-24}"

case "$NODE_MAJOR" in
  22|24|26) ;;
  *) echo "[CompressOS Node] ERROR: Unsupported Node.js major: $NODE_MAJOR (use 22, 24 or 26)" >&2; exit 1 ;;
esac

if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
  current_major="$(node --version | sed -nE 's/^v([0-9]+)\..*/\1/p')"
  if [[ "$current_major" == "$NODE_MAJOR" ]]; then
    echo "[CompressOS Node] Node.js $(node --version) and npm $(npm --version) already available; skipping install"
    exit 0
  fi
  echo "[CompressOS Node] Existing Node.js $(node --version) detected. Refusing automatic replacement; upgrade manually after reviewing compatibility." >&2
  exit 1
fi

echo "[CompressOS Node] Node.js/npm missing. No automatic third-party repository or remote script will be added." >&2
echo "[CompressOS Node] Install supported Node.js $NODE_MAJOR LTS from https://nodejs.org/en/download and re-run this check." >&2
exit 1
