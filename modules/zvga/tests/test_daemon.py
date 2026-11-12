import base64
import os
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from compresso_engine.codec import MAX_CONTAINER, MAX_INPUT, compress
from compresso_engine.daemon import MAX_MESSAGE, process_request, read_message, request, serve
from compresso_engine.engine import Engine


class ProtocolTests(unittest.TestCase):
    def test_status_reports_only_executable_helper(self):
        with tempfile.TemporaryDirectory() as directory:
            helper = Path(directory) / 'worker'
            engine = Engine('auto', str(helper))
            self.assertFalse(process_request({'op': 'status'}, engine)['helper_available'])
            helper.write_text('#!/bin/sh\n')
            helper.chmod(0o600)
            self.assertFalse(process_request({'op': 'status'}, engine)['helper_available'])
            helper.chmod(0o700)
            self.assertTrue(process_request({'op': 'status'}, engine)['helper_available'])

    def test_invalid_requests(self):
        for data in ([], {}, {'op': 'invalid'}, {'op': 'compress'},
                     {'op': 'compress', 'data': '!'}, {'op': 'compress', 'data': 12},
                     {'op': 'decompress', 'data': 'eA=='}):
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    process_request(data, Engine('cpu'))

    def test_message_size_and_framing_limits(self):
        for payload in (b'{}\n{}\n', b'x' * (MAX_MESSAGE + 1), b'{}'):
            reader, writer = socket.socketpair()
            def write():
                try:
                    writer.sendall(payload)
                    writer.shutdown(socket.SHUT_WR)
                except OSError:
                    pass
                finally:
                    writer.close()
            thread = threading.Thread(target=write)
            thread.start()
            try:
                with reader, self.assertRaises(ValueError):
                    read_message(reader)
            finally:
                thread.join(5)

    def test_socket_read_deadline(self):
        reader, writer = socket.socketpair()
        with reader, writer, patch('compresso_engine.daemon.time.monotonic', side_effect=[0, 6]):
            with self.assertRaisesRegex(ValueError, 'deadline'):
                read_message(reader)


class DaemonTests(unittest.TestCase):
    def test_socket_roundtrip_error_recovery_and_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'private' / 'engine.sock'
            ready, stop = threading.Event(), threading.Event()
            errors = []
            def run():
                try:
                    serve(path, Engine('cpu'), stop, ready)
                except Exception as exc:
                    errors.append(exc)
                    ready.set()
            thread = threading.Thread(target=run)
            thread.start()
            try:
                self.assertTrue(ready.wait(5))
                self.assertFalse(errors)
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                status = request(path, {'op': 'status'})
                self.assertTrue(status['ok'])
                self.assertEqual(status['max_input_bytes'], MAX_INPUT)
                self.assertEqual(status['max_decompress_input_bytes'], MAX_CONTAINER)
                self.assertFalse(request(path, {'op': 'bad'})['ok'])
                self.assertFalse(request(path, {'op': 'decompress', 'data': 'eA=='})['ok'])
                for data in (b'', b'AB' * 4096, os.urandom(1024 * 1024)):
                    encoded = request(path, {'op': 'compress', 'data': base64.b64encode(data).decode()})
                    self.assertTrue(encoded['ok'])
                    self.assertEqual(base64.b64decode(encoded['data']), compress(data))
                    decoded = request(path, {'op': 'decompress', 'data': encoded['data']})
                    self.assertEqual(base64.b64decode(decoded['data']), data)
                # A second server must preserve the live socket when bind fails.
                with self.assertRaises(OSError):
                    serve(path, Engine('cpu'), stop)
                self.assertTrue(request(path, {'op': 'status'})['ok'])
            finally:
                stop.set()
                thread.join(5)
            self.assertFalse(thread.is_alive())
            self.assertFalse(errors)
            self.assertFalse(path.exists())

    def test_rejects_public_socket_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            os.chmod(directory, 0o755)
            with self.assertRaisesRegex(ValueError, '0700'):
                serve(Path(directory) / 'engine.sock', Engine('cpu'))

    def test_busy_request_is_rejected_without_waiting_for_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'private' / 'engine.sock'
            ready, stop, started, release = (threading.Event() for _ in range(4))
            class SlowEngine(Engine):
                def compress(self, data):
                    started.set()
                    if not release.wait(5):
                        raise RuntimeError('test worker was not released')
                    return super().compress(data)
            server = threading.Thread(target=serve, args=(path, SlowEngine('cpu'), stop, ready))
            server.start()
            first_response = []
            client = threading.Thread(target=lambda: first_response.append(
                request(path, {'op': 'compress', 'data': 'QQ=='})))
            try:
                self.assertTrue(ready.wait(5))
                client.start()
                self.assertTrue(started.wait(5))
                before = time.monotonic()
                response = request(path, {'op': 'status'})
                self.assertLess(time.monotonic() - before, 2)
                self.assertFalse(response['ok'])
                self.assertIn('busy', response['error'])
            finally:
                release.set()
                if client.ident:
                    client.join(5)
                stop.set()
                server.join(5)
            self.assertTrue(first_response[0]['ok'])
            self.assertFalse(server.is_alive())
