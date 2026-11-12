# CompressOS-HAL

**Hardware Abstraction Layer for GPU-Assisted Linux Optimization**

CompressOS-HAL is an experimental, modular Linux systems project exploring resource indexing, lossless data processing, CPU/GPU workload dispatch, and integration with existing Linux memory mechanisms.

> **Status: Experimental / Research and Development.** Features are validated incrementally. No production readiness, universal hardware support, kernel swap acceleration, or performance improvement is implied.

## Project goals

- Build a hardware-aware abstraction layer for CPU, GPU, memory, and storage resources.
- Identify and index reusable resources with bounded, auditable operations.
- Explore lossless compression and compute-shader processing through CPU and Vulkan backends.
- Integrate carefully with Linux ZRAM and Zswap without conflating user-space buffers with kernel-managed memory pages.
- Preserve reproducible tests, hardware evidence, and explicit implementation limits.

## Architecture and modules

| Module | Responsibility | Current status |
|---|---|---|
| `modules/memory` | Memory profiles, metrics, read-only health checks, hardware inventory, CAS resource registry, audit and policy experiments | Experimental; Linux Mint integration work in progress |
| `modules/zvga` | Bounded user-space codec, CPU backend, Vulkan compute worker, local daemon and CLI | Build and test suite pass; physical RX 6500 XT shader execution confirmed |
| Buildroot integration | Package and external-tree experiments | Experimental; full image/boot validation pending |

See each module's README for commands, requirements, safety limits, and test coverage.

## Verified hardware checkpoint — 2026-11-12

A physical Linux host with an **AMD Radeon RX 6500 XT (Navi 24)** was enumerated by Vulkan through Mesa RADV. The native ZVGA Vulkan worker was built and executed a compute request. Its runtime log identified:

```text
device: AMD Radeon RX 6500 XT (RADV NAVI24)
exit code: 0
```

The ZVGA test suite completed **23 tests successfully; 2 tests were skipped** because they require the installed CLI. The Vulkan equivalence test passed, comparing GPU output with the CPU reference.

This confirms execution by the named physical GPU for the recorded test. It does **not** establish a speedup, favorable compression ratio, sustained throughput, GPU-backed swap, kernel page migration, or ZRAM/Zswap integration. Performance benchmarking and end-to-end memory integration remain separate milestones. Full details and reproducible commands are in [the hardware validation record](docs/HARDWARE-VALIDATION-2026-11-12.md).

## Quick start: build and test ZVGA on Linux Mint / Ubuntu

Install build dependencies:

```bash
sudo apt-get update
sudo apt-get install -y cmake ninja-build g++ python3 \
  libvulkan-dev mesa-vulkan-drivers glslang-tools spirv-tools
```

Configure and build:

```bash
cmake -S modules/zvga -B build/zvga -G Ninja \
  -DCMAKE_BUILD_TYPE=Release
cmake --build build/zvga
```

Run the module tests against the locally built Vulkan helper:

```bash
COMPRESSO_VULKAN_HELPER="$PWD/build/zvga/compresso-vulkan" \
  bash modules/zvga/scripts/test.sh
```

To directly confirm which physical device executes the shader:

```bash
set -o pipefail
head -c 4096 /dev/zero | \
  build/zvga/compresso-vulkan \
  > /tmp/compresso-gpu-output.bin \
  2> /tmp/compresso-gpu-log.txt
status=$?
cat /tmp/compresso-gpu-log.txt
echo "exit=$status"
stat -c '%s bytes' /tmp/compresso-gpu-output.bin
```

A valid hardware checkpoint must show the intended GPU model in the worker log and exit code `0`. Vulkan enumeration alone is not proof that the shader ran on that device. Systems exposing multiple Vulkan devices may also expose a software renderer such as llvmpipe; always inspect the worker's runtime device line.

## Safety and integration boundaries

- Hardware inventory and health diagnostics are read-only unless a command explicitly documents otherwise.
- Do not enable memory daemons, change active swap, modify kernel parameters, or alter ZRAM/Zswap configuration as part of a shader build/test.
- ZVGA currently processes bounded user-space input buffers. It does not automatically read process memory or kernel swap pages.
- Vulkan compute execution is not equivalent to a kernel swap backend. GPU-backed swap, page migration, P2P DMA, and kernel codec adapters are not validated.
- The CPU reference is retained for correctness checks and fallback. A successful test is not a performance claim.

## Development branches

- `main` is the canonical integration branch for CompressOS-HAL.
- `exp/*` branches are experimental work areas; preserve their history and integrate completed changes into `main` through reviewable merges.
- `recovery/*` branches are retained as recovery/reference history, not as alternate canonical branches.
- Automated review branches are retained for traceability; do not treat them as independent releases.

The current branch inventory and synchronization notes are maintained in [BRANCH-STATUS.md](docs/BRANCH-STATUS.md).

## Related project

Fedora-specific distribution work remains in the separate [Fedora-compresSO repository](https://github.com/hegonhernandez-pixel/Fedora-compresSO). CompressOS-HAL `main` is the canonical core for this repository.

## Licensing

Licensing and commercial distribution terms are under evaluation. No license is granted to proprietary components unless explicitly stated. Review [LICENSE-STATUS.md](LICENSE-STATUS.md) before reusing project materials.

## Project philosophy

**Research first. Validate before claiming. Document failures. Preserve reproducibility. Build modularly.**
