#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTERNAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION="$(tr -d '[:space:]' < "$EXTERNAL_DIR/BUILDROOT_VERSION")"
BUILDROOT_DIR="${BUILDROOT_DIR:-$EXTERNAL_DIR/.cache/buildroot-$VERSION}"
OUTPUT_DIR="${OUTPUT_DIR:-$EXTERNAL_DIR/output-$VERSION}"
JOBS="${JOBS:-$(nproc)}"
"$SCRIPT_DIR/check-buildroot-host.sh"
if [[ ! -d "$BUILDROOT_DIR/.git" ]]; then
  mkdir -p "$(dirname "$BUILDROOT_DIR")"
  git clone --depth 1 --branch "$VERSION" https://gitlab.com/buildroot.org/buildroot.git "$BUILDROOT_DIR"
fi
actual_version="$(git -C "$BUILDROOT_DIR" describe --tags --exact-match 2>/dev/null || true)"
if [[ "$actual_version" != "$VERSION" ]]; then
  echo "ERROR: expected Buildroot $VERSION, found '${actual_version:-untagged tree}'." >&2
  echo "Set BUILDROOT_DIR to a clean checkout of tag $VERSION." >&2
  exit 1
fi
mkdir -p "$OUTPUT_DIR"
make -C "$BUILDROOT_DIR" O="$OUTPUT_DIR" BR2_EXTERNAL="$EXTERNAL_DIR" compresso_x86_64_defconfig
make -C "$BUILDROOT_DIR" O="$OUTPUT_DIR" BR2_EXTERNAL="$EXTERNAL_DIR" -j"$JOBS"
echo
echo "Buildroot EXP rootfs build finished."
echo "EXT4: $OUTPUT_DIR/images/rootfs.ext4"
echo "TAR:  $OUTPUT_DIR/images/rootfs.tar"
echo "This is a rootfs-only prototype; no kernel, bootloader or bootable ISO was produced."
