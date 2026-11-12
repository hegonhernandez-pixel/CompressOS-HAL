#!/usr/bin/env bash
set -euo pipefail
required=(git make gcc g++ patch cpio rsync bc perl python3 file wget tar xz gzip bzip2 unzip flex bison glslangValidator)
missing=()
for command_name in "${required[@]}"; do
  command -v "$command_name" >/dev/null 2>&1 || missing+=("$command_name")
done
if [[ "$(uname -m)" != "x86_64" ]]; then
  echo "ERROR: this EXP defconfig currently targets x86_64." >&2
  exit 1
fi
if (("${#missing[@]}" > 0)); then
  printf 'Missing host tools: %s\n' "${missing[*]}" >&2
  echo "On Linux Mint/Ubuntu install them with:" >&2
  echo "sudo apt-get update && sudo apt-get install -y build-essential git bc bison flex cpio file rsync unzip wget xz-utils glslang-tools" >&2
  exit 1
fi
free_kb="$(df -Pk "$(pwd)" | awk 'NR==2 {print $4}')"
if (( free_kb < 15000000 )); then
  echo "WARNING: less than 15 GB free; Buildroot may run out of disk space." >&2
fi
echo "Buildroot host prerequisites: OK"
printf 'Architecture: %s\n' "$(uname -m)"
printf 'Parallel jobs: %s\n' "$(nproc)"
