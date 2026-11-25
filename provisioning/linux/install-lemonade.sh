#!/usr/bin/env bash
set -euo pipefail

REPORT_DIR="${1:?Uso: install-lemonade.sh REPORT_DIR}"
mkdir -p "$REPORT_DIR"

log() { printf "[CompressOS Lemonade] %s\n" "$*"; }

install_lemonade() {
  log "Installing Lemonade Server from the official stable PPA"
  sudo apt-get install -y software-properties-common
  sudo add-apt-repository -y ppa:lemonade-team/stable
  sudo apt-get update
  sudo apt-get install -y lemonade-server
  lemonade status --json > "$REPORT_DIR/lemonade-status.json" 2>"$REPORT_DIR/lemonade-status.err" || true

  # Install only backends that the local Lemonade catalog advertises.
  local catalog
  catalog="$(lemonade backends --all 2>/dev/null || true)"
  printf '%s\n' "$catalog" > "$REPORT_DIR/lemonade-backends.txt"
  for backend in llamacpp:vulkan whispercpp:vulkan sd-cpp:vulkan moonshine:cpu onnxruntime:cpu; do
    if grep -Fq "$backend" <<<"$catalog"; then
      log "Installing Lemonade backend: $backend"
      lemonade backends install "$backend" || log "Backend failed and was left for review: $backend"
    else
      log "Backend not advertised on this host; skipping: $backend"
    fi
  done
}

install_lemonade
