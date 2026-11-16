# Authorized remote provisioning

## Goal

Reproduce a known-good CompressOS AI node from an authorized remote session without requiring the customer to ship the computer.

The MVP does **not** maintain permanent unrestricted remote control.

## Transport

The provisioning executable is designed to be transferred to the customer's machine and invoked through an authenticated remote channel such as SSH.

Example operator flow:

```bash
scp <approved-bundle> customer-host:~/compresso-install/
ssh customer-host
cd ~/compresso-install/CompressOS-HAL
bash provisioning/linux/remote-bootstrap.sh --repo-dir "$PWD"
```

The first run is check-only.

After reviewing the capability report and receiving authorization:

```bash
bash provisioning/linux/remote-bootstrap.sh \
  --repo-dir "$PWD" \
  --apply \
  --install-lemonade \
  --build-zvga
```

Memory activation remains a separate explicit decision:

```bash
bash provisioning/linux/remote-bootstrap.sh \
  --repo-dir "$PWD" \
  --apply \
  --enable-memory
```

## Why activation is separated

The existing memory installer intentionally installs without starting services because another ZRAM manager may already own the device. Remote provisioning preserves that boundary:

1. install;
2. run `memoryd.py --dry-run`;
3. inspect conflicts/configuration;
4. only then enable the service with explicit authorization.

## What is automated in v0.1

- capability scan before changes;
- Mint/Ubuntu validation;
- base build/Vulkan/creator dependencies;
- existing CompressOS memory installer;
- memory dry-run;
- optional explicit memory activation;
- optional Lemonade installation;
- host-aware Lemonade backend installation from the advertised backend catalog;
- optional zVGA shader/worker build;
- bounded zVGA test;
- post-install scan;
- provisioning manifest and logs.

## What remains

- signed/versioned install bundles instead of raw repository transfer;
- Windows PowerShell bootstrap;
- package/version pinning;
- rollback orchestration;
- automatic profile/model selection from the scanner JSON;
- remote-support session expiration;
- central client/device database upload;
- n8n/MCP deployment;
- unattended integration tests on clean VMs.

## Security boundary

No credentials are embedded in the script. Private GitHub tokens should not be copied onto customer hosts. Deliver a versioned bundle or package to the authorized session instead.
