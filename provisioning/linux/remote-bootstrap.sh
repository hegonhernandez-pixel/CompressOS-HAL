#!/usr/bin/env bash
set -euo pipefail

APPLY=0
INSTALL_HAL=0
ENABLE_MEMORY=0
BUILD_ZVGA=0
INSTALL_LEMONADE=0
INSTALL_NODE=0
NODE_MAJOR="24"
PROFILE="creator"
REPO_DIR=""
REPORT_DIR="${HOME}/compresso-provisioning-report"

usage() {
  cat <<'EOF'
CompressOS authorized remote bootstrap (Linux Mint / Ubuntu)

Default behavior is CHECK-ONLY and makes no system changes.

Usage:
  remote-bootstrap.sh [options]

Options:
  --repo-dir PATH       Path to an already transferred CompressOS-HAL checkout/bundle
  --profile NAME        creator|business|personal (default: creator)
  --report-dir PATH     Where to store reports
  --apply               Allow installation changes
  --install-ai-stack   Install Lemonade + HAL + zVGA
  --install-node       Check Node.js/npm LTS; never install without explicit preparation (requires --apply)
  --node-major MAJOR   Node.js major for the optional check: 22|24|26 (default: 24)
  --install-hal        Install HAL memory module
  --install-lemonade    Install Lemonade from the official stable PPA (requires --apply)
  --build-zvga          Install build deps, build shader/worker and run bounded tests (requires --apply)
  --enable-memory       Install and explicitly enable compresso-memoryd after dry-run (requires --apply)
  -h, --help            Show this help

Examples:
  ./remote-bootstrap.sh --repo-dir ~/CompressOS-HAL
  ./remote-bootstrap.sh --repo-dir ~/CompressOS-HAL --apply --install-lemonade --build-zvga
  ./remote-bootstrap.sh --repo-dir ~/CompressOS-HAL --apply --enable-memory
EOF
}

log() { printf '[CompressOS] %s\n' "$*"; }
die() { printf '[CompressOS] ERROR: %s\n' "$*" >&2; exit 1; }

while (($#)); do
  case "$1" in
    --repo-dir) REPO_DIR="${2:-}"; shift 2 ;;
    --profile) PROFILE="${2:-}"; shift 2 ;;
    --report-dir) REPORT_DIR="${2:-}"; shift 2 ;;
    --apply) APPLY=1; shift ;;
    --install-ai-stack)
      INSTALL_HAL=1
      INSTALL_LEMONADE=1
      BUILD_ZVGA=1
      shift ;;
  --install-hal) INSTALL_HAL=1; shift ;;
    --install-lemonade) INSTALL_LEMONADE=1; shift ;;
    --install-node) INSTALL_NODE=1; shift ;;
    --node-major) NODE_MAJOR="${2:-}"; shift 2 ;;
    --build-zvga) BUILD_ZVGA=1; shift ;;
    --enable-memory) ENABLE_MEMORY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown argument: $1" ;;
  esac
done

case "$PROFILE" in
  creator|business|personal) ;;
  *) die "Unsupported profile: $PROFILE" ;;
esac

[[ -n "$REPO_DIR" ]] || die "--repo-dir is required"
REPO_DIR="$(cd "$REPO_DIR" 2>/dev/null && pwd)" || die "Repository directory not found"
[[ -f "$REPO_DIR/modules/memory/scripts/install-mint.sh" ]] || die "CompressOS-HAL memory installer not found"
[[ -f "$REPO_DIR/modules/zvga/CMakeLists.txt" ]] || die "zVGA sources not found"

[[ -r /etc/os-release ]] || die "/etc/os-release missing"
# shellcheck disable=SC1091
. /etc/os-release
if [[ "${ID:-}" != "linuxmint" && "${ID_LIKE:-}" != *ubuntu* && "${ID:-}" != "ubuntu" ]]; then
  die "Supported MVP target is Linux Mint/Ubuntu family; detected ${PRETTY_NAME:-unknown}"
fi

mkdir -p "$REPORT_DIR"
log "Mode: $([[ "$APPLY" -eq 1 ]] && echo APPLY || echo CHECK-ONLY)"
log "Profile: $PROFILE"
log "OS: ${PRETTY_NAME:-unknown}"


