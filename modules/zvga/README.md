<!-- coderabbit-ai-generated:v1 -->

<!-- coderabbit-ai-generated-section:v1:2955bb52a200bad7b10c7434a6ce050b68c5d504fc24195cbe6b31cf056ac3e3 -->

# Experimental Linux compression engine (zVGA)

This module connects a bounded CPU compression reference, a Vulkan 1.0 compute shader, a scheduler and a local user daemon. It operates on explicit user-space buffers. `memoryd` retains sole ownership of swap configuration; the engine does not supply a kernel ZRAM/Zswap codec or compress arbitrary process memory.

## Format and bounds

CSO1 is an experimental lossless format, not compatible with LZ4, Zstd or kernel swap representations. Compression accepts at most 1 MiB of input. Decompression accepts CSO1 containers up to 1,049,356 bytes and produces at most 1 MiB. Pages are 4096 bytes. RLE pairs contain a byte for run length minus one and a byte value (maximum run 256). Pages that would expand are stored raw.

The little-endian header is `4sII`: magic `CSO1`, original byte length, CRC32. Each page has a `BH` header: mode (0 raw, 1 RLE) and payload byte length, followed by its payload. The original length determines the number and expanded size of pages. Empty inputs contain only the header. Decoding rejects invalid sizes, excess expansion, malformed/truncated blocks, trailing bytes and CRC mismatch. CRC32 detects accidental corruption; it is not authentication.

GPU buffers use one uint per input byte and a fixed 4097-uint output slice per page (run count plus at most 4096 packed tokens). Each invocation owns one page. Shader compilation and `spirv-val` are mandatory build gates. The worker checks compute limits, requests coherent host-visible memory, waits for a fence after the shader-to-host barrier and has a ten-second completion deadline. The dispatcher bounds the process to fifteen seconds. The entire GPU result is compared with the CPU reference before use, including pages ultimately stored raw.

This first backend deliberately repeats reference work and initializes Vulkan for each request. It makes no acceleration or compression-ratio claim. Physical GPUs and Linux Mint still require validation; software Vulkan validates execution and equivalence only.

## Build on Linux

Ubuntu/Mint dependencies for the optional Vulkan backend:

```bash
sudo apt-get install cmake ninja-build g++ python3 libvulkan-dev mesa-vulkan-drivers glslang-tools spirv-tools
cmake -S modules/zvga -B build/zvga -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build/zvga
COMPRESSO_VULKAN_HELPER="$PWD/build/zvga/compresso-vulkan" bash modules/zvga/scripts/test.sh
```

Select a software ICD explicitly when comparing in a VM without a physical GPU. Mesa's lavapipe manifest is normally `/usr/share/vulkan/icd.d/lvp_icd.json` or `lvp_icd.x86_64.json`; set `VK_ICD_FILENAMES` to the file on your host. CI requires this backend and fails on Vulkan errors rather than skipping equivalence tests.

For a CPU-only installation, configure with `-DCOMPRESSO_VULKAN=OFF`; no C++ compiler is required.

Without `COMPRESSO_VULKAN_HELPER`, the test suite skips the two runtime Vulkan tests. For source use, run `PYTHONPATH=modules/zvga/src python3 -m compresso_engine.cli ...` and supply `--helper "$PWD/build/zvga/compresso-vulkan"` for the compiled worker.

## Install and use

```bash
sudo cmake --install build/zvga
compresso-engine status
compresso-engine compress --backend cpu < input.bin > input.cso
compresso-engine decompress < input.cso > restored.bin
cmp input.bin restored.bin
```

The compress and decompress commands read binary stdin, write binary stdout, and report the actual backend and fallback reason as JSON on stderr. The status command reads no stdin and prints JSON on stdout with configuration, helper availability and both input limits. Its package path is relative to the launcher, so the CLI also supports a CMake install-time `--prefix` override. Configure the final prefix with `-DCMAKE_INSTALL_PREFIX=...` when using the systemd service; its ExecStart path is set during configuration.

Inputs above the operation limit are rejected. `--backend auto` tries Vulkan and falls back to CPU with a reason. `--backend vulkan` returns an error if Vulkan fails; empty input uses CPU without GPU dispatch. Decompression always uses CPU. `status` reports configuration and worker presence, not a GPU health probe; force Vulkan compression to verify execution. `--helper` selects a trusted local executable and is not accepted from socket requests.

If the memory package is installed from this revision, the same commands are exposed by `compressoctl engine ...`. Install the engine separately using CMake; the memory installer does not install GPU dependencies.

## User daemon

Installation does not enable or start the service. On a Linux session with systemd user services:

```bash
systemctl --user daemon-reload
systemctl --user start compresso-engined.service
compresso-engine status --remote
compresso-engine compress --remote < input.bin > input.cso
compresso-engine decompress --remote < input.cso > restored.bin
systemctl --user stop compresso-engined.service
```

For a custom installation prefix, systemd may not search the installed unit directory. Link it before starting the service, using the configured prefix and an absolute path:

```bash
systemctl --user link "$HOME/.local/lib/systemd/user/compresso-engined.service"
systemctl --user daemon-reload
```

The example uses a build configured with `-DCMAKE_INSTALL_PREFIX="$HOME/.local"`. Then start the unit as shown above.

After testing, optionally enable subsequent user-session activation with `systemctl --user enable compresso-engined.service`. It is independent of `compresso-memoryd.service`. The user must have permission to access their GPU render device for hardware Vulkan.

For a manual foreground server, run `compresso-engine serve --backend auto`. The default socket is `$XDG_RUNTIME_DIR/compresso-engine/engine.sock`. Outside a user session, use `--socket /path/to/private-directory/engine.sock` on both server and remote client. The directory must belong to the current UID with mode 0700; the socket is 0600 and peers must share the UID. Existing sockets are never replaced; after an unclean shutdown, verify no server is running before manually removing a stale socket. SIGINT/SIGTERM shut down after the bounded current request and remove the socket.

Protocol: one newline-terminated JSON object per connection. Operations are `status`, `compress`, `decompress`; data is strict base64. Compression/decompression responses have `ok`, base64 `data`, `input_bytes`, `output_bytes` and backend metadata, or an `error`. Status returns `ok`, `configured_backend`, `helper_available`, `max_input_bytes` and `max_decompress_input_bytes`; it has no data payload.

One request is processed at a time. While it is active, additional connections receive an engine-busy error after their bounded request is read; clients can retry later. Work is never queued behind a slow Vulkan worker. Status publishes separate compression and decompression input limits.

Wire messages are capped at twice the maximum CSO1 container size and reading/sending has five-second deadlines. There is no request-selected backend, executable, filesystem path or shell execution.

## Remaining planned work

Physical GPU and Mint testing, performance measurement, richer codecs, indexers/Fast-RAM caching, kernel adapters, full Buildroot rootfs compilation/boot and Mint ISO/early-boot work remain separate milestones. The optional zVGA Buildroot package and defconfig are present, but only defconfig resolution has been validated. This module establishes the explicit buffer path between engine, shader and daemon.


<!-- /coderabbit-ai-generated:v1 -->