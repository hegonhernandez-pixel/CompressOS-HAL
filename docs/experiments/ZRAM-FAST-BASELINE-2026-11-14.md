# ZRAM fast baseline — Linux Mint physical host

Date: 2026-11-14  
Branch: `exp/volatile-memory-shader-pipeline`  
Host profile: Linux Mint 22.3, AMD Ryzen 5 3600, 15 GiB RAM

## Purpose

Establish a measured physical-host baseline for the existing `zram-fast` profile before enabling Zswap or adding zVGA/Vulkan experiments.

This result is runtime evidence only. It does not claim that zVGA is integrated into the kernel swap path.

## Configuration observed before the stress run

- CompressOS memory profile: `zram-fast`
- ZRAM device: `/dev/zram0`
- ZRAM size: approximately 7.8 GiB
- ZRAM compressor: `lz4`
- ZRAM swap priority: `100`
- NVMe backing swap partition: `/dev/nvme0n1p4`
- NVMe swap size: approximately 6.3 GiB
- NVMe swap priority: `-1`
- Zswap: disabled (`N`)
- `compresso-memoryd.service`: active and enabled
- `compressoctl doctor`: HEALTHY
- Temporary test swappiness: `100` (normal host value before the experiment was `60`)

Initial counters immediately before forcing swap were effectively idle:

- ZRAM DATA: 4 KiB
- ZRAM COMPR: 64 B
- ZRAM swap used: 0 B
- `pswpin`: 0
- `pswpout`: 0
- `oom_kill`: 0

## Stress command

```bash
stress-ng \
  --vm 1 \
  --vm-bytes 13G \
  --vm-keep \
  --timeout 60s \
  --metrics-brief
```

Observed stress-ng result:

- successful run
- bogo ops: 3,993,600
- real time: 61.50 s
- user time: 53.07 s
- system time: 8.14 s
- bogo ops/s (real time): 64,936.35
- bogo ops/s (usr+sys): 65,251.47
- failures: 0

CPU scaling governors were reported as `powersave`; they were intentionally left unchanged so this run represents the host's normal power-governor state.

## Post-run memory evidence

```text
Mem:   15 GiB total, ~2.0 GiB used, ~13 GiB free after the workload exited
Swap:  14 GiB total, ~702 MiB used

/dev/nvme0n1p4  6.3G   0B    priority -1
/zram0          7.8G   703M  priority 100
```

ZRAM:

```text
DATA    683.5M
COMPR   280.6M
TOTAL   302.4M
```

Kernel VM counters after the run:

```text
pswpin      87182
pswpout     266359
pgmajfault  101132
oom_kill    0
```

## Interpretation

The workload forced real swap activity.

Because `/zram0` had priority `100` and the NVMe swap partition priority was `-1`, the host placed swapped pages in ZRAM while the NVMe swap remained unused.

The measured logical-data-to-compressed-payload ratio was approximately:

```text
683.5 MiB / 280.6 MiB ≈ 2.44:1
```

Using ZRAM's total allocated memory instead of only compressed payload gives approximately:

```text
683.5 MiB / 302.4 MiB ≈ 2.26:1
```

No OOM kill occurred.

This validates the current `zram-fast` path on the physical Mint host:

```text
RAM pressure
  -> Linux swap-out
  -> high-priority ZRAM
  -> LZ4 compression
  -> no observed NVMe swap write during this run
```

## Experimental sequence from here

1. Keep this run as the `zram-fast` baseline.
2. Restore the host's normal `vm.swappiness=60` after testing.
3. Define and activate a controlled hybrid profile with ZRAM + Zswap + NVMe backing swap.
4. Repeat the same 13 GiB / 60 s workload and collect the same counters.
5. Run the existing zVGA physical-GPU test on the RX 6500 XT.
6. Add a separate RAM -> Vulkan shader -> RAM benchmark that does not persist the payload to disk.
7. Compare throughput, compression ratio, major faults, swap I/O, CPU time and memory overhead across the experimental modes.

## Boundary

The commercial/business launch work is intentionally separate from this branch. This branch exists to continue the original CompressOS-HAL memory/compression/shader research independently of whether those mechanisms become part of the commercial product.
