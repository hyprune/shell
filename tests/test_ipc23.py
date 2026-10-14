"""IPC 0.23 (RFC-0011 P2): the character, path and interaction actions (no new grant), the npcs
state key, the 0.23 instance / editor path / reticle / graphics shapes, the bridge's choice-list
input and panel interactions, world format 0.9, and the pure helpers in qml/Npcs.js (node).

Wire checks run against the vendored 0.23 pin; 0.22 must refuse the new shapes."""
import asyncio
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bridge'))
from client import Client, CoreError, capabilities  # noqa: E402
from launch import NPC_ACTIONS, OBJECT_ACTIONS, action_event, action_notice, shell_actions  # noqa: E402
from protocol import VALIDATORS, SUPPORTED_PROTOCOLS, WORLD_VALIDATORS, frame, read_frame, validate_response  # noqa: E402

NPCS_JS = (ROOT / 'qml/Npcs.js').read_text()
OLDER = [v for v in SUPPORTED_PROTOCOLS if int(v.split('.')[1]) < 23]
PREVIOUS = OLDER[-1]
V23 = VALIDATORS['0.23']

GUIDE = 'user/guide'
RESIDENT = 'library/com.hyprune.starter@0.1.0/resident-blue'
POSE = {'position': [3.2, 0, -4.5], 'rotation': [0, 0.258819, 0, 0.965926]}
TABS = ['map', 'quests', 'objects', 'places', 'surfaces', 'workspaces', 'help', 'whatsnew', 'settings', 'performance']


def evaluate(script, expression):
    return json.loads(subprocess.check_output(['node', '-e', script + '\nconsole.log(JSON.stringify(' + expression + '));'], text=True))


def js(expression):
    return evaluate(NPCS_JS, expression)


def call(name, *args):
    return js(name + '(' + ', '.join(json.dumps(a) for a in args) + ')')


def request(method, params, rid='r'):
    return {'jsonrpc': '2.0', 'id': rid, 'method': method, 'params': params}


def definition(validator, name):
    return validator.evolve(schema={'$ref': validator.schema['$id'] + '#/$defs/' + name})


def point(x, z, kind='line'):
    return {'position': [x, 0, z], 'type': kind}


def path(id, source='package', use='route', walkable=True, **over):
    return {'ref': source + '/' + id, 'source': source, 'id': id, 'name': None, 'use': use, 'closed': False,
            'points': [point(0, 0), point(4, 0, 'curve'), point(4, 4)], 'speed': None, 'stops': [],
            'walkable': walkable if use == 'route' else None, 'problems': [], 'bound': [], **over}


PATHS = [
    path('plaza-loop', name='Plaza loop', closed=True, bound=['resident-1']),
    path('bridge-walk', walkable=False, problems=['no floor under (4.0, 0.0, 2.5)', 'capsule hits a wall at (4.0, 0.0, 3.0)']),
    path('path-1', source='user', name='Desk round', stops=[{'point': 1, 'seconds': 5, 'clip': 'wave'}]),
    path('rail', use='track'),
    path('crowded', bound=['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']),
]


def instance(**over):
    return {'id': 'u-npc001', 'source': 'user', 'ref': GUIDE, 'name': 'Guide', 'areaId': 'plaza', 'pose': POSE, 'scale': 1,
            'state': 'active', 'movable': False, 'locked': False, 'rule': None, 'path': 'user/path-1', 'activity': 'walking',
            'seat': None, 'character': True, 'accent': [0.6939, 0.0953, 0.0437], **over}


RESIDENT_1 = instance(id='resident-1', source='authored', ref=RESIDENT, name='Ada', path='package/plaza-loop', activity='stopped', accent=None)
SITTER = instance(id='sitter', source='authored', ref=RESIDENT, name='Bo', path=None, seat='bench-1', activity='sitting', accent=None)
LAMP = {k: v for k, v in instance(id='u-lamp', ref='user/lamp', name='Lamp', character=False, path=None, activity=None, accent=None, movable=True).items()}
NPCS = {'motion': 'auto', 'state': 'paused', 'reason': 'battery', 'usage': {'authored': 2, 'user': 1}, 'limits': {'authored': 16, 'user': 8},
        'drawing': None, 'aimed': None, 'interaction': None}
AIMED = {'objectId': 'resident-1', 'name': 'Ada', 'prompt': 'Talk',
         'interactions': [{'id': 'hello', 'label': 'Talk', 'type': 'say'}]}
SAY = {'objectId': 'resident-1', 'interactionId': 'hello', 'type': 'say', 'label': 'Talk', 'choices': [], 'line': 'Mind the rails.',
       'lineIndex': 0, 'lineCount': 2, 'panel': None}
CHOOSE = {'objectId': 'resident-1', 'interactionId': None, 'type': 'choose', 'label': 'Ada', 'line': None, 'lineIndex': 0, 'lineCount': 0, 'panel': None,
          'choices': [{'id': 'hello', 'label': 'Talk'}, {'id': 'map', 'label': 'Show me the map'}, {'id': 'follow', 'label': 'Walk with me'}]}


