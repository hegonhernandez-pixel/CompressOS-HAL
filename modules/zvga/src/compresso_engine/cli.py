"""Linux compression worker CLI and local daemon client."""
import argparse
import base64
import json
import signal
import sys
import threading
from . import codec
from .daemon import default_socket, process_request, request, serve
from .engine import BackendError, Engine


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('compress', 'decompress', 'status', 'serve'))
    parser.add_argument('--backend', choices=('cpu', 'auto', 'vulkan'), default='auto',
                        help='local/serve backend; remote requests use daemon configuration')
    parser.add_argument('--socket', help='daemon socket (required only outside a user runtime)')
    parser.add_argument('--remote', action='store_true', help='send operation to running daemon')
    parser.add_argument('--helper', help='path to trusted compresso-vulkan worker (local/serve only)')
    args = parser.parse_args(argv)
    try:
        engine = Engine(args.backend, args.helper)
        if args.operation == 'serve':
            if args.remote:
                parser.error('serve cannot use --remote')
            stop = threading.Event()
            for signum in (signal.SIGTERM, signal.SIGINT):
                signal.signal(signum, lambda *_: stop.set())
            serve(args.socket or default_socket(), engine, stop)
            return 0
        message = {'op': args.operation}
        if args.operation != 'status':
            limit = codec.MAX_INPUT if args.operation == 'compress' else codec.MAX_CONTAINER
            data = sys.stdin.buffer.read(limit + 1)
            if len(data) > limit:
                raise ValueError('input exceeds operation limit')
            message['data'] = base64.b64encode(data).decode()
        response = (request(args.socket or default_socket(), message) if args.remote
                    else process_request(message, engine))
        if not response['ok']:
            raise ValueError(response['error'])
        if args.operation == 'status':
            print(json.dumps(response))
        else:
            sys.stdout.buffer.write(base64.b64decode(response.pop('data'), validate=True))
            print(json.dumps(response), file=sys.stderr)
        return 0
    except (ValueError, BackendError, OSError) as exc:
        print(f'compresso-engine: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
