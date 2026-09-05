#!/usr/bin/env python3
# Copyright 2026 The Joao Browser Authors
# Use of this source code is governed by a BSD-style license in LICENSE.
"""Package the native Chromium Windows installer and its portable payload."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import subprocess
import tempfile
import zipfile

REPOSITORY = 'JoaoDEVWHADS/chromium'
REQUIRED_FILES = ('chrome.exe', 'chrome.dll', 'chrome_elf.dll', 'resources.pak',
                  'icudtl.dat', 'locales/en-US.pak')


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate_pe(path):
    with path.open('rb') as stream:
        if stream.read(2) != b'MZ':
            raise ValueError(f'{path}: missing executable header')
        stream.seek(0x3c)
        offset = struct.unpack('<I', stream.read(4))[0]
        stream.seek(offset)
        if stream.read(6) != b'PE\0\0\x64\x86':
            raise ValueError(f'{path}: not a Windows x64 executable')


def validate_portable(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(name.casefold() for name in names)):
            raise ValueError('Duplicate archive entries')
        for name in names:
            parts = PurePosixPath(name).parts
            if (not parts or parts[0] != 'JoaoBrowser' or '..' in parts or
                    '\\' in name or ':' in name or name.startswith('/')):
                raise ValueError(f'Unsafe portable archive path: {name}')
        for name in (*REQUIRED_FILES, 'joao_portable', 'LICENSE.chromium.html'):
            if 'JoaoBrowser/' + name not in names:
                raise ValueError(f'Missing portable file: {name}')
        bad_file = archive.testzip()
        if bad_file:
            raise ValueError(f'Archive CRC failed: {bad_file}')


def create_portable(extracted, destination, version, license_file):
    application = extracted / 'Chrome-bin'
    version_dir = application / version
    if not version_dir.is_dir():
        raise ValueError(f'Missing packaged version directory: {version_dir}')
    files = {}
    for base in (application, version_dir):
        for source in sorted(base.rglob('*')):
            if base == application and version_dir in source.parents:
                continue
            if source.is_symlink():
                raise ValueError(f'Symlink in browser payload: {source}')
            if not source.is_file():
                continue
            name = source.relative_to(base).as_posix()
            if name in files:
                raise ValueError(f'Conflicting archive file: {name}')
            files[name] = source
    for name in REQUIRED_FILES:
        if name not in files:
            raise ValueError(f'Missing runtime file: {name}')
    validate_pe(files['chrome.exe'])
    validate_pe(files['chrome.dll'])
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, source in files.items():
            archive.write(source, 'JoaoBrowser/' + name)
        archive.writestr('JoaoBrowser/joao_portable', '')
        archive.write(license_file, 'JoaoBrowser/LICENSE.chromium.html')
        archive.writestr('JoaoBrowser/README.txt',
                        'Execute chrome.exe to open Joao Browser.\r\n'
                        'Keep the joao_portable marker beside chrome.exe.\r\n'
                        'Browser profile is stored in User Data beside chrome.exe.\r\n'
                        'Close every browser process before moving this directory.\r\n'
                        'Windows-encrypted passwords and cookies remain tied to\r\n'
                        'the Windows account/machine; use password export/import\r\n'
                        'before changing computers.\r\n')
    validate_portable(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--depot-tools-commit', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    version_values = dict(line.split('=') for line in
                          (root / 'chrome/VERSION').read_text().splitlines())
    version = '.'.join(version_values[key] for key in ('MAJOR', 'MINOR', 'BUILD', 'PATCH'))
    if not re.fullmatch(r'joao-v' + re.escape(version) + r'(?:-[0-9]+)?', args.tag):
        raise ValueError(f'Tag must be joao-v{version}, optionally followed by -BUILD_NUMBER')
    for commit in (args.commit, args.depot_tools_commit):
        if not re.fullmatch('[0-9a-f]{40}', commit):
            raise ValueError('Source revisions must be full Git commit hashes')
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError('Output directory must be empty; do not mix release versions')
    build = args.build_dir.resolve()
    installer = build / 'mini_installer.exe'
    validate_pe(installer)
    offline = output / f'JoaoBrowser-{args.tag}-windows-x64-offline.exe'
    shutil.copy2(installer, offline)
    portable = output / f'JoaoBrowser-{args.tag}-windows-x64-portable.zip'
    with tempfile.TemporaryDirectory(prefix='joao-package-') as staging:
        subprocess.run([str(root / 'third_party/lzma_sdk/bin/win64/7za.exe'),
                        'x', str(build / 'chrome.7z'), '-o' + staging, '-y'], check=True)
        create_portable(Path(staging), portable, version, build / 'gen/components/resources/about_credits.html')
        metadata = Path(staging) / 'ReleaseInfo.cs'
        url = f'https://github.com/{REPOSITORY}/releases/download/{args.tag}/{offline.name}'
        metadata.write_text('internal static class ReleaseInfo {\n'
                            f'  internal const string Url = "{url}";\n'
                            f'  internal const string Sha256 = "{sha256(offline)}";\n'
                            f'  internal const long Size = {offline.stat().st_size}L;\n'
                            '}\n', encoding='ascii')
        online = output / f'JoaoBrowser-{args.tag}-windows-x64-online.exe'
        compiler = Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
        subprocess.run([str(compiler), '/nologo', '/target:winexe', '/platform:x64',
                        '/optimize+', '/reference:System.Net.Http.dll',
                        '/reference:System.Windows.Forms.dll', '/reference:System.Drawing.dll',
                        '/out:' + str(online), str(root / 'tools/joao_browser/OnlineInstaller.cs'),
                        str(metadata)], check=True)
        validate_pe(online)
    manifest = {'version': version, 'tag': args.tag, 'repository': REPOSITORY,
                'source_commit': args.commit, 'depot_tools_commit': args.depot_tools_commit,
                'artifacts': {path.name: {'sha256': sha256(path), 'size': path.stat().st_size}
                              for path in (offline, portable, online)}}
    (output / 'release-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (output / 'SHA256SUMS.txt').write_text(''.join(
        f'{sha256(path)}  {path.name}\n' for path in sorted(output.iterdir())
        if path.is_file()))
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