class Grants(unittest.TestCase):
    """0.23 adds no grant: character changes use objects.control (requested from 0.22)."""

    def test_hello_validates_and_grants_are_inherited(self):
        frame(request('session.hello', {'protocols': ['0.23'], 'client': {'id': 'com.hyprune.shell', 'name': 'Hyprune shell'},
                                        'capabilities': capabilities('0.23')}), V23)
        self.assertEqual(capabilities('0.23'), capabilities('0.22'))
        self.assertIn('objects.control', capabilities('0.23'))
        self.assertNotIn('objects.control', capabilities('0.99'))  # unvendored, never assumed newer


class HelloOnTheWire(unittest.IsolatedAsyncioTestCase):
    async def test_0_23_hello(self):
        captured = asyncio.get_running_loop().create_future()
        with tempfile.TemporaryDirectory() as tmp:
            sock = tmp + '/core.sock'

            async def peer(reader, writer):
                msg = await read_frame(reader, V23)
                if not captured.done(): captured.set_result(msg['params'])
                writer.close()
            server = await asyncio.start_unix_server(peer, sock)
            os.chmod(sock, 0o600)
            client = Client(sock, lambda e: None, protocol='0.23')
            task = asyncio.create_task(client.run())
            try:
                async with asyncio.timeout(4):
                    params = await captured
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                server.close(); await server.wait_closed()
        self.assertEqual(params['protocols'], ['0.23'])
        self.assertIn('objects.control', params['capabilities'])


class Allowlist(unittest.TestCase):
    def test_npc_methods_only_from_0_23(self):
        for version in OLDER + ['0.99']:
            self.assertFalse(set(NPC_ACTIONS) & set(shell_actions(version)), version)
        self.assertEqual(set(shell_actions('0.23')) - set(shell_actions(PREVIOUS)), set(NPC_ACTIONS))
        self.assertTrue(set(OBJECT_ACTIONS) <= set(shell_actions('0.23')))

    def test_every_npc_action_is_a_0_23_method(self):
        methods = V23.schema['$defs']['session.hello.result']['properties']['methods']['items']['enum']
        old = VALIDATORS[PREVIOUS].schema['$defs']['session.hello.result']['properties']['methods']['items']['enum']
        self.assertEqual(sorted(set(methods) - set(old)), sorted(NPC_ACTIONS))
        for method in NPC_ACTIONS:
            self.assertIn(method + '.request', V23.schema['$defs'])
            self.assertNotIn(method + '.request', VALIDATORS[PREVIOUS].schema['$defs'])

    def test_results_and_refusals_echo_params_and_rule(self):
        event = action_event('npcs.spawn', {'ref': GUIDE}, {'revision': 4, 'id': 'u-npc002'})
        self.assertEqual(event['params'], {'ref': GUIDE})
        cmd = {'type': 'action', 'method': 'paths.set', 'params': {'path': {'use': 'route', 'closed': False, 'points': [point(0, 0), point(1, 0)]}}}
        notice = action_notice(cmd, CoreError(-32007, 'no floor under (4.0, 0.0, 2.5)', {'retryable': False, 'rule': 'walkable'}))
        self.assertEqual(notice['params'], cmd['params'])
        self.assertEqual(notice['error'], {'code': -32007, 'message': 'no floor under (4.0, 0.0, 2.5)', 'rule': 'walkable'})
        budget = action_notice({'type': 'action', 'method': 'npcs.spawn', 'params': {'ref': GUIDE}},
                               CoreError(-32008, 'user characters: 8 per world', {'retryable': False, 'rule': 'budget'}))
        self.assertEqual(budget['error']['rule'], 'budget')
        choose = action_notice({'type': 'action', 'method': 'interaction.choose', 'params': {'objectId': 'x', 'interactionId': None}}, CoreError(-32004, 'unknown id'))
        self.assertEqual(choose['error'], {'code': -32004, 'message': 'unknown id'})


