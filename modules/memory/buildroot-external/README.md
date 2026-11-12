# Buildroot external tree — experimental scaffold

This external tree packages the existing memory daemon, CAS/audit tools and the existing zVGA C++/Vulkan worker.

## Status and boundaries

- Buildroot produces a separate target root filesystem. It does **not** produce a Linux Mint ISO.
- The external tree is not yet a validated complete defconfig or bootable ISO.
- Pin a Buildroot release before relying on package names, Kconfig symbols or paths.
- `compresso-cas` uses Python 3 and SQLite for a user-space CAS index, SHA-256 audit and route planner.
- `compresso-zvga` packages the existing C++17/Vulkan worker and requires Vulkan headers/loader, glslang, SPIR-V Tools and host-side shader validators.
- The Vulkan package is optional and disabled unless its dependencies are selected. It still needs a real Buildroot build and target-hardware validation.

The Mint host can build this external tree after Buildroot is downloaded separately. Mint's own live-image workflow remains a distinct project.
