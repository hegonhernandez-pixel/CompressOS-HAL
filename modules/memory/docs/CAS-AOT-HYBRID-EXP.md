# CAS / AOT indexer / hybrid policy — EXP foundation

Status: experimental user-space foundation. This is not kernel page swapping, a Vulkan VRAM allocator, a modified ELF loader, or a completed Buildroot image.

## Components added

- `compresso_cas.registry.CasRegistry`: immutable content-addressed snapshots, SHA-256 identities, deterministic UUIDv5 identifiers, SQLite alias map, and integrity audit.
- `compresso_cas.indexer.index_tree`: non-mutating ELF file indexer. It snapshots ELF files into CAS; it does not rewrite ELF headers, PLT/GOT, DT_NEEDED, syscalls, or opcodes.
- `compresso_cas.policy.choose_route`: deterministic policy planner for critical/normal/background I/O, read/write direction, GPU availability, game mode and VRAM watermarks.
- `compresso-cas`: CLI for indexing, auditing and printing route decisions.
- Four rulesets under `modules/memory/config`.
- Buildroot external package `compresso-cas`, extending the existing external tree.

## CAS data model

`blocks(sha256 PRIMARY KEY, uuid UNIQUE, size_bytes, relative_path, state)`

`aliases(original_path PRIMARY KEY, sha256 REFERENCES blocks)`

Blob URI is `cas://sha256/<digest>`. UUIDv5 is derived from the SHA-256 digest. The content hash remains the integrity authority; UUID is a stable alias, not a second integrity algorithm. Corrupt blobs are moved to `quarantine/`, marked `corrupt`, and must not be served. Missing blobs are marked `missing`. Both states indicate CPU fallback in the audit report.

## I/O policy

- Critical READ, block >= 4 MiB, GPU available, no game mode, VRAM usage <= 60%: recommend `fast_vram`.
- VRAM usage >= 85%, game mode, or GPU unavailable: recommend `zswap` / CPU fallback.
- Between 60% and 85%: hysteresis band; do not allocate fast VRAM.
- Normal I/O: recommend `zswap`.
- Background WRITE: recommend `nvme_background`.

The policy is a planner only. It does not transfer kernel pages, write sysfs, alter Zswap limits, or reserve VRAM. A future adapter must expose a real, capability-checked backend and be separately tested.

## Buildroot integration

The existing external tree is `modules/memory/buildroot-external`; this change adds a Python/SQLite package. It does not claim to be a complete defconfig or a Mint ISO builder. Buildroot creates a separate target root filesystem. Mint remains the development host. The Buildroot release and Kconfig symbols must be pinned and validated against the chosen upstream release before claiming a reproducible full image build.

The existing zVGA CMake/Vulkan worker remains a separate module. Its Buildroot package is deliberately not enabled by this change because the project has not yet pinned a Buildroot release and verified the Vulkan package symbols/toolchain combination. C++17, CMake, Vulkan headers/loader, glslang and spirv-tools are required for that next packaging step.

## Not implemented / explicitly deferred

- Actual AOT opcode translation and instruction-level deduplication.
- Binary rewriting, syscall hooks, PLT/GOT/DT_NEEDED patching, and glibc/ld.so replacement.
- A kernel CAS page-cache or swap backend.
- `ZONE_VRAM_ZRAM`, P2P DMA, DirectStorage, arbitrary `vkMapMemory` access to process memory.
- Automatic writes to `/sys/module/zswap`, GPU sysfs, or active swap devices.
- Vulkan execution in initramfs and rootfs decompression into VRAM.
- Btrfs CAS storage integration and physical GPU performance claims.

These require kernel/driver interfaces and hardware-specific validation; the historical architecture notes are design inputs, not evidence that those interfaces exist on Linux Mint 22.3.

## Local tests

```bash
PYTHONPATH=modules/memory/src python3 -m unittest discover -s modules/memory/tests -p 'test_cas_registry.py'
PYTHONPATH=modules/memory/src python3 -m unittest discover -s modules/memory/tests -p 'test_hybrid_policy.py'
```
