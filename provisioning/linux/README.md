# CompressOS Linux Modular Provisioning

Status: Experimental.

## Components

The installer supports independent module selection:

- HAL: Linux memory subsystem.
- Lemonade: Local AI inference server.
- zVGA: Experimental Vulkan compression engine.
- AI Stack: HAL + Lemonade + zVGA.
- Node.js: optional LTS prerequisite checker (independent; not part of AI Stack).

Node.js is not a dependency of HAL, Lemonade or zVGA. n8n is intentionally not installed.

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

### Optional Node.js LTS prerequisite check

The optional flag checks for a supported installed Node.js/npm combination. It **does not** download Node.js, add repositories, replace a version, or run remote scripts. If the requested major is absent, it reports the official download instructions and stops. Install manually after reviewing compatibility, then retry.

```bash
bash provisioning/linux/remote-bootstrap.sh \
  --repo-dir "$PWD" --apply --install-node --node-major 24
```

The default Node major is 24; supported choices: 22, 24, 26. Check current support at https://nodejs.org/en/about/previous-releases.

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
