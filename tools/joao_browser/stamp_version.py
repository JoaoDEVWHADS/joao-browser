#!/usr/bin/env python3
# Copyright 2026 The Joao Browser Authors
# Use of this source code is governed by a BSD-style license in LICENSE.
"""Commit a UTC release version and tag through GitHub's API, without checkout."""

import base64
from datetime import datetime, timedelta, timezone
import json
import os
import re
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class GitHub:
    def __init__(self, repository, token):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
            raise ValueError('Invalid repository name')
        self.base = 'https://api.github.com/repos/' + repository
        self.token = token

    def __call__(self, method, path, data=None):
        request = Request(self.base + path, method=method,
                          data=json.dumps(data).encode() if data is not None else None,
                          headers={'Authorization': 'Bearer ' + self.token,
                                   'Accept': 'application/vnd.github+json',
                                   'X-GitHub-Api-Version': '2022-11-28',
                                   'User-Agent': 'JoaoBrowserRelease',
                                   'Content-Type': 'application/json'})
        with urlopen(request, timeout=60) as response:
            if response.status == 204:
                return {}
            return json.load(response)


def next_version(previous, now):
    candidate = now.astimezone(timezone.utc).replace(microsecond=0)
    if re.fullmatch(r'[0-9]{14}', previous):
        previous_time = datetime.strptime(previous, '%Y%m%d%H%M%S').replace(
            tzinfo=timezone.utc)
        candidate = max(candidate, previous_time + timedelta(seconds=1))
    return candidate.strftime('%Y%m%d%H%M%S')


def stamp(api, now=lambda: datetime.now(timezone.utc), sleep=time.sleep):
    for attempt in range(8):
        parent = api('GET', '/git/ref/heads/main')['object']['sha']
        commit = api('GET', '/git/commits/' + parent)
        try:
            existing = api('GET', '/contents/version.txt?ref=' + parent)
            previous = base64.b64decode(existing['content']).decode('ascii').strip()
        except HTTPError as error:
            if error.code != 404:
                raise
            previous = ''
        version = next_version(previous, now())
        blob = api('POST', '/git/blobs', {'content': version + '\n', 'encoding': 'utf-8'})
        tree = api('POST', '/git/trees', {
            'base_tree': commit['tree']['sha'],
            'tree': [{'path': 'version.txt', 'mode': '100644', 'type': 'blob',
                      'sha': blob['sha']}]})
        created = api('POST', '/git/commits', {
            'message': 'Stamp Joao Browser ' + version + ' [skip ci]',
            'tree': tree['sha'], 'parents': [parent],
            'author': {'name': 'github-actions[bot]',
                       'email': '41898282+github-actions[bot]@users.noreply.github.com'}})
        sha = created['sha']
        try:
            # No force: a concurrently updated main cannot be overwritten.
            api('PATCH', '/git/refs/heads/main', {'sha': sha, 'force': False})
        except HTTPError as error:
            if error.code not in (409, 422):
                raise
            sleep(min(attempt + 1, 5))
            continue
        tag = 'joao-v' + version
        try:
            api('POST', '/git/refs', {'ref': 'refs/tags/' + tag, 'sha': sha})
        except HTTPError as error:
            if error.code != 422:
                raise
            # Accept only an identical tag, never replace an existing release.
            if api('GET', '/git/ref/tags/' + tag)['object']['sha'] != sha:
                raise RuntimeError('Release tag already names a different commit') from error
        # GITHUB_TOKEN pushes do not start workflows. An explicit dispatch does,
        # and the new tagged build run cancels this stamping run through concurrency.
        api('POST', '/actions/workflows/release.yml/dispatches', {
            'ref': tag, 'inputs': {'release_tag': tag, 'release_commit': sha}})
        return {'version': version, 'tag': tag, 'commit': sha}
    raise RuntimeError('Could not advance main after eight attempts; check branch permissions/races')


def main():
    result = stamp(GitHub(os.environ['GH_REPO'], os.environ['GH_TOKEN']))
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
        for name, value in result.items():
            output.write(name + '=' + value + '\n')
    print('Stamped ' + result['tag'] + ' at ' + result['commit'])


if __name__ == '__main__':
    main()
