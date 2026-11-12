# Buildroot external tree — EXP rootfs prototype

Pinned Buildroot baseline: **2025.02.19 LTS**. The official Buildroot download page lists this as the maintained LTS series (support through March 2028). The exact tag is recorded in `BUILDROOT_VERSION`.

## Build scope

- Produces an x86_64 Buildroot root filesystem (EXT4 + TAR), not a Linux Mint ISO.
- Includes systemd, Python 3, SQLite, the memory daemon, CAS/audit tools and optional C++17/Vulkan zVGA worker.
- The Buildroot target is a separate experimental rootfs. A matching kernel, GPU DRM driver/firmware and bootloader are not included in this first rootfs-only profile.
- The optional Vulkan worker compiles the existing shader. The Mint build host must provide `glslangValidator`; Buildroot builds host `spirv-val` through its `host-spirv-tools` package.
- The memory configurator and CAS auditor services are enabled in the generated Buildroot image only. This does not change the Linux Mint host.

## Build from Linux Mint

Install the host dependencies listed by `scripts/check-buildroot-host.sh`, then run:

```bash
bash modules/memory/buildroot-external/scripts/build-buildroot.sh
```

The script clones the exact Buildroot tag into `.cache/`, configures an out-of-tree build under `output/`, and builds the rootfs. It does not install anything into the running Mint system.

## Validation status

The external packages and defconfig are experimental. The full Buildroot build, resulting rootfs boot, kernel/DRM integration, physical GPU execution and Mint live-image workflow are not yet validated. Do not call this a bootable ISO.
