#!/usr/bin/env python3
"""Run the self-contained RAFTBOUND game on http://localhost:8000."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from functools import partial

if __name__ == '__main__':
    directory = str(Path(__file__).resolve().parent)
    server = ThreadingHTTPServer(('127.0.0.1', 8000), partial(SimpleHTTPRequestHandler, directory=directory))
    print('RAFTBOUND: http://localhost:8000')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')
