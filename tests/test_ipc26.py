"""IPC 0.26: the debug tool (tool 9 and editor.debugTool), the companion's pace (Settings >
Companion Walk / Run) and the whole pocket list (more than 16 windows in Director > Surfaces).

Wire checks run against the vendored 0.26 pin; 0.25 must refuse the new shapes."""
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

COMPANION_JS = (ROOT / 'qml/Companion.js').read_text()
DIRECTOR_JS = (ROOT / 'qml/DirectorModel.js').read_text()
V26 = VALIDATORS['0.26']
V25 = VALIDATORS['0.25']
ASH = 'library/io.github.rick-the-alien.drunk-ash@0.1.0/drunk-ash'


def js(source, expression):
    return json.loads(subprocess.check_output(['node', '-e', source + '\nconsole.log(JSON.stringify(' + expression + '));'], text=True))


def call(source, name, *args):
    return js(source, name + '(' + ', '.join(json.dumps(a) for a in args) + ')')


def request(method, params, rid='r'):
    return {'jsonrpc': '2.0', 'id': rid, 'method': method, 'params': params}


def definition(validator, name):
    return validator.evolve(schema={'$ref': validator.schema['$id'] + '#/$defs/' + name})


def companion(**over):
    return {'ref': ASH, 'name': 'Drunk Ash', 'state': 'active', 'reason': None, 'mode': 'follow', 'path': None,
            'activity': 'following', 'position': [3.2, 0, -4.1], 'carried': False, 'pace': 'walk', **over}


def debug_tool(**over):
    return {'layer': 'collision', 'label': 'Collision & backstops', 'index': 2, 'count': 10,
            'legend': [{'label': 'floor', 'colour': [0.3, 0.9, 0.4]}, {'label': 'wall', 'colour': [0.25, 0.78, 0.85]}],
            'card': None, **over}


def pocket(n):
    return {'count': n, 'windows': [{'surfaceId': f'surface-{i}', 'title': f'Window {i}', 'appClass': 'foot', 'logicalSize': [1280, 720]}
                                    for i in range(n)],
            'selectedId': 'surface-0' if n else None, 'preview': False, 'objects': []}


class Pin(unittest.TestCase):
    def test_vendored_pin(self):
        source = json.loads((ROOT / 'protocol/v0.26/SOURCE.json').read_text())
        self.assertEqual(source['protocol'], '0.26')
        self.assertEqual(hashlib.sha256((ROOT / 'protocol/v0.26/ipc.schema.json').read_bytes()).hexdigest(), source['sha256'])
        self.assertIn('0.26', SUPPORTED_PROTOCOLS)
        self.assertEqual(V26.schema['$defs']['session.hello.result']['properties']['protocol']['const'], '0.26')

    def test_no_new_grant_or_method(self):
        frame(request('session.hello', {'protocols': ['0.26'], 'client': {'id': 'com.hyprune.shell', 'name': 'Hyprune shell'},
                                        'capabilities': capabilities('0.26')}), V26)
        self.assertEqual(capabilities('0.26'), capabilities('0.25'))
        self.assertEqual(shell_actions('0.26'), shell_actions('0.25'))


