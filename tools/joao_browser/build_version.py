#!/usr/bin/env python3
# Copyright 2026 The Joao Browser Authors
# Use of this source code is governed by a BSD-style license in LICENSE.
"""Map the public UTC release timestamp to an increasing Windows file version."""

import argparse
from datetime import datetime
from pathlib import Path

from package import read_release_version


def stamp_native_version(root, tag):
    release = read_release_version(root, tag)
    instant = datetime.strptime(release, '%Y%m%d%H%M%S')
    days = (instant - datetime(2020, 1, 1)).days
    if not 1 <= days <= 65535:
        raise ValueError('Release date is outside the Windows version epoch')
    path = root / 'chrome/VERSION'
    values = dict(line.split('=') for line in path.read_text(encoding='ascii').splitlines())
    major = int(values['MAJOR'])
    if not 1 <= major <= 65535:
        raise ValueError('Chromium major does not fit a Windows version field')
    # Preserve the engine major. All four Windows fields must fit an unsigned WORD.
    # A later day, minute or second produces a strictly newer installer version.
    values = {'MAJOR': major, 'MINOR': days,
              'BUILD': instant.hour * 60 + instant.minute, 'PATCH': instant.second}
    path.write_text(''.join(f'{key}={value}\n' for key, value in values.items()),
                    encoding='ascii')
    return '.'.join(str(value) for value in values.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    print(stamp_native_version(args.root, args.tag))


if __name__ == '__main__':
    main()
