# Physical GPU validation record — 2026-11-12

## Scope

Record the first confirmed execution of the ZVGA Vulkan compute worker on the physical AMD Radeon RX 6500 XT. This is a hardware-execution checkpoint, not a performance benchmark or a Linux swap integration result.

## Host and Vulkan inventory

Observed on the user's Linux Mint host:

- GPU: AMD Radeon RX 6500 XT (RADV NAVI24)
- PCI vendor/device: `1002:743f`
- Vulkan device type: discrete GPU
- Vulkan driver: Mesa RADV
- Mesa version: `25.0.7-0ubuntu0.24.04.2`
- Vulkan instance version reported by `vulkaninfo`: `1.3.275`
- Vulkan API version reported for the GPU: `1.4.305`
- A second Vulkan device was present: llvmpipe (software CPU renderer).

The worker runtime log, rather than enumeration alone, is the evidence that the physical GPU was selected for the execution below.

## Build

The development dependencies were installed, including `libvulkan-dev`, `glslang-tools`, and `spirv-tools`.

Commands:

```bash
cmake -S modules/zvga -B build/zvga \
  -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build/zvga
```

Observed build stages included generation of `rle_shader.h` from `modules/zvga/shaders/rle.comp` and linking of `compresso-vulkan`.

## Automated test results

Command:

```bash
COMPRESSO_VULKAN_HELPER="$PWD/build/zvga/compresso-vulkan" \
  bash modules/zvga/scripts/test.sh
```

Result:

- 23 tests passed.
- 2 tests skipped because they require the installed CLI.
- The Vulkan equivalence test `test_gpu_output_equals_cpu` passed.
- The native input-bound test passed.
- The suite completed with `OK (skipped=2)`.

## Direct physical execution

Command:

```bash
set -o pipefail
head -c 4096 /dev/zero | \
  build/zvga/compresso-vulkan \
  > /tmp/compresso-gpu-output.bin \
  2> /tmp/compresso-gpu-log.txt
RESULT=$?
cat /tmp/compresso-gpu-log.txt
echo "$RESULT"
stat -c '%s bytes' /tmp/compresso-gpu-output.bin
```

Observed output:

```text
device: AMD Radeon RX 6500 XT (RADV NAVI24)
exit code: 0
16388 bytes
```

This confirms that the native worker selected the RX 6500 XT and completed the tested compute request. The output size is recorded as an observation only; this particular run is not a compression-ratio benchmark.

## What is confirmed

- Vulkan loader and RADV driver expose the RX 6500 XT.
- The ZVGA native worker compiles and links.
- The worker reports the RX 6500 XT at runtime.
- The direct worker invocation exits successfully.
- The module's current automated tests pass, including GPU/CPU output equivalence.

## What is not yet confirmed

- GPU throughput or latency advantage over CPU.
- Compression ratio or energy efficiency under representative workloads.
- Sustained load, thermal behavior, or concurrent GPU contention.
- GPU participation in Linux kernel swap.
- ZRAM/Zswap codec integration, kernel page migration, P2P DMA, or VRAM-backed swap.
- End-to-end stability across reboots or other GPUs/distributions.

## Next validation sequence

1. Add repeatable CPU-versus-GPU benchmarks with identical datasets and warm-up policy.
2. Measure latency, throughput, output size, and correctness across compressible and incompressible inputs.
3. Record GPU utilization, clocks, temperature, and memory use without changing system memory configuration.
4. Validate the separately installed ZVGA CLI/daemon after local build and benchmark gates pass.
5. Design any ZRAM/Zswap or kernel integration as a separate, reviewed milestone with explicit rollback and safety tests.
