#!/usr/bin/env python3
# Copyright 2026 The Joao Browser Authors
# Use of this source code is governed by a BSD-style license in LICENSE.
"""Exercise packaging with a synthetic archive, without needing Chromium built."""
import pathlib
import struct
import tempfile
import unittest
import zipfile

import package


class PackageTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name)
        self.version = '155.0.8044.0'
        self.application = self.root / 'Chrome-bin'
        self.version_dir = self.application / self.version
        self.version_dir.mkdir(parents=True)
        executable = bytearray(128)
        executable[:2] = b'MZ'
        struct.pack_into('<I', executable, 0x3c, 64)
        executable[64:70] = b'PE\0\0\x64\x86'
        for name in package.REQUIRED_FILES:
            base = self.application if name == 'chrome.exe' else self.version_dir
            target = base / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(executable if name.endswith(('.exe', '.dll')) else b'resource')
        self.license = self.root / 'credits.html'
        self.license.write_text('Chromium license notices')
        self.zip = self.root / 'portable.zip'

    def test_native_archive_is_flattened_and_marked(self):
        package.create_portable(self.root, self.zip, self.version, self.license)
        with zipfile.ZipFile(self.zip) as archive:
            self.assertIn('JoaoBrowser/chrome.dll', archive.namelist())
            self.assertIn('JoaoBrowser/joao_portable', archive.namelist())
            self.assertFalse(any(self.version in name for name in archive.namelist()))

    def test_missing_runtime_fails(self):
        (self.version_dir / 'chrome.dll').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing runtime'):
            package.create_portable(self.root, self.zip, self.version, self.license)

    def test_wrong_architecture_fails(self):
        path = self.application / 'chrome.exe'
        content = bytearray(path.read_bytes())
        content[68:70] = b'\x4c\x01'
        path.write_bytes(content)
        with self.assertRaisesRegex(ValueError, 'not a Windows x64'):
            package.create_portable(self.root, self.zip, self.version, self.license)

    def test_runtime_collision_fails(self):
        (self.application / 'chrome.dll').write_bytes(b'duplicate')
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            package.create_portable(self.root, self.zip, self.version, self.license)

    def test_traversal_rejected(self):
        for name in ('../outside', 'JoaoBrowser/../outside', 'JoaoBrowser/C:/x',
                     'JoaoBrowser/..\\outside', '/JoaoBrowser/x'):
            with self.subTest(name=name):
                with zipfile.ZipFile(self.zip, 'w') as archive:
                    archive.writestr(name, 'bad')
                with self.assertRaisesRegex(ValueError, 'Unsafe'):
                    package.validate_portable(self.zip)

    def test_case_collision_rejected(self):
        with zipfile.ZipFile(self.zip, 'w') as archive:
            archive.writestr('JoaoBrowser/a', '1')
            archive.writestr('JoaoBrowser/A', '2')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            package.validate_portable(self.zip)


if __name__ == '__main__':
    unittest.main()
