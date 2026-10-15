"""IPC 0.25 (draft, RFC-0010 companions amendment): the companion actions (no new grant), the
companion state key and catalog capability, the Settings > Companion picker wiring, and the
pure helpers in qml/Companion.js (node).

Wire checks run against the vendored 0.25 pin; 0.24 must refuse the new shapes."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bridge'))
from client import capabilities  # noqa: E402
from launch import COMPANION_ACTIONS, ECHO_ACTIONS, shell_actions  # noqa: E402
from protocol import VALIDATORS, SUPPORTED_PROTOCOLS, frame, validate_response  # noqa: E402

COMPANION_JS = (ROOT / 'qml/Companion.js').read_text()
OLDER = [v for v in SUPPORTED_PROTOCOLS if int(v.split('.')[1]) < 25]
PREVIOUS = OLDER[-1]
V25 = VALIDATORS['0.25']
ASH = 'library/io.github.rick-the-alien.drunk-ash@0.1.0/drunk-ash'


def js(expression):
    return json.loads(subprocess.check_output(['node', '-e', COMPANION_JS + '\nconsole.log(JSON.stringify(' + expression + '));'], text=True))


def call(name, *args):
    return js(name + '(' + ', '.join(json.dumps(a) for a in args) + ')')


def request(method, params, rid='r'):
    return {'jsonrpc': '2.0', 'id': rid, 'method': method, 'params': params}


def definition(validator, name):
    return validator.evolve(schema={'$ref': validator.schema['$id'] + '#/$defs/' + name})


def companion(**over):
    return {'ref': ASH, 'name': 'Drunk Ash', 'state': 'active', 'reason': None, 'mode': 'follow', 'path': None,
            'activity': 'following', 'position': [3.2, 0, -4.1], 'carried': False, **over}


NONE = companion(ref=None, name=None, state='none', activity=None, position=None)


def entry(ref, name, source='library', capable=True, reason=None, character=True, thumbnail=None):
    return {'ref': ref, 'name': name, 'source': source, 'thumbnail': thumbnail, 'traits': ['character'] if character else ['decorative'],
            'companion': {'capable': capable, 'name': name, 'reason': reason} if character else None}


class Pin(unittest.TestCase):
    def test_vendored_pin(self):
        source = json.loads((ROOT / 'protocol/v0.25/SOURCE.json').read_text())
        self.assertEqual(source['protocol'], '0.25')
        self.assertEqual(hashlib.sha256((ROOT / 'protocol/v0.25/ipc.schema.json').read_bytes()).hexdigest(), source['sha256'])
        self.assertIn('0.25', SUPPORTED_PROTOCOLS)
        self.assertEqual(V25.schema['$defs']['session.hello.result']['properties']['protocol']['const'], '0.25')


class Grants(unittest.TestCase):
    """0.25 adds no grant: the companion methods use objects.control (requested from 0.22)."""

    def test_hello_validates_and_grants_are_inherited(self):
        frame(request('session.hello', {'protocols': ['0.25'], 'client': {'id': 'com.hyprune.shell', 'name': 'Hyprune shell'},
                                        'capabilities': capabilities('0.25')}), V25)
        self.assertEqual(capabilities('0.25'), capabilities('0.24'))
        self.assertIn('objects.control', capabilities('0.25'))


class Allowlist(unittest.TestCase):
    def test_companion_methods_only_from_0_25(self):
        for version in OLDER + ['0.99']:
            self.assertFalse(set(COMPANION_ACTIONS) & set(shell_actions(version)), version)
        self.assertEqual(set(shell_actions('0.25')) - set(shell_actions(PREVIOUS)), set(COMPANION_ACTIONS))
        self.assertTrue(set(COMPANION_ACTIONS) <= set(ECHO_ACTIONS))

    def test_every_companion_action_is_a_0_25_method(self):
        methods = V25.schema['$defs']['session.hello.result']['properties']['methods']['items']['enum']
        old = VALIDATORS[PREVIOUS].schema['$defs']['session.hello.result']['properties']['methods']['items']['enum']
        self.assertEqual(sorted(set(methods) - set(old)), sorted(COMPANION_ACTIONS))


class Wire(unittest.TestCase):
    def test_requests(self):
        for choice in [ASH, '']:
            made = call('choose', choice)
            message = request(made['method'], made['params'])
            frame(message, V25)
            with self.assertRaises(Exception):
                VALIDATORS[PREVIOUS].validate(message)
        for mode in ['follow', 'stay']:
            frame(request('companion.mode', {'mode': mode}), V25)
        for method, params in [('companion.mode', {'mode': 'route'}), ('companion.set', {}), ('companion.clear', {'ref': ASH})]:
            with self.assertRaises(Exception, msg=(method, params)):
                frame(request(method, params), V25)
        # The reserved id works with the 0.23 methods.
        frame(request('paths.draw', {'use': 'route', 'bind': 'companion'}), V25)
        frame(request('interaction.choose', {'objectId': 'companion', 'interactionId': 'stay'}), V25)

    def test_results(self):
        for method in COMPANION_ACTIONS:
            validate_response({'jsonrpc': '2.0', 'id': 'r', 'result': {'revision': 4}}, method, V25)

    def test_state_and_catalog_shapes(self):
        self.assertIn('companion', V25.schema['$defs']['state']['required'])
        self.assertNotIn('companion', VALIDATORS[PREVIOUS].schema['$defs']['state']['properties'])
        state = definition(V25, 'companionState')
        for c in [companion(), NONE, companion(mode='route', path='user/path-3', activity='walking'), companion(mode='stay', activity='idle'),
                  companion(state='unavailable', reason='not installed', activity=None, position=None), companion(activity='carried', carried=True)]:
            state.validate(c)
        for c in [companion(state='lost'), companion(mode='guide'), companion(extra=1)]:
            with self.assertRaises(Exception, msg=c):
                state.validate(c)
        capability = V25.schema['$defs']['catalogEntry']['properties']['companion']
        self.assertIn('companion', V25.schema['$defs']['catalogEntry']['required'])
        definition(V25, 'catalogEntry').evolve(schema=capability).validate({'capable': False, 'name': 'Tall', 'reason': 'taller than 2.0 m'})


class Picker(unittest.TestCase):
    CATALOG = [entry('library/a@1.0.0/zed', 'Zed'), entry(ASH, 'Drunk Ash', thumbnail='/t/ash.png'),
               entry('user/giant', 'Giant', source='user', capable=False, reason='taller than 2.0 m'),
               entry('package/keeper', 'Keeper', source='package', capable=False, reason='a world resident'),
               entry('library/a@1.0.0/lamp', 'Lamp', character=False)]

    def test_choices(self):
        choices = call('choices', self.CATALOG)
        self.assertEqual([c['name'] for c in choices], ['Drunk Ash', 'Zed', 'Giant'])  # capable first, by name; no residents or props
        self.assertEqual(choices[0], {'ref': ASH, 'name': 'Drunk Ash', 'thumbnail': '/t/ash.png', 'source': 'library', 'capable': True, 'reason': ''})
        self.assertEqual(choices[2]['reason'], 'taller than 2.0 m')
        self.assertEqual(call('choices', None), [])

    def test_choose_and_mode(self):
        self.assertEqual(call('choose', ASH), {'method': 'companion.set', 'params': {'ref': ASH}})
        self.assertEqual(call('choose', ''), {'method': 'companion.clear', 'params': {}})
        self.assertEqual(call('chosen', companion()), ASH)
        self.assertEqual(call('chosen', NONE), '')
        self.assertEqual([call('modeIndex', companion(mode=m)) for m in ['follow', 'stay', 'route']], [0, 1, -1])
        self.assertEqual(call('modeIndex', NONE), -1)

    def test_status(self):
        paths = [{'ref': 'user/path-3', 'name': 'Desk round'}]
        self.assertEqual(call('status', NONE, []), 'No companion')
        self.assertEqual(call('status', None, []), 'No companion')
        self.assertEqual(call('status', companion(), []), 'Drunk Ash is following you')
        self.assertEqual(call('status', companion(activity='running'), []), 'Drunk Ash is catching up')
        self.assertEqual(call('status', companion(mode='stay', activity='idle'), []), 'Drunk Ash stays here')
        self.assertEqual(call('status', companion(mode='route', path='user/path-3'), paths), 'Drunk Ash walks Desk round')
        self.assertEqual(call('status', companion(mode='route', path='user/path-9'), paths), 'Drunk Ash walks path-9')
        self.assertEqual(call('status', companion(state='unavailable', reason='not installed'), []), "Drunk Ash can't come along: not installed")
        self.assertEqual(call('status', companion(state='waiting'), []), 'Drunk Ash is waiting for a free spot')

    def test_settings_section(self):
        settings = (ROOT / 'qml/components/DirectorSettings.qml').read_text()
        self.assertIn("root.category === 'world' && ShellState.companionSupported", settings)
        self.assertIn('CompanionSettings {', settings)
        picker = (ROOT / 'qml/components/CompanionSettings.qml').read_text()
        for name in ['companionSettings', 'companionStatus', 'companionMode', "'companionChoice:'"]:
            self.assertIn(name, picker)
        shell = (ROOT / 'qml/ShellState.qml').read_text()
        self.assertIn("available('companion.set')", shell)
        self.assertIn('supportsProtocol(25)', shell)


if __name__ == '__main__':
    unittest.main()