class Wire(unittest.TestCase):
    """Every request the shell builds validates against 0.23 and is refused by 0.22."""

    def requests(self):
        user, settings = instance(), {'speed': 1.5, 'phase': 0.25, 'reverse': True, 'accent': '#3c8dbc'}
        made = [call('spawnRequest', GUIDE, {'kind': 'route', 'path': 'package/plaza-loop'}, settings),
                call('spawnRequest', GUIDE, {'kind': 'route', 'path': 'plaza-loop'}, {}),
                call('spawnRequest', GUIDE, {'kind': 'stand'}, settings),
                call('spawnRequest', RESIDENT, {'kind': 'draw'}, settings),
                call('bindRequest', user, {'kind': 'route', 'path': 'user/path-1'}, {'speed': 0.5}),
                call('bindRequest', user, {'kind': 'draw'}, {}),
                call('bindRequest', user, {'kind': 'settings'}, {'accent': '#d9573b'}),
                call('characterRequest', user, 'disable'), call('characterRequest', instance(state='hidden'), 'disable'),
                call('characterRequest', RESIDENT_1, 'disable'), call('characterRequest', user, 'remove'),
                call('motionRequest', 'still'),
                call('stopsRequest', PATHS[2], [{'point': 0, 'seconds': '4', 'kind': 'seat', 'seat': 'bench-1'},
                                                {'point': 2, 'seconds': 2.5, 'kind': 'clip', 'clip': 'nod'}, {'point': 1, 'seconds': 3, 'kind': 'wait'}])]
        made += [{'method': 'npcs.remove', 'params': {'all': True}}, {'method': 'paths.list', 'params': {}},
                 {'method': 'paths.finish', 'params': {}}, {'method': 'paths.remove', 'params': {'id': 'path-9'}},
                 {'method': 'paths.remove', 'params': {'id': 'path-1', 'unbind': True}},
                 {'method': 'interaction.choose', 'params': call('chooseParams', CHOOSE, 'map')},
                 {'method': 'interaction.choose', 'params': call('chooseParams', CHOOSE, None)}]
        return made

    def test_requests(self):
        for made in self.requests():
            self.assertIsNotNone(made)
            message = request(made['method'], made['params'])
            frame(message, V23)
            if made['method'] != 'graphics.set':
                with self.assertRaises(Exception, msg=made):
                    VALIDATORS[PREVIOUS].validate(message)
        with self.assertRaises(Exception):  # npc_motion is a 0.23 graphics key
            VALIDATORS[PREVIOUS].validate(request('graphics.set', {'patch': {'npc_motion': 'still'}}))

    def test_param_shapes(self):
        made = self.requests()
        self.assertEqual(made[0], {'method': 'npcs.spawn', 'params': {'ref': GUIDE, 'path': 'package/plaza-loop', 'speed': 1.5,
                                                                      'accent': [0.0452, 0.2664, 0.5029], 'phase': 0.25, 'reverse': True}})
        self.assertEqual(made[1]['params'], {'ref': GUIDE, 'path': 'package/plaza-loop'})  # defaults are left out
        self.assertEqual(made[2]['params'], {'ref': GUIDE, 'speed': 1.5, 'accent': [0.0452, 0.2664, 0.5029]})  # no phase/reverse off a route
        self.assertEqual(made[3], {'method': 'paths.draw', 'params': {'use': 'route', 'spawn': {'ref': RESIDENT, 'speed': 1.5,
                                                                                               'accent': [0.0452, 0.2664, 0.5029], 'phase': 0.25}}})
        self.assertEqual(made[4]['params'], {'id': 'u-npc001', 'path': 'user/path-1', 'speed': 0.5})
        self.assertEqual(made[5], {'method': 'paths.draw', 'params': {'use': 'route', 'bind': 'u-npc001'}})
        self.assertEqual(made[7]['params'], {'id': 'u-npc001', 'disabled': True})
        self.assertEqual(made[8]['params'], {'id': 'u-npc001', 'disabled': False})
        self.assertEqual(made[9]['params'], {'id': 'resident-1', 'disabled': True})  # authored characters disable too
        self.assertEqual(made[11], {'method': 'graphics.set', 'params': {'patch': {'npc_motion': 'still'}}})
        path = made[12]['params']['path']
        self.assertEqual((path['id'], path['name'], path['use']), ('path-1', 'Desk round', 'route'))
        self.assertNotIn('speed', path)
        self.assertEqual(path['stops'], [{'point': 0, 'seconds': 4, 'seat': 'bench-1'}, {'point': 1, 'seconds': 3},
                                         {'point': 2, 'seconds': 2.5, 'clip': 'nod'}])

    def test_refused_shapes(self):
        self.assertIsNone(call('characterRequest', RESIDENT_1, 'remove'))  # authored: never removed
        self.assertIsNone(call('bindRequest', RESIDENT_1, {'kind': 'route', 'path': 'plaza-loop'}, {}))  # authored: not rebound
        self.assertIsNone(call('bindRequest', instance(), {'kind': 'settings'}, {}))  # nothing to change
        self.assertIsNone(call('motionRequest', 'sometimes'))
        for method, params in [('npcs.spawn', {'ref': GUIDE, 'path': 'plaza-loop', 'pose': POSE}), ('npcs.spawn', {'ref': GUIDE, 'reverse': True}),
                               ('npcs.spawn', {'ref': GUIDE, 'speed': 3}), ('npcs.bind', {'id': 'u-npc001'}),
                               ('paths.draw', {'spawn': {'ref': GUIDE}, 'bind': 'u-npc001'}), ('paths.set', {'path': {'use': 'route', 'closed': False, 'points': [point(0, 0)]}}),
                               ('interaction.choose', {'objectId': 'resident-1'}), ('npcs.remove', {'id': 'x', 'all': True})]:
            with self.assertRaises(Exception, msg=(method, params)):
                frame(request(method, params), V23)

    def test_results(self):
        cases = [('npcs.spawn', {'revision': 3, 'id': 'u-npc002'}), ('npcs.bind', {'revision': 4}), ('npcs.disable', {'revision': 5}),
                 ('npcs.remove', {'revision': 6}), ('paths.list', {'paths': PATHS}), ('paths.set', {'revision': 7, 'id': 'path-2'}),
                 ('paths.remove', {'revision': 8}), ('paths.draw', {'revision': 9, 'id': 'path-3'}),
                 ('paths.finish', {'revision': 10, 'id': 'path-3', 'bound': 'u-npc002'}), ('paths.finish', {'revision': 11, 'id': None, 'bound': None}),
                 ('interaction.choose', {'revision': 12})]
        for method, result in cases:
            validate_response({'jsonrpc': '2.0', 'id': 'r', 'result': result}, method, V23)

    def test_state_shapes(self):
        state = V23.schema['$defs']['state']
        self.assertIn('npcs', state['required'])
        self.assertNotIn('npcs', VALIDATORS[PREVIOUS].schema['$defs']['state']['properties'])
        npcs = definition(V23, 'npcsState')
        npcs.validate(NPCS)
        npcs.validate({**NPCS, 'state': 'animating', 'reason': None, 'aimed': AIMED, 'interaction': SAY,
                       'drawing': {'pathId': 'path-3', 'use': 'route', 'spawn': {'ref': GUIDE}, 'bind': None}})
        npcs.validate({**NPCS, 'interaction': CHOOSE})
        instances = definition(V23, 'objectInstance')
        for subject in [instance(), RESIDENT_1, SITTER, LAMP, instance(state='suspended', activity='suspended')]:
            instances.validate(subject)
        with self.assertRaises(Exception):  # 0.22 instances have no character or accent
            definition(VALIDATORS[PREVIOUS], 'objectInstance').validate(instance())
        editor_path = {'id': 'path-1', 'worldId': 'w', 'areaId': 'a', 'closed': False, 'points': PATHS[2]['points'], 'use': 'route',
                       'name': 'Desk round', 'speed': None, 'stops': PATHS[2]['stops']}
        definition(V23, 'editorPath').validate(editor_path)
        self.assertIn('interact', V23.schema['$defs']['reticle']['properties']['action']['enum'])
        self.assertNotIn('interact', VALIDATORS[PREVIOUS].schema['$defs']['reticle']['properties']['action']['enum'])
        self.assertEqual(V23.schema['$defs']['graphicsPatch']['properties']['npc_motion']['enum'], ['auto', 'always', 'still', 'off'])

    def test_shell_motion_ids_follow_the_pin(self):
        self.assertEqual([m['id'] for m in js('MOTIONS')], V23.schema['$defs']['npcMotion']['enum'])
        self.assertEqual(sorted(c['id'] for c in js('CLIPS')), sorted(V23.schema['$defs']['pathStop']['properties']['clip']['enum']))
        self.assertTrue(set(js('Object.keys(ACTIVITIES)')) >= set(V23.schema['$defs']['npcActivity']['enum']))


