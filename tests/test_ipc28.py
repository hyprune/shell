"""IPC 0.28 (draft, the shared clip library): character styles (spawn, rebind and the
companion's Settings rows), the catalog's motion and a companion's dances (the E menu's
Dance list sends interaction.choose with an option).

Wire checks run against the vendored 0.28 pin; 0.27 must refuse the new shapes."""
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

NPCS_JS = (ROOT / 'qml/Npcs.js').read_text()
COMPANION_JS = (ROOT / 'qml/Companion.js').read_text()
V28 = VALIDATORS['0.28']
V27 = VALIDATORS['0.27']
MUSE = 'library/com.hyprune.companions@0.1.0/neon-cyber-muse'
MOTION = {'skeleton': 'mixamo-v1', 'styles': {'walk': ['confident', 'stroll'], 'run': ['fast'], 'idle': ['calm-2']},
          'dances': ['shimmy', 'hip-hop-2'], 'packs': ['starter-motion', 'companion-moves']}


def js(source, expression):
    return json.loads(subprocess.check_output(['node', '-e', source + '\nconsole.log(JSON.stringify(' + expression + '));'], text=True))


def call(source, name, *args):
    return js(source, name + '(' + ', '.join(json.dumps(a) for a in args) + ')')


def request(method, params, rid='r'):
    return {'jsonrpc': '2.0', 'id': rid, 'method': method, 'params': params}


def companion(**over):
    return {'ref': MUSE, 'name': 'Muse', 'state': 'active', 'reason': None, 'mode': 'follow', 'path': None, 'activity': 'following',
            'position': [3.2, 0, -4.1], 'carried': False, 'pace': 'walk', 'style': None, 'dance': None, **over}


class Pin(unittest.TestCase):
    def test_vendored_pin(self):
        source = json.loads((ROOT / 'protocol/v0.28/SOURCE.json').read_text())
        self.assertEqual(source['protocol'], '0.28')
        self.assertEqual(hashlib.sha256((ROOT / 'protocol/v0.28/ipc.schema.json').read_bytes()).hexdigest(), source['sha256'])
        self.assertIn('0.28', SUPPORTED_PROTOCOLS)
        self.assertEqual(V28.schema['$defs']['session.hello.result']['properties']['protocol']['const'], '0.28')

    def test_no_new_grant_or_method(self):
        frame(request('session.hello', {'protocols': ['0.28'], 'client': {'id': 'com.hyprune.shell', 'name': 'Hyprune shell'},
                                        'capabilities': capabilities('0.28')}), V28)
        self.assertEqual(capabilities('0.28'), capabilities('0.27'))
        self.assertEqual(shell_actions('0.28'), shell_actions('0.27'))


