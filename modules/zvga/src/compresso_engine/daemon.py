"""User-owned Unix socket service: bounded, sequential, one request per connection."""
import base64
from concurrent.futures import ThreadPoolExecutor
import binascii
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import time
from .codec import MAX_CONTAINER, MAX_INPUT, CodecError, decompress
from .engine import BackendError

MAX_MESSAGE = 2 * MAX_CONTAINER


def default_socket():
    runtime = os.environ.get('XDG_RUNTIME_DIR')
    if not runtime:
        raise ValueError('XDG_RUNTIME_DIR is required; alternatively specify --socket')
    return Path(runtime) / 'compresso-engine' / 'engine.sock'


def read_message(connection):
    deadline = time.monotonic() + 5
    data = bytearray()
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError('message deadline exceeded')
        connection.settimeout(remaining)
        chunk = connection.recv(min(65536, MAX_MESSAGE + 1 - len(data)))
        if not chunk:
            raise ValueError('incomplete message')
        data.extend(chunk)
        if len(data) > MAX_MESSAGE:
            raise ValueError('message exceeds limit')
        if b'\n' in chunk:
            if not data.endswith(b'\n') or data.count(b'\n') != 1:
                raise ValueError('expected one JSON line')
            return json.loads(data)


def send_message(connection, message):
    payload = json.dumps(message, separators=(',', ':')).encode() + b'\n'
    if len(payload) > MAX_MESSAGE:
        raise ValueError('response exceeds limit')
    connection.settimeout(5)
    connection.sendall(payload)


def process_request(request, engine):
    if not isinstance(request, dict) or request.get('op') not in ('compress', 'decompress', 'status'):
        raise ValueError('op must be compress, decompress or status')
    if request['op'] == 'status':
        return {'ok': True, 'configured_backend': engine.backend,
                'helper_available': bool(engine.helper and shutil.which(engine.helper)), 'max_input_bytes': MAX_INPUT,
                'max_decompress_input_bytes': MAX_CONTAINER}
    if not isinstance(request.get('data'), str):
        raise ValueError('data must be base64 text')
    try:
        data = base64.b64decode(request['data'], validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError('invalid base64') from exc
    if request['op'] == 'compress':
        output, metadata = engine.compress(data)
    else:
        output = decompress(data)
        metadata = {'backend': 'cpu', 'fallback_reason': None}
    return {'ok': True, 'data': base64.b64encode(output).decode(),
            'input_bytes': len(data), 'output_bytes': len(output), **metadata}


def serve(path, engine, stop=None, ready=None):
    path = Path(path).absolute()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    parent = path.parent.stat()
    if path.parent.is_symlink() or parent.st_uid != os.getuid() or parent.st_mode & 0o077:
        raise ValueError('socket directory must be owned by this user with mode 0700')
    # Refuse existing sockets rather than unlinking a potentially running server.
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    bound = False
    try:
        server.bind(str(path))
        bound = True
        os.chmod(path, 0o600)
        server.listen(8)
        server.settimeout(0.2)
        if ready:
            ready.set()
        def handle(connection):
            with connection:
                try:
                    _, uid, _ = struct.unpack('3i', connection.getsockopt(
                        socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i')))
                    if uid != os.getuid():
                        raise ValueError('peer must have the same UID')
                    response = process_request(read_message(connection), engine)
                except (ValueError, RecursionError, CodecError, BackendError, OSError) as exc:
                    response = {'ok': False, 'error': str(exc)}
                try:
                    send_message(connection, response)
                except (ValueError, OSError):
                    pass  # A disconnected client must not terminate the service.

        # Keep exactly one active request, without queuing work behind a slow
        # worker. The accept loop stays responsive and rejects overload promptly.
        with ThreadPoolExecutor(max_workers=1) as executor:
            active = None
            while stop is None or not stop.is_set():
                try:
                    connection, _ = server.accept()
                except socket.timeout:
                    continue
                if active is not None and not active.done():
                    with connection:
                        try:
                            # Drain the bounded request before replying/closing so
                            # a large client send cannot lose the busy response.
                            read_message(connection)
                            send_message(connection, {'ok': False, 'error': 'engine busy; retry later'})
                        except (ValueError, RecursionError, OSError):
                            pass
                else:
                    active = executor.submit(handle, connection)
    finally:
        server.close()
        if bound:
            path.unlink(missing_ok=True)


def request(path, message):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(5)
        connection.connect(str(path))
        send_message(connection, message)
        # Worker has a 15-second deadline; include room for codec validation.
        connection.settimeout(25)
        # Response framing has its own bounded read deadline after first byte.
        first = connection.recv(1, socket.MSG_PEEK)
        if not first:
            raise ValueError('daemon closed connection')
        return read_message(connection)
