"""Embed already validated SPIR-V as aligned C++ words."""
import pathlib
import struct
import sys

source = pathlib.Path(sys.argv[1]).read_bytes()
words = struct.unpack('<' + 'I' * (len(source) // 4), source)
pathlib.Path(sys.argv[2]).write_text(
    '#include <cstdint>\nstatic constexpr uint32_t shader_code[] = {\n' +
    ','.join(hex(word) for word in words) + '\n};\n')
