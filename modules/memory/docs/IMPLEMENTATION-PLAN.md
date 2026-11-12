# EXP implementation plan and affected files

## Current package
- src/compresso/memoryd.py: sole writer for swap profile setup.
- config/memory.conf: strict configuration input.
- systemd/compresso-memoryd.service: privileged oneshot service.
- scripts/install-mint.sh and uninstall-mint.sh: Mint integration.
- tests/test_memoryd.py: configuration safety tests.
- buildroot-external/: initial external-tree/package scaffolding.
- .github/workflows/tests.yml: CI entrypoint.

## Next changes
- Add fake-sysfs integration fixtures for Zswap-only and hybrid writes.
- Add read-only metricsd and health reporting; neither may write sysfs.
- Pin Buildroot release and validate paths/Kconfig against that release.
- Add a Mint live-image workflow only after choosing a Mint-compatible customization method.
- Add Vulkan runtime only after CPU reference tests, SPIR-V validation, bounded buffers and output-equivalence tests.

## Safety
The daemon refuses an already active ZRAM device. It does not hot-switch profiles, create swapfiles, call swapoff, or monitor memory pressure. Activation is separate from installation.

<!-- coderabbit-ai-generated:v1 -->

<!-- coderabbit-ai-generated-section:v1:5fb9493d0b5253f8334865807159f55f8c81c891be313853be351bfaf9f7da75 -->

## Linux engine implementation — 2026-11-12

`modules/zvga` now supplies a CPU RLE reference with raw-page fallback, bounded CSO1 decoding, a matching Vulkan shader and native worker, explicit CPU/Vulkan/auto dispatch, and a user-owned Unix socket daemon. CPU reference tests preceded runtime implementation; the build requires SPIR-V validation. Equivalence and daemon tests are included in CI. `compressoctl engine` forwards to the separately installed engine CLI. The existing swap configuration and read-only diagnostics contracts are preserved.

Hardware GPU/Mint runtime validation, indexers, cache management, kernel codec integration, Buildroot pinning, early boot and ISO work remain pending. See the [engine guide](../../zvga/README.md) for reproducible build and test commands.


<!-- /coderabbit-ai-generated:v1 -->
