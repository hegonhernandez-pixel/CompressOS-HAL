"""CPU/Vulkan dispatch with validated results and observable fallback."""
import shutil
import struct
import subprocess
from . import codec


class BackendError(RuntimeError):
    pass


class Engine:
    def __init__(self, backend='auto', helper=None):
        if backend not in ('cpu', 'vulkan', 'auto'):
            raise ValueError('backend must be cpu, vulkan or auto')
        self.backend = backend
        self.helper = helper or shutil.which('compresso-vulkan')

    def _vulkan(self, data):
        if not self.helper:
            raise BackendError('compresso-vulkan is not installed')
        try:
            result = subprocess.run([self.helper], input=data, capture_output=True,
                                    timeout=15, check=True)
        except (OSError, subprocess.SubprocessError) as exc:
            raise BackendError('Vulkan worker failed or exceeded its deadline') from exc
        pages = (len(data) + codec.PAGE_SIZE - 1) // codec.PAGE_SIZE
        if len(result.stdout) != pages * 4097 * 4:
            raise BackendError('invalid Vulkan output size')
        encoded = []
        for page in range(pages):
            start = page * 4097 * 4
            count, = struct.unpack_from('<I', result.stdout, start)
            page_length = min(codec.PAGE_SIZE, len(data) - page * codec.PAGE_SIZE)
            if not 1 <= count <= page_length:
                raise BackendError('invalid Vulkan run count')
            payload = bytearray()
            for index in range(count):
                word, = struct.unpack_from('<I', result.stdout, start + 4 + index * 4)
                if word > 65535:
                    raise BackendError('invalid Vulkan token')
                payload.extend((word >> 8, word & 255))
            # Validate every page, even those later stored raw. This also guards
            # against shader/driver errors producing a valid-looking container.
            expected = codec.encode_page(data[page * codec.PAGE_SIZE:
                                              (page + 1) * codec.PAGE_SIZE])
            if payload != expected:
                raise BackendError('Vulkan output differs from CPU reference')
            encoded.append(bytes(payload))
        return codec.pack(data, encoded), result.stderr.decode('utf-8', errors='replace').strip()

    def compress(self, data):
        if len(data) > codec.MAX_INPUT:
            raise codec.CodecError('input exceeds 1 MiB')
        if self.backend == 'cpu' or not data:
            return codec.compress(data), {'backend': 'cpu', 'fallback_reason': None}
        try:
            output, device = self._vulkan(data)
            return output, {'backend': 'vulkan', 'device': device, 'fallback_reason': None}
        except BackendError as exc:
            if self.backend == 'vulkan':
                raise
            return codec.compress(data), {'backend': 'cpu', 'fallback_reason': str(exc)}
