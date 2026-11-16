# CompressOS Linux Modular Provisioning

Status: Experimental.

## Components

The installer supports independent module selection:

- HAL: Linux memory subsystem.
- Lemonade: Local AI inference server.
- zVGA: Experimental Vulkan compression engine.
- AI Stack: HAL + Lemonade + zVGA.

## Installation modes

Run from the repository root.

### Check-only (default)

bash provisioning/linux/remote-bootstrap.sh \
  --repo-dir "$PWD"

### HAL

bash provisioning/linux/remote-bootstrap.sh \
  --repo-dir "$PWD" --apply --install-hal

### Lemonade

bash provisioning/linux/remote-bootstrap.sh \
  --repo-dir "$PWD" --apply --install-lemonade

### zVGA

bash provisioning/linux/remote-bootstrap.sh \
  --repo-dir "$PWD" --apply --build-zvga

### Complete AI Stack

bash provisioning/linux/remote-bootstrap.sh \
  --repo-dir "$PWD" --apply --install-ai-stack

WARNING: --apply performs real installation operations.
Do not run it without reviewing the target system.

HAL installation does not activate memory services by default.

## Validation record

Date: 2026-11-16
Branch: feature/modular-installer-lemonade
Commit: 93ed930

Four simulated installation flows passed:

- Lemonade only.
- HAL only.
- zVGA only.
- Complete AI Stack.

The simulations used temporary repository copies and mocked
sudo, cmake and lemonade commands.

These tests validate installer control flow and module isolation.
They do not establish successful installation on a clean system,
runtime compatibility or performance improvements.

## Pending validation

- Profile-specific tests.
- Clean Linux Mint installation.
- Dependency and rollback testing.
- Actual AI inference and Vulkan runtime integration.
- Performance benchmarking.
