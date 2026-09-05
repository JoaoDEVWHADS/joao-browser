#!/usr/bin/env python3
# Copyright 2026 The Joao Browser Authors
# Use of this source code is governed by a BSD-style license in LICENSE.
"""Loopback-only, deterministic native adblock smoke-test fixture."""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            port = self.server.server_port
            content_type = 'text/html; charset=utf-8'
            body = f'''<!doctype html><html><body>
<script src="/normal.js"></script>
<script src="http://ad.doubleclick.net:{port}/ad.js"></script>
</body></html>'''
        elif self.path in ('/normal.js', '/ad.js'):
            name = 'normal' if self.path == '/normal.js' else 'ad'
            content_type = 'application/javascript'
            body = f'document.body.setAttribute("data-joao-{name}", "executed");'
        else:
            self.send_error(404)
            return
        payload = body.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ready-file', type=Path, required=True)
    args = parser.parse_args()
    with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
        temporary = args.ready_file.with_suffix('.tmp')
        temporary.write_text(json.dumps({'port': server.server_port}), encoding='utf-8')
        temporary.replace(args.ready_file)
        server.serve_forever()


if __name__ == '__main__':
    main()
