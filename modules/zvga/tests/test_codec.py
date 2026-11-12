import os
import struct
import unittest
from compresso_engine.codec import (
    BLOCK, HEADER, MAX_INPUT, CodecError, compress, decompress, encode_page,
)


class CodecTests(unittest.TestCase):
    def test_known_vectors(self):
        self.assertEqual(encode_page(b'AAAABBC'), b'\x03A\x01B\x00C')
        self.assertEqual(encode_page(b'Z' * 257), b'\xffZ\x00Z')

    def test_roundtrip_and_storage_bound(self):
        for data in (b'', b'a', b'x' * 4096, b'x' * 4097,
                     bytes(range(256)) * 33, os.urandom(9001), b'\0' * MAX_INPUT):
            with self.subTest(size=len(data)):
                encoded = compress(data)
                self.assertEqual(decompress(encoded), data)
                self.assertLessEqual(len(encoded), HEADER.size + len(data) +
                                     ((len(data) + 4095) // 4096) * BLOCK.size)

    def test_incompressible_data_is_raw(self):
        self.assertEqual(compress(bytes(range(256)))[HEADER.size], 0)

    def test_rejects_bad_data(self):
        valid = compress(b'A' * 4096)
        cases = [b'', valid[:-1], valid + b'x', b'BAD!' + valid[4:],
                 HEADER.pack(b'CSO1', MAX_INPUT + 1, 0),
                 valid[:8] + b'\0\0\0\0' + valid[12:],
                 valid[:12] + BLOCK.pack(2, 1) + b'A',
                 valid[:12] + BLOCK.pack(1, 2) + b'\0A']
        for container in cases:
            with self.subTest(container=container[:16]):
                with self.assertRaises(CodecError):
                    decompress(container)
        with self.assertRaises(CodecError):
            compress(b'x' * (MAX_INPUT + 1))

    def test_every_truncation_is_rejected(self):
        encoded = compress(b'x' * 256 + b'y' * 257)
        for length in range(len(encoded)):
            with self.assertRaises(CodecError):
                decompress(encoded[:length])
