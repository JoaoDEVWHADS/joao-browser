#!/usr/bin/env python3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import tempfile
import unittest
from pathlib import Path

from generate_joao_version import read_version


class VersionTest(unittest.TestCase):
    def test_release_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'version.txt'
            path.write_text('20240229123059\n')
            self.assertEqual(read_version(path), '20240229123059')

    def test_invalid_timestamps(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'version.txt'
            for value in ['20230229120000', '20260905240000',
                          '20260905120060', 'joao-v20260905120000',
                          '155.0.8044.0', '2026090512000x', '']:
                with self.subTest(value=value):
                    path.write_text(value)
                    with self.assertRaises(ValueError):
                        read_version(path)

    def test_missing_version(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                read_version(Path(directory) / 'missing')


if __name__ == '__main__':
    unittest.main()