class WorldFormat(unittest.TestCase):
    WORLD = {'formatVersion': '0.9', 'id': 'org.example.plaza', 'version': '0.1.0', 'name': 'Plaza', 'license': 'CC0-1.0', 'scene': 'scene.glb',
             'defaultSpawn': 'arrival', 'spawns': [{'id': 'arrival', 'pose': {'position': [0, 0, 0], 'rotation': [0, 0, 0, 1]}}],
             'attribution': [{'path': '.', 'author': 'Example', 'license': 'CC0-1.0'}],
             'paths': [{'id': 'plaza-loop', 'name': 'Plaza loop', 'use': 'route', 'closed': True,
                        'points': [point(0, 0), point(4, 0, 'curve'), point(4, 4)], 'stops': [{'point': 1, 'seconds': 4, 'clip': 'wave'}]}],
             'seats': [{'id': 'bench-1', 'pose': {'position': [2, 0, 2], 'rotation': [0, 0, 0, 1]}, 'height': 0.45}],
             'keepClear': [{'id': 'door', 'min': [-1, 0, -1], 'max': [1, 2, 1]}]}

    def test_world_0_9_is_accepted_and_0_8_refuses_its_fields(self):
        WORLD_VALIDATORS['0.9'].validate(self.WORLD)
        older = copy.deepcopy(self.WORLD)
        older['formatVersion'] = '0.8'
        with self.assertRaises(Exception):
            WORLD_VALIDATORS['0.8'].validate(older)