class Styles(unittest.TestCase):
    def test_labels_and_choices(self):
        self.assertEqual(call(NPCS_JS, 'styleLabel', 'calm-2'), 'Calm 2')
        self.assertEqual(call(NPCS_JS, 'styleLabel', 'hip-hop'), 'Hip hop')
        self.assertEqual(call(NPCS_JS, 'styleChoices', MOTION, 'walk'),
                         [{'id': '', 'label': 'Plain'}, {'id': 'confident', 'label': 'Confident'}, {'id': 'stroll', 'label': 'Stroll'}])
        self.assertEqual(call(NPCS_JS, 'styleChoices', None, 'walk'), [{'id': '', 'label': 'Plain'}])
        self.assertTrue(call(NPCS_JS, 'hasStyles', MOTION))
        self.assertFalse(call(NPCS_JS, 'hasStyles', {'styles': {'walk': [], 'run': [], 'idle': []}}))
        self.assertFalse(call(NPCS_JS, 'hasStyles', None))

    def test_spawn_and_bind_params(self):
        style = {'walk': 'confident', 'run': '', 'idle': 'calm-2'}
        spawn = call(NPCS_JS, 'spawnRequest', MUSE, {'kind': 'stand'}, {'speed': 1, 'style': style})
        self.assertEqual(spawn, {'method': 'npcs.spawn', 'params': {'ref': MUSE, 'style': {'walk': 'confident', 'idle': 'calm-2'}}})
        frame(request(spawn['method'], spawn['params']), V28)
        with self.assertRaises(Exception):
            frame(request(spawn['method'], spawn['params']), V27)
        # All plain: a spawn leaves the style out; a rebind clears it (null).
        plain = {'walk': '', 'run': '', 'idle': ''}
        self.assertNotIn('style', call(NPCS_JS, 'spawnRequest', MUSE, {'kind': 'stand'}, {'style': plain})['params'])
        user = {'id': 'user-1', 'source': 'user', 'path': None}
        bind = call(NPCS_JS, 'bindRequest', user, {'kind': 'settings'}, {'style': plain, 'clearStyle': True})
        self.assertEqual(bind, {'method': 'npcs.bind', 'params': {'id': 'user-1', 'style': None}})
        frame(request(bind['method'], bind['params']), V28)
        # Without styles (an older core or no motion) nothing changes.
        self.assertIsNone(call(NPCS_JS, 'bindRequest', user, {'kind': 'settings'}, {'speed': 1}))
        # paths.draw spawn takes no style.
        draw = call(NPCS_JS, 'spawnRequest', MUSE, {'kind': 'draw'}, {'style': style})
        self.assertNotIn('style', draw['params']['spawn'])
        frame(request(draw['method'], draw['params']), V28)

    def test_companion_style(self):
        self.assertEqual(call(COMPANION_JS, 'styleParams', companion(), 'walk', 'confident'), {'mode': 'follow', 'style': {'walk': 'confident'}})
        c = companion(mode='stay', style={'walk': 'confident', 'idle': 'calm-2'})
        self.assertEqual(call(COMPANION_JS, 'styleParams', c, 'walk', ''), {'mode': 'stay', 'style': {'idle': 'calm-2'}})
        self.assertEqual(call(COMPANION_JS, 'styleParams', companion(style={'run': 'fast'}), 'run', ''), {'mode': 'follow', 'style': None})
        for args in [(companion(mode='route', path='user/path-1'), 'walk', 'stroll'), (companion(), 'walk', ''), (companion(), 'sit', 'calm'),
                     (None, 'walk', 'stroll')]:
            self.assertIsNone(call(COMPANION_JS, 'styleParams', *args), args)
        for params in [{'mode': 'follow', 'style': {'walk': 'confident'}}, {'mode': 'stay', 'style': None}]:
            frame(request('companion.mode', params), V28)
            with self.assertRaises(Exception):
                frame(request('companion.mode', params), V27)
        self.assertEqual(js(COMPANION_JS, "ACTIVITIES.dancing"), 'dancing')


class Dance(unittest.TestCase):
    INTERACTIONS = [{'id': 'talk', 'label': 'Talk', 'type': 'say', 'options': None},
                    {'id': 'dance', 'label': 'Dance', 'type': 'dance', 'options': [{'id': 'shimmy', 'label': 'Shimmy'},
                                                                                 {'id': 'hip-hop-2', 'label': 'Hip hop 2'}]}]

    def test_options_and_items(self):
        self.assertEqual(call(NPCS_JS, 'danceOptions', self.INTERACTIONS, 'dance'), self.INTERACTIONS[1]['options'])
        self.assertIsNone(call(NPCS_JS, 'danceOptions', self.INTERACTIONS, 'talk'))
        self.assertIsNone(call(NPCS_JS, 'danceOptions', None, 'dance'))
        items = call(NPCS_JS, 'danceItems', self.INTERACTIONS[1]['options'])
        self.assertEqual(items, [{'id': '', 'label': 'Any dance', 'key': '1'}, {'id': 'shimmy', 'label': 'Shimmy', 'key': '2'},
                                 {'id': 'hip-hop-2', 'label': 'Hip hop 2', 'key': '3'}])
        many = call(NPCS_JS, 'danceItems', [{'id': f'd{i}', 'label': f'D{i}'} for i in range(20)])
        self.assertEqual(len(many), 17)
        self.assertEqual([i['key'] for i in many[8:10]], ['9', ''])

    def test_choose_params(self):
        choose = {'objectId': 'companion', 'type': 'choose'}
        chosen = call(NPCS_JS, 'chooseParams', choose, 'dance', 'shimmy')
        self.assertEqual(chosen, {'objectId': 'companion', 'interactionId': 'dance', 'option': 'shimmy'})
        frame(request('interaction.choose', chosen), V28)
        with self.assertRaises(Exception):
            frame(request('interaction.choose', chosen), V27)
        self.assertEqual(call(NPCS_JS, 'chooseParams', choose, 'dance', ''), {'objectId': 'companion', 'interactionId': 'dance'})
        self.assertEqual(call(NPCS_JS, 'chooseParams', choose, None, 'shimmy'), {'objectId': 'companion', 'interactionId': None})


if __name__ == '__main__':
    unittest.main()
