# Lemonade Minimal Linux experiment

## Goal

Create a minimal Linux target for local AI inference using AMD Lemonade Server, llama.cpp Vulkan, and the existing lightweight web prompt UI.

This branch intentionally separates two implementation tracks:

1. **Ubuntu/Lubuntu minimal track (primary):**
   - Ubuntu minimal userspace
   - LXQt or similarly lightweight desktop
   - Mesa RADV/Vulkan
   - Lemonade Server
   - llama.cpp Vulkan backend
   - lightweight local web inference UI
   - CompressOS-HAL memory experiments where compatible

2. **Buildroot track (experimental):**
   - Buildroot-generated root filesystem
   - minimal graphical stack only if required
   - Vulkan/Mesa support validated independently
   - Lemonade/runtime dependencies evaluated explicitly
   - no claim that Buildroot is based on Mint, Ubuntu, Lubuntu, or SliTaz

## Current validated host context

The development host has already validated:

- Lemonade Server 2026.46.2
- `llamacpp:vulkan` backend installed
- Qwen3-0.6B-GGUF loaded successfully
- status reports:
  - `device: gpu`
  - `recipe: llamacpp`
  - `llamacpp_backend: vulkan`
  - `status: ready`
- AMD Radeon RX 6500 XT via Vulkan
- local browser UI talking to Lemonade through the OpenAI-compatible chat completions endpoint

## Why Ubuntu/Lubuntu first

Lemonade, Mesa Vulkan, Python/runtime dependencies, packaging, driver updates, and desktop integration are much easier to keep reproducible on Ubuntu-family userspace than in a custom Buildroot image.

The primary prototype should therefore use a minimal Ubuntu/Lubuntu-style userspace with LXQt.

## Why keep Buildroot

Buildroot remains useful for measuring the smallest viable appliance-style image and for reusing the existing CompressOS-HAL external-tree experiments. It should be treated as a separate portability target rather than as a remaster of Ubuntu or Mint.

## SliTaz

SliTaz may be explored later as an additional lightweight distro target, but should not be the first Lemonade/Vulkan integration target because package/runtime compatibility would need independent validation.

## Initial milestones

1. Record runtime and package dependencies required by Lemonade + Vulkan.
2. Build a minimal Ubuntu/LXQt prototype.
3. Add the local Lemonade web UI as an optional service.
4. Verify Vulkan GPU inference after clean boot.
5. Measure idle RAM, loaded-model RAM/VRAM, startup time, and tokens/s.
6. Reuse compatible CompressOS-HAL memory and hardware probes.
7. Evaluate which dependencies can be reproduced in Buildroot.
8. Only after dependency closure, attempt a bootable Buildroot appliance image.

## Non-goals for the first iteration

- No ROCm requirement.
- No production stability claim.
- No claim of full Buildroot compatibility until a complete rootfs is built and boot-tested.
- No replacement of kernel ZRAM/Zswap with the user-space Vulkan codec.