class ChoiceInput(unittest.IsolatedAsyncioTestCase):
    """The bridge holds exclusive input for a choice list (like the note prompt)."""

    def client(self, interaction=None, director=False):
        events, calls = [], []
        client = Client('/unused', events.append, protocol='0.23')

        async def fake(method, params, bootstrap=False):
            calls.append((method, params))
            frame(request(method, params), V23)  # every call the bridge makes is a valid 0.23 request
            return {'revision': 7}
        client.call = fake
        client.lease, client.output, client.ready, client.wayland_pid, client.director = 'lease-1', 'output-main', True, 4242, director
        client.hello = {'methods': ['interaction.choose', 'ui.open', 'shell.overlay', 'shell.bind']}
        client.state = {'runtime': {'active': True}, 'npcs': {**NPCS, 'interaction': interaction}}
        return client, events, calls

    def prompts(self, events): return [e['value'] for e in events if e['type'] == 'interaction.prompt']

    async def test_choice_grabs_and_releases_input(self):
        client, events, calls = self.client(CHOOSE)
        await client.sync_choice()
        self.assertEqual([c[0] for c in calls], ['shell.bind', 'shell.overlay'])
        self.assertEqual(calls[1][1], {'leaseId': 'lease-1', 'outputId': 'output-main', 'visible': True, 'exclusiveInput': True})
        self.assertEqual(self.prompts(events), [CHOOSE])
        await client.sync_choice()  # same list: nothing again
        self.assertEqual(len(calls), 2)
        client.state['npcs']['interaction'] = SAY  # the choice became a say: list hidden, input released
        await client.sync_choice()
        self.assertEqual(calls[-1], ('shell.overlay', {'leaseId': 'lease-1', 'outputId': 'output-main', 'visible': False, 'exclusiveInput': False}))
        self.assertEqual(self.prompts(events), [CHOOSE, None])
        self.assertIsNone(client.choice_key)

    async def test_director_or_note_keep_their_input(self):
        client, events, calls = self.client(CHOOSE, director=True)
        await client.sync_choice()
        self.assertEqual(calls, [])
        self.assertEqual(self.prompts(events), [CHOOSE])
        client.state['npcs']['interaction'] = None
        await client.sync_choice()
        self.assertEqual(calls, [])  # the Director's overlay stays

    async def test_older_protocols_ignore_npcs(self):
        client, events, calls = self.client(CHOOSE)
        client.protocol = '0.22'
        await client.sync_choice()
        self.assertEqual((calls, events), ([], []))

    async def test_core_escape_ends_the_interaction(self):
        client, events, calls = self.client(CHOOSE)
        await client.sync_choice()
        client.end_choice(dismiss=True)
        await asyncio.sleep(0)
        await asyncio.gather(*client.tasks)
        self.assertEqual(calls[-1], ('interaction.choose', {'objectId': 'resident-1', 'interactionId': None}))
        self.assertEqual(self.prompts(events)[-1], None)
        self.assertFalse(client.choice_grab)

    async def test_panel_interaction_opens_the_director_then_ends(self):
        panel = {**SAY, 'type': 'panel', 'interactionId': 'map', 'label': 'Map', 'line': None, 'lineCount': 0, 'panel': 'map'}
        client, events, calls = self.client(panel)
        await client.interaction_panel('resident-1')
        self.assertEqual(calls, [('ui.open', {'leaseId': 'lease-1', 'outputId': 'output-main', 'panel': 'overview'}),
                                 ('interaction.choose', {'objectId': 'resident-1', 'interactionId': None})])
        with self.assertRaises(ValueError):
            await client.interaction_panel('someone-else')
        client.state['npcs']['interaction'] = SAY
        with self.assertRaises(ValueError):
            await client.interaction_panel('resident-1')


class Spawn(unittest.TestCase):
    """qml/Npcs.js: catalog characters, the route column and settings."""

    def test_character_entries(self):
        entry = {'ref': GUIDE, 'traits': ['character', 'movable'], 'state': 'ready', 'placeable': False, 'reason': 'use npcs.spawn', 'errors': []}
        self.assertEqual(call('isCharacter', entry), True)
        self.assertEqual(call('canSpawn', entry), True)  # placeable does not apply to characters
        self.assertEqual(call('spawnNote', entry), '')
        broken = {**entry, 'state': 'invalid', 'errors': ['no walk clip']}
        self.assertEqual((call('canSpawn', broken), call('spawnNote', broken)), (False, 'no walk clip'))
        self.assertEqual(call('isCharacter', {'traits': ['movable']}), False)

    def test_route_options(self):
        rows = call('routeOptions', PATHS)
        self.assertEqual([r['ref'] for r in rows], ['package/plaza-loop', 'package/bridge-walk', 'user/path-1', 'package/crowded'])  # routes only
        loop, bridge, mine, crowded = rows
        self.assertEqual((loop['label'], loop['sourceLabel'], loop['enabled'], loop['note'], loop['closed']), ('Plaza loop', 'World', True, '1 character walks it', True))
        self.assertEqual((bridge['label'], bridge['enabled'], bridge['note'], bridge['level']), ('bridge-walk', False, 'no floor under (4.0, 0.0, 2.5)', 'warning'))
        self.assertEqual((mine['sourceLabel'], mine['enabled'], mine['points']), ('Mine', True, 3))
        self.assertEqual((crowded['enabled'], crowded['note']), (False, '8 characters already walk it'))
        self.assertEqual(call('routeText', PATHS, 'plaza-loop'), 'Plaza loop')  # bare id = package/<id>
        self.assertEqual(call('routeText', PATHS, 'user/gone'), 'gone')

    def test_drawn_paths_are_offered(self):
        # A path drawn with tool 3 is generic; core makes it a route when a character is put on it.
        drawn = path('path-7', source='user', use='generic', walkable=None, closed=True)
        empty = {**path('path-8', source='user', use='generic', walkable=None), 'points': []}
        package_generic = path('vista', use='generic', walkable=None)
        rows = call('routeOptions', [drawn, empty, package_generic])
        self.assertEqual([r['ref'] for r in rows], ['user/path-7'])
        row = rows[0]
        self.assertEqual((row['label'], row['sourceLabel'], row['enabled'], row['closed'], row['note']),
                         ('Drawn path', 'Mine', True, True, 'Drawn with tool 3 · becomes a route'))
        named = call('routeOptions', [{**drawn, 'name': 'Square'}])[0]
        self.assertEqual(named['label'], 'Square')
        request = call('bindRequest', instance(), {'kind': 'route', 'path': 'user/path-7'}, {'speed': 1, 'phase': 0, 'reverse': False, 'accent': ''})
        self.assertEqual(request, {'method': 'npcs.bind', 'params': {'id': 'u-npc001', 'path': 'user/path-7'}})

    def test_accent_round_trip_and_settings(self):
        for hexa in js('ACCENTS'):
            self.assertEqual(call('hexFromAccent', call('accentFromHex', hexa)), hexa)
        self.assertIsNone(call('accentFromHex', 'red'))
        self.assertEqual(call('settingsParams', {'speed': 9, 'phase': 1.4, 'reverse': True, 'accent': ''}, True), {'speed': 2, 'phase': 0.999, 'reverse': True})
        self.assertEqual(call('settingsParams', {'speed': '0,1', 'phase': -1}, True), {'speed': 0.25})
        self.assertEqual(call('settingsParams', {'speed': 1, 'phase': 0.5, 'reverse': True}, False), {})

    def test_stops(self):
        drafts = call('stopDrafts', PATHS[2])
        self.assertEqual(drafts, [{'point': 1, 'seconds': 5, 'kind': 'clip', 'clip': 'wave', 'seat': '', 'face': None}])
        self.assertEqual(call('nextStopPoint', PATHS[2], drafts), 0)
        added = call('addStop', PATHS[2], drafts)
        self.assertEqual([d['point'] for d in added], [0, 1])
        full = call('addStop', PATHS[2], call('addStop', PATHS[2], added))
        self.assertEqual(len(full), 3)
        self.assertEqual(call('addStop', PATHS[2], full), full)  # every point has a stop
        for bad, words in [([{'point': 3, 'seconds': 3, 'kind': 'wait'}], 'points run'), ([{'point': 0, 'seconds': 0.1, 'kind': 'wait'}], 'seconds'),
                           ([{'point': 0, 'seconds': 3, 'kind': 'seat', 'seat': ' '}], 'seat'),
                           ([{'point': 0, 'seconds': 3, 'kind': 'wait'}, {'point': '0', 'seconds': 3, 'kind': 'wait'}], 'One stop per point')]:
            self.assertIn(words, call('stopsRequest', PATHS[2], bad)['error'])
        self.assertIn('error', call('stopsRequest', PATHS[0], []))  # package routes are read-only
        self.assertEqual(call('editableRoute', PATHS[2]), True)


