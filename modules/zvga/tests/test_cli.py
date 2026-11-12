import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest


class CliTests(unittest.TestCase):
    def command(self, *args):
        installed = os.environ.get('COMPRESSO_INSTALLED_CLI')
        return ([installed] if installed else [sys.executable, '-m', 'compresso_engine.cli']) + list(args)

    def test_local_binary_roundtrip_and_explicit_worker_failure(self):
        data = b'XYZ' * 3000
        encoded = subprocess.run(self.command('compress', '--backend', 'cpu'),
                                 input=data, capture_output=True, timeout=10, check=True)
        decoded = subprocess.run(self.command('decompress'), input=encoded.stdout,
                                 capture_output=True, timeout=10, check=True)
        self.assertEqual(decoded.stdout, data)
        failure = subprocess.run(self.command('compress', '--backend', 'vulkan',
                                              '--helper', '/nonexistent/worker'),
                                 input=data, capture_output=True, timeout=10)
        self.assertEqual(failure.returncode, 2)
        self.assertEqual(failure.stdout, b'')

    def test_foreground_daemon_client_and_sigterm_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'private' / 'engine.sock'
            helper = os.environ.get('COMPRESSO_VULKAN_HELPER')
            backend = 'vulkan' if helper else 'cpu'
            options = ['--helper', helper] if helper else []
            server = subprocess.Popen(self.command('serve', '--backend', backend,
                                                    '--socket', str(path), *options),
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic() + 5
                ready = False
                while time.monotonic() < deadline and server.poll() is None:
                    probe = subprocess.run(self.command('status', '--remote', '--socket', str(path)),
                                           capture_output=True, timeout=2)
                    if probe.returncode == 0:
                        ready = True
                        break
                    time.sleep(0.02)
                self.assertTrue(ready, 'daemon did not answer a readiness request')
                result = subprocess.run(self.command('compress', '--remote', '--socket', str(path)),
                                        input=b'A' * 8192, capture_output=True, timeout=30, check=True)
                self.assertIn(('\"backend\": \"' + backend + '\"').encode(), result.stderr)
                decoded = subprocess.run(self.command('decompress', '--remote', '--socket', str(path)),
                                         input=result.stdout, capture_output=True, timeout=10, check=True)
                self.assertEqual(decoded.stdout, b'A' * 8192)
            finally:
                server.send_signal(signal.SIGTERM)
                try:
                    stdout, stderr = server.communicate(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.communicate()
                    raise
            self.assertEqual(server.returncode, 0, stderr)
            self.assertFalse(path.exists())

    @unittest.skipUnless(os.environ.get('COMPRESSO_INSTALLED_CLI'), 'requires installed CLI')
    def test_compressoctl_engine_forwarding(self):
        cli = Path(__file__).resolve().parents[2] / 'memory' / 'scripts' / 'compressoctl'
        environment = os.environ.copy()
        environment['PATH'] = str(Path(os.environ['COMPRESSO_INSTALLED_CLI']).parent) + ':' + environment['PATH']
        result = subprocess.run(['bash', str(cli), 'engine', 'status'], env=environment,
                                capture_output=True, check=True, timeout=10)
        self.assertIn(b'configured_backend', result.stdout)

    @unittest.skipUnless(os.environ.get('COMPRESSO_INSTALLED_CLI'), 'requires installed CLI')
    def test_installed_launcher_ignores_untrusted_python_packages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evil = root / 'compresso_engine'
            evil.mkdir()
            (evil / '__init__.py').write_text('from pathlib import Path\nPath("compromised").touch()\n')
            (evil / 'cli.py').write_text('raise SystemExit(123)\n')
            env = os.environ.copy()
            env['PYTHONPATH'] = directory
            result = subprocess.run(self.command('status', '--backend', 'cpu'), cwd=directory,
                                    env=env, capture_output=True, timeout=10, check=True)
            self.assertIn(b'"configured_backend": "cpu"', result.stdout)
            self.assertFalse((root / 'compromised').exists())
