#!/usr/bin/env python3
# Copyright 2026 The Joao Browser Authors
# Use of this source code is governed by a BSD-style license in LICENSE.
"""Exercise the real HTTP fixture and its ready-file startup protocol."""

import http.client
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


class SmokeServerTest(unittest.TestCase):
    def test_fixture_lifecycle_and_responses(self):
        with tempfile.TemporaryDirectory(prefix='Joao fixture ') as directory:
            ready = Path(directory) / 'ready.json'
            process = subprocess.Popen([
                sys.executable, str(Path(__file__).with_name('smoke_server.py')),
                '--ready-file', str(ready)])
            try:
                deadline = time.monotonic() + 10
                while not ready.exists():
                    self.assertIsNone(process.poll(), 'Fixture exited before ready')
                    self.assertLess(time.monotonic(), deadline, 'Fixture startup timed out')
                    time.sleep(0.02)
                port = json.loads(ready.read_text(encoding='utf-8'))['port']
                connection = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
                try:
                    for path, expected in (
                            ('/', f'http://ad.doubleclick.net:{port}/ad.js'),
                            ('/normal.js', 'data-joao-normal'),
                            ('/ad.js', 'data-joao-ad')):
                        connection.request('GET', path, headers={
                            'Host': f'ad.doubleclick.net:{port}'})
                        response = connection.getresponse()
                        self.assertEqual(response.status, 200)
                        self.assertEqual(response.getheader('Cache-Control'), 'no-store')
                        self.assertIn(expected, response.read().decode('utf-8'))
                    connection.request('GET', '/missing')
                    response = connection.getresponse()
                    self.assertEqual(response.status, 404)
                    response.read()
                finally:
                    connection.close()
            finally:
                process.terminate()
                process.wait(timeout=5)


if __name__ == '__main__':
    unittest.main()