class Panel(unittest.TestCase):
    """The Characters panel: rows, actions, motion and state."""

    def test_rows(self):
        rows = call('characterRows', [RESIDENT_1, LAMP, SITTER, instance(), instance(id='u-off', state='hidden'),
                                      instance(id='u-stuck', state='suspended', activity='suspended')], PATHS)
        self.assertEqual([r['id'] for r in rows], ['resident-1', 'sitter', 'u-npc001', 'u-off', 'u-stuck'])  # characters only
        self.assertEqual([r['place'] for r in rows[:3]], ['Route · Plaza loop', 'Seat · bench-1', 'Route · Desk round'])
        self.assertEqual([r['activity'] for r in rows], ['Stopped', 'Sitting', 'Walking', 'Disabled', 'Suspended · route not walkable'])
        self.assertEqual([r['level'] for r in rows], ['ok', 'ok', 'ok', 'muted', 'warning'])
        self.assertEqual([r['sourceLabel'] for r in rows[:3]], ['World', 'World', 'Mine'])
        self.assertEqual(call('placeText', instance(path=None), PATHS), 'Standing spot')

    def test_actions(self):
        self.assertEqual([(a['id'], a['visible']) for a in call('characterActions', RESIDENT_1)], [('disable', True), ('rebind', False), ('remove', False)])
        self.assertEqual([a['visible'] for a in call('characterActions', instance())], [True, True, True])
        self.assertEqual(call('characterActions', instance(state='hidden'))[0]['label'], 'Enable')

    def test_motion_state(self):
        self.assertEqual(call('stateText', NPCS), 'Paused · on battery')
        self.assertEqual(call('stateText', {**NPCS, 'reason': 'usb-c power'}), 'Paused · on USB-C power')
        self.assertEqual(call('stateText', {**NPCS, 'reason': 'something new'}), 'Paused · something new')  # core's words
        self.assertEqual(call('stateText', {**NPCS, 'state': 'animating', 'reason': None}), 'Animating')
        self.assertEqual([call('stateLevel', {**NPCS, 'state': s}) for s in ['animating', 'paused', 'off']], ['ok', 'warning', 'muted'])
        self.assertEqual(call('usageText', NPCS), '2 / 16 world  ·  1 / 8 mine')
        self.assertEqual(call('userFull', {**NPCS, 'usage': {'authored': 0, 'user': 8}}), True)
        self.assertEqual(sorted(js('Object.keys(MOTION_NOTES)')), ['always', 'auto', 'off', 'still'])
        # auto no longer pauses for power or idle: the same as always (both kept on the wire).
        self.assertIn('whenever the world is shown', js('MOTION_NOTES.auto'))
        self.assertIn('same as Auto', js('MOTION_NOTES.always'))
        self.assertNotIn('battery', js('MOTION_NOTES.auto'))


