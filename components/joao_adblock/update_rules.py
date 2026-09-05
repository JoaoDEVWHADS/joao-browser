#!/usr/bin/env python3
"""Refresh the reviewed data snapshot over HTTPS; commit before building a release."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).parent
URL = 'https://easylist.to/easylist/easylist.txt'
LIMIT = 8 * 1024 * 1024


def validate(data):
    text = data.decode('utf-8')
    if not text.startswith('[Adblock Plus') or len(data) < 100_000:
        raise ValueError('Not an EasyList snapshot')
    if len(data) > LIMIT or '\x00' in text:
        raise ValueError('Invalid or oversized rules')
    return text


def main():
    with urllib.request.urlopen(urllib.request.Request(
            URL, headers={"User-Agent": "JoaoBrowser-RulesUpdater/1.0"}), timeout=60) as response:
        if response.url != URL:
            raise ValueError('Unexpected upstream redirect')
        data = response.read(LIMIT + 1)
    validate(data)
    temporary = ROOT / 'easylist.txt.tmp'
    temporary.write_bytes(data)
    temporary.replace(ROOT / 'easylist.txt')
    metadata = {'url': URL, 'sha256': hashlib.sha256(data).hexdigest(),
                'bytes': len(data)}
    (ROOT / 'snapshot.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(metadata))


if __name__ == '__main__':
    main()
