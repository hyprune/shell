"""IPC 0.32 (draft, RFC-0015 amendment): Director > Library over core. The shell asks for
content.control, may send the content, sources and registry methods, and reads state.content.

Wire checks run against the vendored 0.32 pin; 0.31 must refuse the new shapes."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bridge'))
from client import capabilities  # noqa: E402
from protocol import VALIDATORS, SUPPORTED_PROTOCOLS  # noqa: E402
from launch import shell_actions, CONTENT_ACTIONS, ECHO_ACTIONS  # noqa: E402

V32, V31 = VALIDATORS['0.32'], VALIDATORS['0.31']
SOURCE = {'id': 'official', 'kind': 'official', 'label': 'Official', 'display': 'Official', 'url': 'http://127.0.0.1:8000/index/official.json',
          'enabled': True, 'builtin': True, 'system': False, 'lastRefresh': None, 'serial': None, 'entries': 0, 'error': None}
JOB = {'jobId': 'j-0a0b0c0d', 'kind': 'install', 'stage': 'confirm', 'target': 'com.hyprune.companions', 'plan': None,
       'progress': None, 'error': None, 'result': None, 'created': '2026-10-16T08:00:00Z'}


def delta(content):
    return {'jsonrpc': '2.0', 'method': 'state.delta', 'params': {'subscriptionId': 's', 'sessionId': 's', 'baseRevision': 0, 'revision': 1,
                                                                  'changes': {'content': content}}}


class Ipc32(unittest.TestCase):
    def test_pin(self):
        source = json.loads((ROOT / 'protocol/v0.32/SOURCE.json').read_text())
        self.assertEqual(source['protocol'], '0.32')
        self.assertEqual(hashlib.sha256((ROOT / 'protocol/v0.32/ipc.schema.json').read_bytes()).hexdigest(), source['sha256'])
        self.assertIn('0.32', SUPPORTED_PROTOCOLS)

    def test_grant_and_actions(self):
        self.assertIn('content.control', capabilities('0.32'))
        self.assertNotIn('content.control', capabilities('0.31'))
        self.assertTrue(set(CONTENT_ACTIONS) <= set(shell_actions('0.32')))
        self.assertFalse(set(CONTENT_ACTIONS) & set(shell_actions('0.31')))
        self.assertTrue(set(CONTENT_ACTIONS) <= set(ECHO_ACTIONS), 'refusals echo their params')

    def test_state_content(self):
        content = {'revision': 3, 'installs': [], 'updates': 0, 'sources': [SOURCE], 'jobs': [JOB]}
        self.assertTrue(V32.is_valid(delta(content)))
        self.assertFalse(V31.is_valid(delta(content)))
        self.assertFalse(V32.is_valid(delta({**content, 'jobs': [{**JOB, 'stage': 'pending'}]})))
        request = {'jsonrpc': '2.0', 'id': '1', 'method': 'content.install', 'params': {'source': {'entry': {'sourceId': 'official', 'id': 'com.hyprune.companions'}}}}
        self.assertTrue(V32.is_valid(request))
        self.assertFalse(V31.is_valid(request))


if __name__ == '__main__':
    unittest.main()
