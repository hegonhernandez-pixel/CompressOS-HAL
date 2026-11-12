import os
import struct
import subprocess
import unittest
from unittest.mock import patch
from compresso_engine import codec
from compresso_engine.engine import BackendError, Engine


class DispatchTests(unittest.TestCase):
    def test_cpu_and_empty_input(self):
        for backend, data in (('cpu', b'AAA'), ('vulkan', b'')):
            output, metadata = Engine(backend).compress(data)
            self.assertEqual(codec.decompress(output), data)
            self.assertEqual(metadata['backend'], 'cpu')

    def test_fallback_is_reported_and_explicit_vulkan_fails(self):
        for failure in (FileNotFoundError(), subprocess.TimeoutExpired('worker', 15),
                        subprocess.CalledProcessError(2, 'worker')):
            with patch('compresso_engine.engine.subprocess.run', side_effect=failure):
                output, metadata = Engine('auto', '/missing').compress(b'A' * 9000)
                self.assertEqual(codec.decompress(output), b'A' * 9000)
                self.assertEqual(metadata['backend'], 'cpu')
                self.assertTrue(metadata['fallback_reason'])
                with self.assertRaises(BackendError):
                    Engine('vulkan', '/missing').compress(b'A')

    def test_corrupt_gpu_output_is_rejected_even_for_raw_page(self):
        # Correct shape, but wrong data on an incompressible page. It must not
        # disappear behind raw-storage selection.
        words = [256] + [0] * 4096
        output = struct.pack('<4097I', *words)
        with patch('compresso_engine.engine.subprocess.run', return_value=
                   subprocess.CompletedProcess([], 0, output, b'')):
            with self.assertRaises(BackendError):
                Engine('vulkan', '/worker').compress(bytes(range(256)))

    def test_rejects_invalid_output_shape_count_and_token(self):
        for output in (b'bad', bytes(4097 * 4),
                       struct.pack('<II', 1, 65536) + bytes(4095 * 4)):
            with patch('compresso_engine.engine.subprocess.run', return_value=
                       subprocess.CompletedProcess([], 0, output, b'')):
                with self.assertRaises(BackendError):
                    Engine('vulkan', '/worker').compress(b'A')

    def test_input_bound_is_checked_before_worker(self):
        with patch('compresso_engine.engine.subprocess.run') as run:
            with self.assertRaises(codec.CodecError):
                Engine('vulkan', '/worker').compress(b'A' * (codec.MAX_INPUT + 1))
            run.assert_not_called()


@unittest.skipUnless(os.environ.get('COMPRESSO_VULKAN_HELPER'),
                     'set COMPRESSO_VULKAN_HELPER to require real Vulkan execution')
class VulkanEquivalenceTests(unittest.TestCase):
    def test_gpu_output_equals_cpu(self):
        engine = Engine('vulkan', os.environ['COMPRESSO_VULKAN_HELPER'])
        for data in (b'A', b'Z' * 257, b'X' * 4096, b'X' * 4097,
                     bytes(range(256)) * 50, os.urandom(9001),
                     b'\0' * codec.MAX_INPUT, os.urandom(codec.MAX_INPUT)):
            with self.subTest(size=len(data)):
                output, metadata = engine.compress(data)
                self.assertEqual(metadata['backend'], 'vulkan')
                self.assertTrue(metadata['device'])
                self.assertEqual(output, codec.compress(data))
                self.assertEqual(codec.decompress(output), data)

    def test_native_input_bound(self):
        result = subprocess.run([os.environ['COMPRESSO_VULKAN_HELPER']],
                                input=b'x' * (codec.MAX_INPUT + 1), capture_output=True,
                                timeout=20)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(result.stdout)
        self.assertIn(b'input exceeds 1 MiB', result.stderr)