class Prompts(unittest.TestCase):
    """HUD prompts and the interaction effects."""

    def test_aimed_prompt(self):
        self.assertEqual(call('aimedPrompt', AIMED)['text'], 'Talk')
        self.assertEqual(call('aimedPrompt', {**AIMED, 'prompt': 'Say hello'})['text'], 'Say hello')
        several = {**AIMED, 'interactions': AIMED['interactions'] + [{'id': 'map', 'label': 'Map', 'type': 'panel'}]}
        prompt = call('aimedPrompt', several)
        self.assertEqual((prompt['key'], prompt['text'], prompt['count']), ('E', 'Talk to Ada', 2))
        self.assertIsNone(call('aimedPrompt', {**AIMED, 'interactions': []}))
        self.assertIsNone(call('aimedPrompt', None))

    def test_aimed_prompt_pause_note(self):
        # Animating (auto or always): no note. Posed still or reduced motion: why, and where it is set.
        animating = {**NPCS, 'state': 'animating', 'reason': None}
        self.assertEqual(call('aimedPrompt', AIMED, animating)['note'], '')
        self.assertEqual(call('aimedPrompt', AIMED, None)['note'], '')
        self.assertEqual(call('aimedPrompt', AIMED, {**NPCS, 'motion': 'still', 'state': 'still', 'reason': None})['note'],
                         'Posed still · Objects › Characters')
        self.assertEqual(call('aimedPrompt', AIMED, {**NPCS, 'state': 'paused', 'reason': 'reduced motion'})['note'], 'Reduced motion · Settings')
        self.assertEqual(call('pauseNote', {**NPCS, 'state': 'paused', 'reason': 'focus'}), 'Paused · a window has focus · Objects › Characters')
        self.assertEqual(call('pauseNote', {**NPCS, 'state': 'off', 'reason': None}), '')
        for note in [call('pauseNote', {**NPCS, 'state': st, 'reason': r}) for st, r in
                     [('still', None), ('paused', 'reduced motion'), ('paused', 'focus'), ('paused', 'battery')]]:
            self.assertLessEqual(len(note), 64, note)  # one short line under the prompt

    def test_caption(self):
        caption = call('caption', SAY, 'Ada')
        self.assertEqual((caption['speaker'], caption['line'], caption['progress'], caption['hint']), ('Ada', 'Mind the rails.', '1 / 2', 'E · next'))
        last = call('caption', {**SAY, 'lineIndex': 1}, '')
        self.assertEqual((last['speaker'], last['hint']), ('Talk', 'E · close'))
        self.assertEqual(call('caption', {**SAY, 'lineCount': 1}, 'Ada')['progress'], '')
        self.assertIsNone(call('caption', CHOOSE, 'Ada'))

    def test_choices(self):
        items = call('choiceItems', CHOOSE)
        self.assertEqual([(i['key'], i['id']) for i in items], [('1', 'hello'), ('2', 'map'), ('3', 'follow')])
        self.assertEqual(call('choiceItems', SAY), [])
        self.assertEqual([call('choiceMove', i, 3, k) for i, k in [(2, 'next'), (0, 'previous'), (-1, 'next'), (1, 'home'), (0, 'end')]], [0, 2, 0, 0, 2])
        self.assertEqual(call('chooseParams', CHOOSE, 'follow'), {'objectId': 'resident-1', 'interactionId': 'follow'})
        self.assertEqual(call('chooseParams', CHOOSE, None), {'objectId': 'resident-1', 'interactionId': None})

    def test_effects(self):
        panel = {**SAY, 'type': 'panel', 'panel': 'map', 'line': None}
        self.assertEqual(call('interactionEffect', panel, 'Ada', TABS), {'kind': 'panel', 'tab': 0, 'view': '', 'objectId': 'resident-1'})
        self.assertEqual(call('interactionEffect', {**panel, 'panel': 'characters'}, 'Ada', TABS)['view'], 'characters')
        self.assertEqual(call('interactionEffect', {**panel, 'panel': 'whats-new'}, 'Ada', TABS)['tab'], TABS.index('whatsnew'))
        self.assertEqual(call('interactionEffect', {**panel, 'panel': 'casino'}, 'Ada', TABS), {'kind': 'end', 'objectId': 'resident-1'})  # unknown ids
        waypoint = call('interactionEffect', {**SAY, 'type': 'waypoint', 'label': 'Show me the desk'}, 'Ada', TABS)
        self.assertEqual((waypoint['kind'], waypoint['toast']['title'], waypoint['toast']['line'], waypoint['toast']['detail']),
                         ('toast', 'Ada', 'Waypoint set', 'Show me the desk'))
        guide = call('interactionEffect', {**SAY, 'type': 'guide', 'label': 'Walk with me'}, 'Ada', TABS)
        self.assertEqual(guide['toast']['line'], 'Follow Ada')
        self.assertLessEqual(guide['toast']['durationMs'], 5000)
        self.assertEqual(call('interactionEffect', CHOOSE, 'Ada', TABS), {'kind': 'choose'})
        self.assertEqual(call('interactionEffect', None, '', TABS), {'kind': 'none'})
        self.assertNotEqual(call('interactionKey', SAY), call('interactionKey', {**SAY, 'type': 'guide'}))

    def test_drawing_hint(self):
        hint = call('drawingHint', {'pathId': 'path-3', 'use': 'route', 'spawn': {'ref': GUIDE}, 'bind': None}, 'Guide')
        self.assertEqual((hint['title'], hint['pathId']), ('Drawing a route', 'path-3'))
        self.assertIn('tool 3', hint['line'])
        self.assertIn('Done', hint['line'])
        self.assertEqual(hint['detail'], 'Guide starts walking it when you finish.')
        self.assertIsNone(call('drawingHint', None, ''))


