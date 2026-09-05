#!/usr/bin/env python3
# Copyright 2026 The Joao Browser Authors
# Use of this source code is governed by a BSD-style license in LICENSE.
"""Test release stamping without changing a remote repository."""

import base64
from datetime import datetime, timezone
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import stamp_version


NOW = datetime(2026, 9, 5, 15, 0, 0, tzinfo=timezone.utc)


class Repository:
    def __init__(self, conflict=False, forbidden=False, tag_conflict=False):
        self.calls = []
        self.conflict = conflict
        self.forbidden = forbidden
        self.tag_conflict = tag_conflict
        self.parent = 'original'
        self.version = '20260905145959'
        self.commits = 0

    def __call__(self, method, path, data=None):
        self.calls.append((method, path, data))
        if path == '/git/ref/heads/main':
            return {'object': {'sha': self.parent}}
        if path.startswith('/git/commits/'):
            return {'tree': {'sha': 'tree-' + self.parent}}
        if path.startswith('/contents/'):
            return {'content': base64.b64encode(self.version.encode()).decode()}
        if path == '/git/blobs':
            return {'sha': 'blob'}
        if path == '/git/trees':
            return {'sha': 'new-tree'}
        if path == '/git/commits':
            self.commits += 1
            return {'sha': 'new-' + str(self.commits)}
        if path == '/git/refs/heads/main':
            if self.forbidden:
                raise HTTPError(path, 403, 'Forbidden', {}, None)
            if self.conflict:
                self.conflict = False
                self.parent = 'concurrent'
                self.version = '20260905150000'
                raise HTTPError(path, 422, 'Not fast forward', {}, None)
            self.parent = data['sha']
            return {}
        if path == '/git/refs':
            if self.tag_conflict:
                raise HTTPError(path, 422, 'Exists', {}, None)
            return {}
        if path.startswith('/git/ref/tags/'):
            return {'object': {'sha': 'unrelated'}}
        if path == '/actions/workflows/release.yml/dispatches':
            return {}
        raise AssertionError((method, path, data))


class StampTest(unittest.TestCase):
    def test_dispatch_accepts_empty_204_response(self):
        response = MagicMock()
        response.status = 204
        response.__enter__.return_value = response
        with patch('stamp_version.urlopen', return_value=response):
            self.assertEqual(stamp_version.GitHub('owner/repo', 'test-token')(
                'POST', '/actions/workflows/release.yml/dispatches',
                {'ref': 'joao-v20260905150000'}), {})

    def test_initial_and_monotonic_timestamp(self):
        self.assertEqual(stamp_version.next_version('', NOW), '20260905150000')
        self.assertEqual(stamp_version.next_version('20260905150000', NOW),
                         '20260905150001')
        self.assertEqual(stamp_version.next_version('20260905235959', NOW),
                         '20260906000000')

    def test_commit_preserves_tree_and_tags_exact_commit(self):
        api = Repository()
        result = stamp_version.stamp(api, now=lambda: NOW)
        self.assertEqual(result, {'version': '20260905150000',
                                  'tag': 'joao-v20260905150000', 'commit': 'new-1'})
        tree = next(data for _, path, data in api.calls if path == '/git/trees')
        self.assertEqual(tree['base_tree'], 'tree-original')
        self.assertEqual([entry['path'] for entry in tree['tree']], ['version.txt'])
        commit = next(data for _, path, data in api.calls if path == '/git/commits')
        self.assertEqual(commit['parents'], ['original'])
        self.assertIn('[skip ci]', commit['message'])
        self.assertIn(('PATCH', '/git/refs/heads/main',
                       {'sha': 'new-1', 'force': False}), api.calls)
        self.assertEqual(api.calls[-2], ('POST', '/git/refs', {
            'ref': 'refs/tags/joao-v20260905150000', 'sha': 'new-1'}))
        dispatches = [call for call in api.calls if call[1].endswith('/dispatches')]
        self.assertEqual(dispatches, [('POST', '/actions/workflows/release.yml/dispatches', {
            'ref': 'joao-v20260905150000', 'inputs': {
                'release_tag': 'joao-v20260905150000', 'release_commit': 'new-1'}})])
        self.assertEqual(api.calls[-1], dispatches[0])

    def test_race_rebases_on_latest_main_without_force(self):
        api = Repository(conflict=True)
        result = stamp_version.stamp(api, now=lambda: NOW, sleep=lambda _: None)
        self.assertEqual(result['version'], '20260905150001')
        commits = [data for _, path, data in api.calls if path == '/git/commits']
        self.assertEqual(commits[-1]['parents'], ['concurrent'])
        self.assertEqual(result['commit'], 'new-2')
        self.assertEqual(sum(path.endswith('/dispatches') for _, path, _ in api.calls), 1)

    def test_permission_failure_does_not_tag(self):
        api = Repository(forbidden=True)
        with self.assertRaises(HTTPError):
            stamp_version.stamp(api, now=lambda: NOW)
        self.assertFalse(any(path == '/git/refs' for _, path, _ in api.calls))
        self.assertFalse(any(path.endswith('/dispatches') for _, path, _ in api.calls))

    def test_existing_tag_is_never_replaced(self):
        api = Repository(tag_conflict=True)
        with self.assertRaisesRegex(RuntimeError, 'different commit'):
            stamp_version.stamp(api, now=lambda: NOW)
        self.assertFalse(any(method == 'PATCH' and 'tags' in path
                             for method, path, _ in api.calls))
        self.assertFalse(any(path.endswith('/dispatches') for _, path, _ in api.calls))


if __name__ == '__main__':
    unittest.main()