class Pace(unittest.TestCase):
    def test_pace_params(self):
        self.assertEqual(js(COMPANION_JS, 'PACES'), [{'id': 'walk', 'label': 'Walk'}, {'id': 'run', 'label': 'Run'}])
        self.assertEqual(call(COMPANION_JS, 'paceParams', companion(), 'run'), {'mode': 'follow', 'pace': 'run'})
        self.assertEqual(call(COMPANION_JS, 'paceParams', companion(mode='stay', pace='run'), 'walk'), {'mode': 'stay', 'pace': 'walk'})
        for c, pace in [(companion(mode='route', path='user/path-3'), 'run'), (companion(ref=None, state='none'), 'run'),
                        (None, 'walk'), (companion(), 'sprint')]:
            self.assertIsNone(call(COMPANION_JS, 'paceParams', c, pace), (c, pace))

    def test_requests(self):
        for c in [companion(), companion(mode='stay')]:
            for pace in ['walk', 'run']:
                message = request('companion.mode', call(COMPANION_JS, 'paceParams', c, pace))
                frame(message, V26)
                with self.assertRaises(Exception):
                    V25.validate(message)
        frame(request('companion.mode', {'mode': 'follow'}), V26)  # Follow / Stay alone still works
        for params in [{'pace': 'run'}, {'mode': 'route', 'pace': 'run'}, {'mode': 'follow', 'pace': 'jog'}]:
            with self.assertRaises(Exception, msg=params):
                frame(request('companion.mode', params), V26)

    def test_state(self):
        state = definition(V26, 'companionState')
        for c in [companion(), companion(pace='run'), companion(mode='route', path='user/path-3', activity='walking', pace='run')]:
            state.validate(c)
        without = companion()
        del without['pace']
        for c in [without, companion(pace='sprint')]:
            with self.assertRaises(Exception, msg=c):
                state.validate(c)
        definition(V25, 'companionState').validate(without)

    def test_settings_row(self):
        picker = (ROOT / 'qml/components/CompanionSettings.qml').read_text()
        for text in ["objectName: 'companionPace'", 'Companion.PACES', 'ShellState.companionPace(id)', 'ShellState.companionPaceSupported']:
            self.assertIn(text, picker)
        shell = (ROOT / 'qml/ShellState.qml').read_text()
        self.assertIn("supportsProtocol(26) && available('companion.mode')", shell)
        self.assertIn('Companion.paceParams(companionState, pace)', shell)


class DebugTool(unittest.TestCase):
    def test_debug_tool_shape(self):
        tool = definition(V26, 'debugTool')
        for t in [debug_tool(), debug_tool(card=['wall-12', 'Collision wall']), debug_tool(layer='steering', index=9, legend=[])]:
            tool.validate(t)
        for t in [debug_tool(layer='wiring'), debug_tool(count=0), debug_tool(extra=1)]:
            with self.assertRaises(Exception, msg=t):
                tool.validate(t)
        self.assertNotIn('debugTool', V25.schema['$defs'])

    def test_tool_nine_on_the_wire(self):
        pose = {'subscriptionId': 'hud', 'sessionId': 's', 'revision': 2, 'monotonicMs': 10, 'outputId': 'output-1', 'worldId': 'w',
                'worldName': 'W', 'position': [0, 0, 0], 'heading': 0, 'pitch': 0, 'zone': None, 'tool': 9, 'subtype': 'collision'}
        V26.validate({'jsonrpc': '2.0', 'method': 'hud.pose', 'params': pose})
        with self.assertRaises(Exception):
            V25.validate({'jsonrpc': '2.0', 'method': 'hud.pose', 'params': pose})
        world = V26.schema['$defs']['inputConfig']['properties']['modes']['properties']['world']
        self.assertIn('tool9', world['required'])

    def test_hud_names_the_layer(self):
        hud = (ROOT / 'qml/HudData.qml').read_text()
        self.assertIn("editor.tool === 9", hud)
        self.assertIn("tool === 9 ? 'Debug'", hud)
        self.assertIn("'LAYER '+(debugTool.index+1)+'/'+debugTool.count", hud)
        deck = (ROOT / 'qml/components/ToolDeck.qml').read_text()
        self.assertIn('HudData.debugLayerText', deck)
        self.assertIn('HudData.debugTool.label.toUpperCase()', deck)
        self.assertIn('root.tool === 9', (ROOT / 'qml/components/ToolGlyph.qml').read_text())
        self.assertIn('function actionLabel(action)', (ROOT / 'qml/components/DirectorSettings.qml').read_text())


class Pocket(unittest.TestCase):
    def test_whole_pocket_listed(self):
        unplaced = definition(V26, 'unplaced')
        unplaced.validate(pocket(40))
        unplaced.validate(pocket(128))
        with self.assertRaises(Exception):
            definition(V25, 'unplaced').validate(pocket(17))
        state = {'surfaces': [], 'editor': {'unplaced': pocket(40)}}
        self.assertEqual(len(call(DIRECTOR_JS, 'pocketIds', state)), 40)
        cards = call(DIRECTOR_JS, 'surfaceCards', state)
        self.assertEqual(len(cards['pocketed']), 40)
        self.assertEqual(cards['pocketed'][39]['id'], 'surface-39')


if __name__ == '__main__':
    unittest.main()
