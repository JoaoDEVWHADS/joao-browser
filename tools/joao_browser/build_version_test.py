#!/usr/bin/env python3
# Copyright 2026 The Joao Browser Authors
# Use of this source code is governed by a BSD-style license in LICENSE.
import pathlib
import tempfile
import unittest

from build_version import stamp_native_version
from package import read_release_version


class BuildVersionTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = pathlib.Path(temporary.name)
        (self.root / 'chrome').mkdir()
        (self.root / 'chrome/VERSION').write_text('MAJOR=155\nMINOR=0\nBUILD=8044\nPATCH=0\n')

    def stamp(self, version):
        (self.root / 'version.txt').write_text(version + '\n')
        return tuple(map(int, stamp_native_version(self.root, 'joao-v' + version).split('.')))

    def test_seconds_minutes_and_days_increase(self):
        versions = [self.stamp(v) for v in ('20260905235958', '20260905235959',
                                           '20260906000000', '20260906000100')]
        self.assertEqual(sorted(set(versions)), versions)
        for version in versions:
            self.assertEqual(155, version[0])
            self.assertTrue(all(0 <= value <= 65535 for value in version))
            self.assertGreater(version, (155, 0, 8044, 0))

    def test_repeating_stamp_is_deterministic(self):
        self.assertEqual(self.stamp('20260905123045'), self.stamp('20260905123045'))

    def test_invalid_dates_and_format_rejected(self):
        for version in ('20260230000000', '20260905246000', '155.0.8044.0',
                        '2026090512000', '../../bad', '20200101000000'):
            with self.subTest(version=version), self.assertRaises(ValueError):
                self.stamp(version)

    def test_tag_must_match_committed_timestamp(self):
        self.stamp('20260905123045')
        with self.assertRaisesRegex(ValueError, 'match version.txt'):
            read_release_version(self.root, 'joao-v20260905123046')


if __name__ == '__main__':
    unittest.main()
