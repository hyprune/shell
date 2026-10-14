"""IPC 0.27: workspace screens. Director > Objects > Placed shows a screen's workspace (the
Workspace section: a number, Next free, None), the Placed row tags it (WS 25) and catalog cards
name it (Screen 16:9). The pure helpers in qml/Objects.js are tested with node.

Wire checks run against the vendored 0.27 pin; 0.26 must refuse the new shapes."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bridge'))
from client import capabilities  # noqa: E402
from launch import shell_actions  # noqa: E402
from protocol import VALIDATORS, SUPPORTED_PROTOCOLS, frame  # noqa: E402

OBJECTS = (ROOT / 'qml/Objects.js').read_text()
V27 = VALIDATORS['0.27']
V26 = VALIDATORS['0.26']
SCREEN = 'user/workspace-screen-wall-16x9'


def js(expression):
    return json.loads(subprocess.check_output(['node', '-e', OBJECTS + '\nconsole.log(JSON.stringify(' + expression + '));'], text=True))


def call(name, *args):
    return js(name + '(' + ', '.join(json.dumps(a) for a in args) + ')')


def request(method, params, rid='r'):
    return {'jsonrpc': '2.0', 'id': rid, 'method': method, 'params': params}


def instance(**over):
    return {'id': 'u-7c2e91', 'source': 'user', 'ref': SCREEN, 'name': 'Wall screen 16:9', 'areaId': '', 'scale': 1,
            'pose': {'position': [0, 1.5, -4], 'rotation': [0, 0, 0, 1]}, 'state': 'active', 'movable': True, 'locked': False,
            'rule': None, 'path': None, 'activity': None, 'seat': None, 'character': False, 'accent': None,
            'screen': {'workspace': 25, 'home': 'screen-u-7c2e91', 'aspect': '16:9', 'size': [3.2, 1.8]}, **over}


class Pin(unittest.TestCase):
    def test_vendored_pin(self):
        source = json.loads((ROOT / 'protocol/v0.27/SOURCE.json').read_text())
        self.assertEqual(source['protocol'], '0.27')
        self.assertEqual(hashlib.sha256((ROOT / 'protocol/v0.27/ipc.schema.json').read_bytes()).hexdigest(), source['sha256'])
        self.assertIn('0.27', SUPPORTED_PROTOCOLS)
        self.assertEqual(V27.schema['$defs']['session.hello.result']['properties']['protocol']['const'], '0.27')

    def test_no_new_grant_or_method(self):
        frame(request('session.hello', {'protocols': ['0.27'], 'client': {'id': 'com.hyprune.shell', 'name': 'Hyprune shell'},
                                        'capabilities': capabilities('0.27')}), V27)
        self.assertEqual(capabilities('0.27'), capabilities('0.26'))
        self.assertEqual(shell_actions('0.27'), shell_actions('0.26'))

    def test_workspace_requests_validate_on_027_only(self):
        for value in [25, 'next-free', None]:
            made = call('workspaceRequest', instance(), value)
            frame(request(made['method'], made['params']), V27)
            with self.assertRaises(Exception):
                frame(request(made['method'], made['params']), V26)


class Section(unittest.TestCase):
    def test_workspace_section_for_screens_only(self):
        sections = {s['id']: s for s in call('panelSections', instance())}
        screen = sections['screen']
        self.assertEqual((screen['title'], screen['visible'], screen['editable'], screen['workspace'], screen['home'], screen['aspect']),
                         ('Workspace', True, True, 25, 'screen-u-7c2e91', '16:9'))
        self.assertEqual(screen['line'], 'Shows workspace 25')
        plain = {s['id']: s for s in call('panelSections', instance(screen=None))}
        self.assertFalse(plain['screen']['visible'])
        older = {s['id']: s for s in call('panelSections', {k: v for k, v in instance().items() if k != 'screen'})}
        self.assertFalse(older['screen']['visible'])  # an IPC 0.26 instance has no screen
        locked = {s['id']: s for s in call('panelSections', instance(locked=True))}
        self.assertFalse(locked['screen']['editable'])
        self.assertIn('unlock', locked['screen']['note'].lower())

    def test_lines_and_tags(self):
        self.assertEqual(call('screenLine', {'workspace': None, 'home': None, 'aspect': '21:9', 'size': [4.2, 1.8]}), 'Shows no workspace')
        self.assertIn('another home', call('screenLine', {'workspace': 21, 'home': None, 'aspect': '16:9', 'size': [3.2, 1.8]}))
        self.assertEqual(call('screenTag', instance()), 'WS 25')
        self.assertEqual(call('screenTag', instance(screen={'workspace': None, 'home': None, 'aspect': '16:9', 'size': [3.2, 1.8]})), 'SCREEN')
        self.assertEqual(call('screenTag', instance(screen=None)), '')
        self.assertEqual(call('screenChip', {'screen': {'aspect': '21:9', 'size': [4.2, 1.8], 'mountType': 'hanging-wall'}}), 'Screen 21:9')
        self.assertEqual(call('screenChip', {'screen': None}), '')

    def test_workspace_request(self):
        self.assertEqual(call('workspaceRequest', instance(), '23'), {'method': 'objects.configure', 'params': {'id': 'u-7c2e91', 'patch': {'workspace': 23}}})
        self.assertEqual(call('workspaceRequest', instance(), 'next-free')['params']['patch'], {'workspace': 'next-free'})
        self.assertEqual(call('workspaceRequest', instance(), None)['params']['patch'], {'workspace': None})
        for bad in ['0', '10000', '2.5', 'abc', '']:
            self.assertIn('error', call('workspaceRequest', instance(), bad), bad)
        self.assertIn('error', call('workspaceRequest', instance(screen=None), '23'))

    def test_feedback_and_rules(self):
        self.assertEqual(call('resultText', 'objects.configure', {'id': 'u', 'patch': {'workspace': 26}}), 'The screen shows workspace 26.')
        self.assertEqual(call('resultText', 'objects.configure', {'id': 'u', 'patch': {'workspace': None}}), 'The screen shows no workspace.')
        self.assertEqual(call('resultText', 'objects.configure', {'id': 'u', 'patch': {'locked': True}}), 'Locked.')
        toast = call('errorToast', 'objects.configure', {'message': 'workspace 21 is the home of sun-court', 'rule': 'workspace.taken'}, '')
        self.assertEqual(toast['detail'], 'Rule: another home already shows that workspace')


if __name__ == '__main__':
    unittest.main()
