# Branch status and integration policy

Last reconciled: 2026-11-12

## Canonical source

`main` is the canonical integration branch for this repository. Completed work should land there through reviewable pull requests or explicitly documented integration commits. Experimental and recovery branch names remain useful for traceability and should not be deleted merely because their changes have been integrated.

## Remote branch inventory at reconciliation

| Branch | Observed head | Relationship to `main` before this documentation update | Handling |
|---|---|---|---|
| `main` | `94665b11fe9ed42e7737899dcdfe01b383538c43` | Canonical | Keep as source of truth |
| `exp/physical-hardware-probe` | `dd536453284e3efddadfb75e52cc5fed992d3a46` | Ancestor of `main`; PR #10 was merged | Preserve branch; fast-forward to canonical head after docs commit |
| `exp/cas-audit-hybrid-buildroot` | `8b5f3e82d5c8b8ea4c6f098fe27c5159294fb97b` | Ancestor of `main`; its changes are integrated | Preserve branch; fast-forward to canonical head after docs commit |
| `recovery/import-memory-hal-2026-11-04` | `e0c4d1a80d79f8f1242e163ec3f8ab071c7b31ac` | Ancestor of `main`; retained as recovery history | Preserve branch; fast-forward to canonical head after docs commit |
| `coderabbit/linux-compression-vulkan-shader/af0c6584` | `df3a00f005f1af0e122e180c035c5fcd32b10ef1` | Ancestor of `main`; review work is integrated | Preserve branch; fast-forward to canonical head after docs commit |

The branch comparisons reported no commits unique to these four branch tips relative to `main`. Their histories are ancestors of the canonical branch; they do not require force-pushing or replaying their old changes.

## Synchronization policy

- Fast-forward stale branch refs only when their current tip is an ancestor of the intended target.
- Never force-push as a shortcut for synchronization.
- Keep recovery and experiment refs until their contents have been reviewed and their retention is explicitly approved.
- New experimental work starts from the current `main` and is merged back through a pull request.
- Record physical test evidence in documentation, including exact device identification and limitations.

## Modular AI Stack development — 2026-11-16

- Branch: `feature/modular-installer-lemonade`.
- Commit: `93ed930`, pushed to origin.
- Scope: modular HAL, Lemonade and zVGA provisioning.
- Status: experimental; documentation and PR preparation ongoing.
- `main` remains unchanged by this work.
- Integration target must be verified before opening the PR.