class Feedback(unittest.TestCase):
    def test_refusal_toasts(self):
        toast = call('errorToast', 'paths.set', {'code': -32007, 'message': 'no floor under (4.0, 0.0, 2.5)', 'rule': 'walkable'}, '')
        self.assertEqual((toast['title'], toast['line'], toast['detail'], toast['tone']), ('Route', 'no floor under (4.0, 0.0, 2.5)', '', 'warning'))
        spawn = call('errorToast', 'npcs.spawn', {'code': -32007, 'message': 'no free spot in front of you', 'rule': 'reach'}, '')
        self.assertEqual((spawn['title'], spawn['detail']), ('Character', 'Rule: out of reach'))
        self.assertEqual(call('errorToast', 'interaction.choose', None, '-32004: unknown id')['line'], 'unknown id')
        # The user's settings refuse a guide (-32005, core's reason) instead of accepting it.
        guide = call('errorToast', 'interaction.choose', {'code': -32005, 'message': 'characters are paused (motion still)'}, '')
        self.assertEqual((guide['title'], guide['line'], guide['tone']), ('Interaction', 'characters are paused (motion still)', 'warning'))

    def test_results_and_notices(self):
        self.assertEqual(call('resultText', 'npcs.spawn', {'ref': GUIDE, 'path': 'package/plaza-loop'}, {}), 'Spawned on plaza-loop.')
        self.assertEqual(call('resultText', 'npcs.spawn', {'ref': GUIDE}, {}), 'Spawned in front of you.')
        self.assertEqual(call('resultText', 'paths.finish', {}, {'id': None, 'bound': None}), 'Nothing was being drawn.')
        self.assertEqual(call('resultText', 'paths.finish', {}, {'id': 'path-3', 'bound': 'u-1'}), 'Route saved; the character walks it.')
        self.assertIsNone(call('resultText', 'paths.list', {}, {}))
        toast = call('noticeToast', {'code': 'path.unwalkable', 'message': 'route path-3: no floor under (1, 0, 2)'})
        self.assertEqual((toast['title'], toast['tone'], toast['line']), ('Route', 'warning', 'route path-3: no floor under (1, 0, 2)'))
        self.assertIsNone(call('noticeToast', {'code': 'runtime.ready', 'message': 'x'}))
        # E on a resident refused by the motion setting: a short toast, not only the notice list.
        refused = call('noticeToast', {'code': 'interaction.refused', 'level': 'info', 'message': 'characters are paused (motion off)'})
        self.assertEqual((refused['title'], refused['tone'], refused['line']), ('Interaction', 'warning', 'characters are paused (motion off)'))


class Presentation(unittest.TestCase):
    """QML wiring (source checks; the nested captures render it)."""

    def read(self, name): return (ROOT / 'qml' / name).read_text()

    def test_objects_tab(self):
        page = self.read('components/DirectorObjects.qml')
        for needle in ["{id: 'characters', label: 'Characters  ·  '", 'NpcSpawn {', 'NpcPanel {', "objectName: 'npcDrawing'",
                       "objectName: 'npc-draw-done'", "objectName: 'npc-draw-cancel'", 'i.character !== true']:
            self.assertIn(needle, page)
        card = self.read('components/ObjectCard.qml')
        self.assertIn("objectName: 'objectSpawn:' + (card.entry ? card.entry.ref : '')", card)
        self.assertIn("ShellState.objectsCan('npcs.spawn')", card)
        spawn = self.read('components/NpcSpawn.qml')
        for needle in ["kind: 'stand'", "kind: 'draw'", 'Npcs.routeOptions(ShellState.pathList)', "objectName: 'npcStops'", 'Npcs.stopsRequest']:
            self.assertIn(needle, spawn)
        panel = self.read('components/NpcPanel.qml')
        for needle in ["objectName: 'npcMotion'", 'Npcs.stateText(root.npcs)', 'ShellState.startRebind', "'npcs.remove', {all: true}"]:
            self.assertIn(needle, panel)

    def test_hud_and_choice_window(self):
        self.assertIn('NpcHud { anchors.fill:parent; z:3; leftLimit:deck.x+deck.width+40; inset:root.inset }', self.read('components/Hud.qml'))
        self.assertIn('shown: questColumn.height > 0 || ShellState.toasts.length > 0', self.read('components/Hud.qml'))
        hud = self.read('components/NpcHud.qml')
        self.assertIn('Tokens.reducedMotion ? 0', hud)
        for name in ['hudNpcPrompt', 'hudNpcCaption', 'hudNpcDrawing']:
            self.assertIn("objectName: '" + name + "'", hud)
        shell = self.read('shell.qml')
        self.assertRegex(shell, r"visible: ShellState\.active && !!ShellState\.npcChoice && !ShellState\.director[\s\S]{0,600}WlrKeyboardFocus\.Exclusive")
        choice = self.read('components/NpcChoice.qml')
        self.assertIn('Keys.onEscapePressed: ShellState.chooseInteraction(null)', choice)

    def test_state_routes_interactions(self):
        state = self.read('ShellState.qml')
        for needle in ["case 'interaction.prompt':", 'handleInteraction(interaction)', "send({type: 'interaction.panel', objectId: effect.objectId})",
                       "action('paths.list', {})", 'Npcs.errorToast(msg.method, msg.error || null, msg.message)', 'Npcs.noticeToast(msg)',
                       "npcAction('paths.finish', {})", "npcAction('paths.remove', {id: npcDrawing.pathId})"]:
            self.assertIn(needle, state)


if __name__ == '__main__':
    unittest.main()
