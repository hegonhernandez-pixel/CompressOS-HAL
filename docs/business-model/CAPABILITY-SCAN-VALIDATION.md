# Capability Scanner validation

Date: 2026-11-14
Branch: `exp/business-model-launch`

## Artifact

`tools/compresso-capability-scan/compresso_capability_scan.py`

The scanner is read-only. It inventories operating system, CPU, memory, storage, GPU/Vulkan, shader tools, audio tools, common creator/automation software, Lemonade status/backends/downloaded models, and derives candidate workload profiles.

## Validation performed before publishing the artifact

Focused unit tests:

```text
test_automation_profile_detects_n8n_or_node ... ok
test_creator_image_profile_with_vulkan_and_4gb_vram ... ok
test_video_local_is_not_claimed_ready_on_low_vram ... ok

Ran 3 tests
OK
```

Python syntax compilation also passed with `python -m py_compile`.

This is local implementation validation, not a GitHub Actions result and not proof of compatibility with every Linux or Windows host.

## Next validation

Run the scanner on the physical Mint host and retain:

- `compresso-scan.json`
- `compresso-scan.md`
- `lemonade status --json`
- relevant Vulkan/shader build result

The resulting host report becomes the first reproducible installation manifest for the Creator profile.
