# CompressOS-HAL repository structure

## Core project

This repository is the canonical project and integration point for the hardware-abstraction and Linux optimization architecture.

## Platform adaptations

Platform-specific distributions and experiments live in separate repositories. `Fedora-compresSO` is maintained as a related Fedora development line; its `main` and `exp/fast-zram-zswap-daemons` branches are preserved there and are not the canonical core branches.

## Memory subsystem

The experimental memory-management package is integrated under [`modules/memory`](../modules/memory/README.md). It contains the ZRAM/Zswap daemon, read-only metrics, supervisor, bounded benchmark, systemd units, tests, and Linux Mint installation scripts. Its current installer targets an existing Linux Mint XFCE installation; it does not build a custom ISO. Real Mint 22.3 validation remains pending.

## Engineering policy

Keep hardware-specific and distribution-specific code behind modules/adapters. Treat proposed GPU/Vulkan acceleration as research until implemented and measured. Do not claim performance gains or platform compatibility without reproducible tests.
