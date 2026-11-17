# Fast RAM and GPU incident observations — 2026-11-16

## Scope and evidence

User-provided terminal snapshots on Linux Mint 22.3 during and after AI video generation using Lemonade. These are observational snapshots, not controlled benchmarks. No kernel compression engine, GPU shader integration with kernel swap, or VRAM-backed swap is demonstrated.

## Memory configuration

- Physical RAM: ~15 GiB.
- ZRAM: `/zram0`, 7.8 GiB, LZ4, swap priority 100.
- NVMe swap: `/dev/nvme0n1p4`, 6.3 GiB, swap priority -1.
- Zswap: disabled (`enabled=N`), configured pool limit 20%, compressor LZO (inactive).
- `vm.swappiness=60`.
- `sudo compressoctl doctor`: `CompressOS-HAL: HEALTHY (perfil: zram-fast)` after reboot. This validates the observed configuration, not the future kernel engine.

## Observations during video-generation workflow

Snapshots were taken at different times; they must not be interpreted as a continuous instrumented trace.

| Snapshot | RAM used | RAM available | Swap used | ZRAM used | NVMe used | Memory PSI some avg10/avg60/avg300 | Memory PSI full avg10/avg60/avg300 |
|---|---:|---:|---:|---:|---:|---|---|
| During video generation, first `free -h` snapshot | 6.3 GiB | 9.2 GiB | 1.5 GiB | Not separately shown in same command | Not separately shown | 0.00/0.09/0.33 | 0.00/0.09/0.33 |
| After a generation finished, 20:52:53 local | 3.1 GiB | 12 GiB | 1.3 GiB | 1.3 GiB | 0 B | 0.00/0.00/0.16 | 0.00/0.00/0.16 |
| Subsequent high-memory snapshot, 21:03:33 local | 11 GiB | 4.3 GiB | 4.1 GiB | 4.1 GiB | 0 B | 0.15/0.36/0.40 | 0.15/0.35/0.40 |

Additional `swapon --show` snapshots during the workflow showed ZRAM at 2.9–3.1 GiB and NVMe at 0 B. The 21:03 snapshot demonstrates elevated memory usage and low measured PSI at that instant; it does not prove a specific speedup or stability under all workloads.

One `/sys/block/zram0/mm_stat` sample was:

```text
1553416192 612769890 651665408 3329179648 2356957184 9593 910 35073 442500
```

The first three values represent original data bytes, compressed data bytes, and total memory used respectively. The counters are a point-in-time observation.

## GPU failure and recovery observations

Previous boot's kernel journal around 17:02 local showed:
- `amdgpu 0000:0a:00.0: device lost from bus!`
- `ring sdma0 test failed (-110)`
- `GPU reset end with ret = -19`
- `GPU Recovery Failed: -19`
- `flip_done timed out`

After reboot:
- PCI device `1002:743f` (XFX Navi 24 RX 6500 XT family) was visible at `0a:00.0`.
- Kernel driver `amdgpu` was bound and loaded.
- Kernel logged `SMU is initialized successfully!` and registered SDMA and compute rings.
- A read-only search for `device lost|gpu recovery failed|ring.*timeout|pcie bus error|aer.*error` in the current boot journal returned no matches.

These observations support successful reinitialization after reboot, not proof of GPU stability under load or root cause.

## Hardware context reported by user

The user reported replacing a previous power supply with a smaller one after an attempted larger GPU installation failed and an adapter burned out. A power-delivery or connection problem is a **hypothesis**, not a confirmed cause of the prior PCIe/GPU loss. Before additional intensive GPU testing, inspect the power supply's suitability, cabling/connectors, and GPU power requirements; avoid reusing damaged adapters.

## Architecture and limitations

The currently operating Fast RAM stage uses existing Linux ZRAM/LZ4 and supervisor diagnostics. It is an intermediate implementation. The intended CompressOS compression engine, shader-assisted kernel memory path, and dynamic coordination/drain across RAM/VRAM/NVMe remain unimplemented or unvalidated. No Zswap, swap-priority, or kernel parameter changes were performed for this observation.