run_scan() {
  local scanner="$REPO_DIR/tools/compresso-capability-scan/compresso_capability_scan.py"
  if [[ -f "$scanner" ]]; then
    python3 "$scanner"       --json "$REPORT_DIR/compresso-scan.json"       --report "$REPORT_DIR/compresso-scan.md"
  else
    log "Capability scanner not present in this checkout; skipping"
  fi
}

log "Running pre-install capability scan"
run_scan || true

if [[ "$APPLY" -ne 1 ]]; then
  log "Check complete. No system changes were made."
  log "Use --apply plus explicit feature flags only after reviewing the report."
  exit 0
fi

if [[ "$ENABLE_MEMORY" -eq 1 && "$INSTALL_HAL" -ne 1 ]]; then
  die "--enable-memory requires --install-hal"
fi

if [[ "$INSTALL_HAL" -eq 0 && "$INSTALL_LEMONADE" -eq 0 && "$BUILD_ZVGA" -eq 0 && "$INSTALL_NODE" -eq 0 ]]; then
  log "No modules selected. Nothing to install."
  exit 0
fi

command -v sudo >/dev/null || die "sudo is required for provisioning"
if ! sudo -n true 2>/dev/null; then
  log "sudo requires interactive authorization. Remote operator must obtain client authorization before APPLY operations."
fi


sudo -v

install_base_deps() {
  log "Installing common dependencies"
  sudo apt-get update
  sudo apt-get install -y ca-certificates curl git python3
}

install_zvga_deps() {
  log "Installing zVGA build dependencies"
  sudo apt-get install -y cmake ninja-build g++ libvulkan-dev \
    mesa-vulkan-drivers vulkan-tools glslang-tools spirv-tools
}

install_memory() {
  log "Installing CompressOS memory package without activating services"
  sudo "$REPO_DIR/modules/memory/scripts/install-mint.sh"
  log "Running memory daemon dry-run"
  sudo python3 /usr/libexec/compresso/memoryd.py --dry-run | tee "$REPORT_DIR/memory-dry-run.txt"

  if [[ "$ENABLE_MEMORY" -eq 1 ]]; then
    log "Explicit memory activation requested"
    sudo systemctl enable --now compresso-memoryd.service
    sudo compressoctl doctor | tee "$REPORT_DIR/compresso-doctor.txt" || true
    swapon --show > "$REPORT_DIR/swapon.txt" || true
  else
    log "Memory services remain inactive; use --enable-memory only after config/conflict review"
  fi
}

build_zvga() {
  log "Building zVGA Vulkan worker and shader"
  cmake -S "$REPO_DIR/modules/zvga" -B "$REPO_DIR/build/zvga"     -G Ninja -DCMAKE_BUILD_TYPE=Release
  cmake --build "$REPO_DIR/build/zvga"
  COMPRESSO_VULKAN_HELPER="$REPO_DIR/build/zvga/compresso-vulkan"     bash "$REPO_DIR/modules/zvga/scripts/test.sh" | tee "$REPORT_DIR/zvga-test.txt"
}

if [[ "$INSTALL_HAL" -eq 1 || "$INSTALL_LEMONADE" -eq 1 || "$BUILD_ZVGA" -eq 1 ]]; then
  install_base_deps
fi

if [[ "$INSTALL_NODE" -eq 1 ]]; then
  bash "$REPO_DIR/provisioning/linux/install-node.sh" "$NODE_MAJOR"
fi

if [[ "$INSTALL_HAL" -eq 1 ]]; then
  install_memory
fi

if [[ "$INSTALL_LEMONADE" -eq 1 ]]; then
  bash "$REPO_DIR/provisioning/linux/install-lemonade.sh" "$REPORT_DIR"
fi

if [[ "$BUILD_ZVGA" -eq 1 ]]; then
  install_zvga_deps
  build_zvga
fi

log "Running post-install capability scan"
run_scan || true

{
  printf 'profile=%s\n' "$PROFILE"
  printf 'os=%s\n' "${PRETTY_NAME:-unknown}"
  printf 'lemonade_requested=%s\n' "$INSTALL_LEMONADE"
  printf 'node_requested=%s\n' "$INSTALL_NODE"
  printf 'zvga_requested=%s\n' "$BUILD_ZVGA"
  printf 'memory_enabled=%s\n' "$ENABLE_MEMORY"
  printf 'completed_at=%s\n' "$(date --iso-8601=seconds)"
} > "$REPORT_DIR/provisioning-manifest.txt"

log "Provisioning complete. Reports: $REPORT_DIR"
