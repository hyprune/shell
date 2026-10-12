"""IPC 0.22 (RFC-0011 P1): objects.control grant negotiation, the object and library actions,
the objects state key, editor gizmo / unplaced objects / node selection, error rules, and the
pure helpers in qml/Objects.js and qml/HudManipulation.js (tested with node).

Wire checks run against the vendored 0.22 pin; 0.21 must refuse the new shapes."""
import asyncio
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bridge'))
from client import Client, CoreError, GRANTS, capabilities  # noqa: E402
from launch import OBJECT_ACTIONS, QUEST_ACTIONS, action_event, action_notice, shell_actions  # noqa: E402
from protocol import VALIDATORS, SUPPORTED_PROTOCOLS, frame, read_frame, validate_response  # noqa: E402

OBJECTS = (ROOT / 'qml/Objects.js').read_text()
MANIPULATION = (ROOT / 'qml/HudManipulation.js').read_text()
OLDER = [v for v in SUPPORTED_PROTOCOLS if int(v.split('.')[1]) < 22]
PREVIOUS = OLDER[-1]
V22 = VALIDATORS['0.22']

RACK = 'library/com.hyprune.starter@0.1.0/server-rack'
POSE = {'position': [3.2, 0, -4.5], 'rotation': [0, 0.258819, 0, 0.965926]}  # 30° yaw
USAGE = {'placements': 3, 'assets': 2, 'triangles': 12400, 'gpuBytes': 4404019, 'collisionTriangles': 24}
LIMITS = {'placements': 128, 'assets': 32, 'triangles': 400000, 'gpuBytes': 201326592, 'collisionTriangles': 10000}


def evaluate(script, expression, *args):
    return json.loads(subprocess.check_output(
        ['node', '-e', script + '\nconsole.log(JSON.stringify(' + expression + '));', *args], text=True))


def js(expression, *args):
    return evaluate(OBJECTS, expression, *args)


def request(method, params, rid='r'):
    return {'jsonrpc': '2.0', 'id': rid, 'method': method, 'params': params}


def definition(validator, name):
    return validator.evolve(schema={'$ref': validator.schema['$id'] + '#/$defs/' + name})


def instance(**over):
    return {'id': 'u-7c2e91', 'source': 'user', 'ref': RACK, 'name': 'Server rack', 'areaId': 'sun-court', 'pose': POSE, 'scale': 1,
            'state': 'active', 'movable': True, 'locked': False, 'rule': None, 'path': None, 'activity': None, 'seat': None, **over}


def entry(**over):
    return {'ref': RACK, 'source': 'library', 'id': 'server-rack', 'version': '0.1.0', 'formatVersion': '0.10', 'name': 'Server rack',
            'description': None, 'category': 'machines', 'tags': ['rack', 'network'], 'traits': ['decorative', 'collidable', 'movable', 'machine'],
            'surfaces': ['floor'], 'scale': [0.5, 2], 'bounds': {'min': [-0.62, 0, -0.65], 'max': [0.62, 2.16, 0.65]}, 'triangles': 4210,
            'gpuBytes': 1048576, 'collisionTriangles': 12, 'thumbnail': '/usr/share/hyprune/libraries/com.hyprune.starter@0.1.0/objects/server-rack/thumbnail.png',
            'license': 'CC-BY-4.0', 'library': 'com.hyprune.starter@0.1.0', 'versions': [], 'state': 'ready', 'placeable': True,
            'reason': None, 'errors': [], **over}


ARMILLARY = instance(id='sun-court-armillary', source='authored', ref='package/armillary', name='Armillary', movable=True)
LANTERN = entry(ref='user/street-lantern', source='user', id='street-lantern', version=None, library=None, name='Street lantern',
                category='lighting', tags=['lamp', 'outdoor'], traits=['decorative', 'movable'], thumbnail=None, triangles=880)
FERN = entry(ref='package/fern', source='package', id='fern', version=None, library=None, name='Potted fern', category='plants',
             tags=['green'], traits=[], placeable=False, reason='not movable: only objects with the movable trait can be placed')
BROKEN = entry(ref='user/broken', source='user', id='broken', version=None, library=None, name='Broken chair', category='furniture',
               tags=[], traits=['movable'], state='invalid', placeable=False, reason='invalid: model.glb is missing',
               errors=['model.glb is missing', 'thumbnail.png is not a PNG'], bounds=None, triangles=None, thumbnail=None)
GUIDE = entry(ref='user/guide', source='user', id='guide', version=None, library=None, name='Guide', category='characters',
              tags=['npc'], traits=['character', 'movable'], placeable=False, reason='character: user characters arrive with routes (RFC-0011 P2)')
CATALOG = [FERN, entry(), LANTERN, BROKEN, GUIDE]
STATE = {'catalogRevision': 3, 'instances': [ARMILLARY, instance(), instance(id='u-0000aa', state='blocked', rule='walls', locked=True, movable=False)],
         'pocket': [{'itemId': 'pocket-1', 'ref': 'user/street-lantern', 'name': 'Street lantern'}], 'usage': USAGE, 'limits': LIMITS}


class Grants(unittest.TestCase):
    """objects.control is requested only where the offered protocol defines it: an older core
    rejects an unknown capability (-32602), so every pin must accept the shell's hello."""

    def test_hello_validates_against_every_pin(self):
        for version in SUPPORTED_PROTOCOLS:
            frame(request('session.hello', {'protocols': [version], 'client': {'id': 'com.hyprune.shell', 'name': 'Hyprune shell'},
                                            'capabilities': capabilities(version)}), VALIDATORS[version])

    def test_objects_control_only_from_0_22(self):
        for version in OLDER + ['0.99']:  # 0.99: unvendored, never assumed newer
            self.assertNotIn('objects.control', capabilities(version))
        self.assertEqual(set(capabilities('0.22')) - set(capabilities(PREVIOUS)), {'objects.control'})
        self.assertEqual(capabilities('0.22')[:len(GRANTS)], GRANTS)
        self.assertIn('quest.control', capabilities('0.22'))  # inherited
        with self.assertRaises(Exception):  # why it matters: 0.21 rejects the capability
            VALIDATORS[PREVIOUS].validate(request('session.hello', {'protocols': [PREVIOUS], 'client': {'id': 'com.hyprune.shell', 'name': 'x'},
                                                                    'capabilities': capabilities('0.22')}))


class HelloOnTheWire(unittest.IsolatedAsyncioTestCase):
    async def hello_params(self, version):
        captured = asyncio.get_running_loop().create_future()
        with tempfile.TemporaryDirectory() as tmp:
            path = tmp + '/core.sock'

            async def peer(reader, writer):
                msg = await read_frame(reader, VALIDATORS[version])
                if not captured.done(): captured.set_result(msg['params'])
                writer.close()
            server = await asyncio.start_unix_server(peer, path)
            os.chmod(path, 0o600)
            client = Client(path, lambda e: None, protocol=version)
            task = asyncio.create_task(client.run())
            try:
                async with asyncio.timeout(4):
                    return await captured
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                server.close(); await server.wait_closed()

    async def test_0_22_requests_objects_control(self):
        params = await self.hello_params('0.22')
        self.assertEqual(params['protocols'], ['0.22'])
        self.assertIn('objects.control', params['capabilities'])

    async def test_0_21_does_not(self):
        params = await self.hello_params(PREVIOUS)
        self.assertEqual(params['protocols'], [PREVIOUS])
        self.assertNotIn('objects.control', params['capabilities'])


class Allowlist(unittest.TestCase):
    def test_object_methods_only_from_0_22(self):
        for version in OLDER + ['0.99']:
            self.assertFalse(set(OBJECT_ACTIONS) & set(shell_actions(version)), version)
        self.assertEqual(set(shell_actions('0.22')) - set(shell_actions(PREVIOUS)), set(OBJECT_ACTIONS))
        self.assertTrue(set(QUEST_ACTIONS) <= set(shell_actions('0.22')))  # older actions are inherited

    def test_every_object_action_is_a_0_22_method(self):
        methods = V22.schema['$defs']['session.hello.result']['properties']['methods']['items']['enum']
        new = [m for m in methods if m.startswith(('objects.', 'libraries.'))]
        self.assertEqual(sorted(new), sorted(OBJECT_ACTIONS))
        for method in OBJECT_ACTIONS:
            self.assertIn(method + '.request', V22.schema['$defs'])
            self.assertNotIn(method + '.request', VALIDATORS[PREVIOUS].schema['$defs'])

    def test_results_and_refusals_echo_params(self):
        event = action_event('objects.pocket', {'ref': RACK}, {'revision': 4, 'itemId': 'pocket-2'})
        self.assertEqual(event['params'], {'ref': RACK})
        cmd = {'type': 'action', 'method': 'objects.transform', 'params': {'id': 'u-7c2e91', 'pose': POSE}}
        notice = action_notice(cmd, CoreError(-32007, 'the shape is inside a wall', {'retryable': False, 'rule': 'walls'}))
        self.assertEqual(notice['params'], cmd['params'])
        self.assertEqual(notice['message'], '-32007: the shape is inside a wall')
        self.assertEqual(notice['error'], {'code': -32007, 'message': 'the shape is inside a wall', 'rule': 'walls'})
        budget = action_notice({'type': 'action', 'method': 'objects.pocket', 'params': {'ref': RACK}},
                               CoreError(-32008, 'user placements: 128 per world', {'retryable': False, 'rule': 'budget'}))
        self.assertEqual(budget['error']['rule'], 'budget')
        plain = action_notice({'type': 'action', 'method': 'objects.remove', 'params': {'id': 'x'}}, CoreError(-32004, 'unknown id'))
        self.assertEqual(plain['error'], {'code': -32004, 'message': 'unknown id'})
        self.assertNotIn('error', action_notice({'type': 'action', 'method': 'surface.pocket', 'params': {}}, CoreError(-32004, 'x')))
        self.assertNotIn('error', action_notice({'type': 'action', 'method': 'objects.remove', 'params': {}}, RuntimeError('Unavailable')))


class Errors(unittest.IsolatedAsyncioTestCase):
    """Core's error.data (0.22: {retryable, rule?}) survives into the exception."""

    async def test_error_response_keeps_rule(self):
        client = Client('/unused', lambda e: None, protocol='0.22')
        client.request_resync = lambda: None
        future = asyncio.get_running_loop().create_future()
        client.pending['shell-1'] = future
        client.pending_methods['shell-1'] = 'objects.place'
        reader = asyncio.StreamReader()
        data = json.dumps({'jsonrpc': '2.0', 'id': 'shell-1', 'error': {'code': -32007, 'message': 'no free spot in front of you',
                                                                      'data': {'retryable': False, 'rule': 'keep-clear'}}}).encode()
        reader.feed_data(struct.pack('!I', len(data)) + data)
        reader.feed_eof()
        with self.assertRaises(asyncio.IncompleteReadError):
            await client.receive(reader)
        error = future.exception()
        self.assertIsInstance(error, CoreError)
        self.assertIsInstance(error, RuntimeError)  # existing handlers keep working
        self.assertEqual(str(error), '-32007: no free spot in front of you')
        self.assertEqual((error.code, error.message, error.rule), (-32007, 'no free spot in front of you', 'keep-clear'))
        self.assertIsNone(CoreError(-32004, 'unknown').rule)


class Wire(unittest.TestCase):
    """The shell's object and library payloads validate against 0.22 only."""

    def requests(self):
        user, authored = instance(), ARMILLARY
        moved = js('transformParams(%s, {x: 4, y: 0, z: -4.5, yaw: 90, scale: 1.5}, [0.5, 2]).params' % json.dumps(user))
        out = [('objects.catalog', {}), ('objects.pocket', {'ref': RACK}), ('objects.pocket', {'ref': 'user/street-lantern'}),
               ('objects.pocket', {'ref': 'package/armillary'}), ('objects.place', {'ref': RACK}),
               ('objects.place', {'ref': RACK, 'pose': POSE, 'scale': 1.5}), ('objects.transform', moved),
               ('objects.remove', {'all': True}), ('objects.reset', {'all': True}),
               ('libraries.list', {}), ('libraries.install', {'archive': '/tmp/starter.tar.zst', 'sha256': 'a' * 64}),
               ('libraries.remove', {'id': 'com.hyprune.starter', 'version': '0.1.0'})]
        for subject, action in [(user, 'remove'), (user, 'reset'), (user, 'lock'), (authored, 'hide'), (authored, 'reset'),
                                (instance(state='hidden', source='authored', id='bench'), 'hide'), (instance(locked=True), 'lock')]:
            made = js('sectionAction(%s, %s)' % (json.dumps(subject), json.dumps(action)))
            out.append((made['method'], made['params']))
        return out

    def test_requests(self):
        for method, params in self.requests():
            message = request(method, params)
            frame(message, V22)
            with self.assertRaises(Exception, msg=method):
                VALIDATORS[PREVIOUS].validate(message)

    def test_action_param_shapes(self):
        made = {(m, json.dumps(p, sort_keys=True)) for m, p in self.requests()}
        self.assertIn(('objects.hide', json.dumps({'hidden': True, 'id': 'sun-court-armillary'}, sort_keys=True)), made)
        self.assertIn(('objects.hide', json.dumps({'hidden': False, 'id': 'bench'}, sort_keys=True)), made)
        self.assertIn(('objects.configure', json.dumps({'id': 'u-7c2e91', 'patch': {'locked': True}}, sort_keys=True)), made)
        self.assertIn(('objects.configure', json.dumps({'id': 'u-7c2e91', 'patch': {'locked': False}}, sort_keys=True)), made)
        self.assertIn(('objects.reset', json.dumps({'id': 'sun-court-armillary'}, sort_keys=True)), made)
        self.assertIn(('objects.remove', json.dumps({'id': 'u-7c2e91'}, sort_keys=True)), made)

    def test_bad_requests_are_refused_before_sending(self):
        for method, params in [('objects.remove', {'id': 'u-7c2e91', 'all': True}), ('objects.reset', {}),
                               ('objects.configure', {'id': 'u-7c2e91', 'patch': {}}), ('objects.configure', {'id': 'x', 'patch': {'accent': 'red'}}),
                               ('objects.transform', {'id': 'x', 'pose': POSE, 'scale': 5}), ('objects.pocket', {'ref': 'server-rack'})]:
            with self.assertRaises(Exception, msg=(method, params)):
                frame(request(method, params), V22)

    def test_results(self):
        cases = [('objects.catalog', {'revision': 3, 'entries': CATALOG}), ('objects.pocket', {'revision': 4, 'itemId': 'pocket-2'}),
                 ('objects.place', {'revision': 5, 'id': 'u-1a2b3c'}), ('objects.transform', {'revision': 6}), ('objects.remove', {'revision': 7}),
                 ('objects.hide', {'revision': 8}), ('objects.reset', {'revision': 9}), ('objects.configure', {'revision': 10}),
                 ('libraries.list', {'libraries': [{'id': 'com.hyprune.starter', 'version': '0.1.0', 'name': 'Starter kit', 'formatVersion': '0.10',
                                                    'objects': 11, 'root': 'user', 'state': 'ready', 'errors': [], 'digest': 'b' * 64}]}),
                 ('libraries.install', {'revision': 11, 'id': 'com.hyprune.starter', 'version': '0.1.0'}), ('libraries.remove', {'revision': 12})]
        for method, result in cases:
            validate_response({'jsonrpc': '2.0', 'id': 'r', 'result': result}, method, V22)

    def test_state_and_editor(self):
        state = V22.schema['$defs']['state']
        self.assertIn('objects', state['required'])
        self.assertNotIn('objects', VALIDATORS[PREVIOUS].schema['$defs']['state']['properties'])
        definition(V22, 'objectsState').validate(STATE)
        editor = V22.schema['$defs']['editor']
        self.assertIn('node', editor['properties']['selectedKind']['enum'])
        self.assertNotIn('node', VALIDATORS[PREVIOUS].schema['$defs']['editor']['properties']['selectedKind']['enum'])
        definition(V22, 'unplaced').validate({'count': 2, 'windows': [{'surfaceId': 'w1', 'title': 'T', 'appClass': 'c', 'logicalSize': [800, 600]}],
                                              'selectedId': 'pocket-1', 'preview': True, 'objects': STATE['pocket']})
        with self.assertRaises(Exception):  # 0.21's queue has no object items
            definition(VALIDATORS[PREVIOUS], 'unplaced').validate({'count': 1, 'windows': [], 'selectedId': None, 'preview': False,
                                                                   'objects': STATE['pocket']})
        self.assertEqual(editor['properties']['gizmo']['required'], ['space', 'pivot', 'snap'])

    def test_error_rule_from_0_22(self):
        error = {'jsonrpc': '2.0', 'id': 'r', 'error': {'code': -32007, 'message': 'inside a wall', 'data': {'retryable': False, 'rule': 'walls'}}}
        V22.validate(error)
        with self.assertRaises(Exception):
            VALIDATORS[PREVIOUS].validate(error)


class Catalog(unittest.TestCase):
    """qml/Objects.js: catalog filters, search, card facts and the grid cursor."""

    def ids(self, filter_):
        return [e['id'] for e in js('filterCatalog(%s, %s)' % (json.dumps(CATALOG), json.dumps(filter_)))]

    def test_source_category_trait_filters_keep_core_order(self):
        self.assertEqual(self.ids({}), ['fern', 'server-rack', 'street-lantern', 'broken', 'guide'])
        self.assertEqual(self.ids({'source': 'all'}), self.ids({}))
        self.assertEqual(self.ids({'source': 'package'}), ['fern'])
        self.assertEqual(self.ids({'source': 'library'}), ['server-rack'])
        self.assertEqual(self.ids({'source': 'user'}), ['street-lantern', 'broken', 'guide'])
        self.assertEqual(self.ids({'category': 'lighting'}), ['street-lantern'])
        self.assertEqual(self.ids({'source': 'user', 'category': 'plants'}), [])
        self.assertEqual(self.ids({'trait': 'machine'}), ['server-rack'])
        self.assertEqual(js('filterCatalog(null, {})'), [])

    def test_search_over_names_and_tags(self):
        self.assertEqual(self.ids({'query': 'RACK'}), ['server-rack'])
        self.assertEqual(self.ids({'query': 'lamp'}), ['street-lantern'])  # a tag
        self.assertEqual(self.ids({'query': '  street   out '}), ['street-lantern'])  # every word, name or tag
        self.assertEqual(self.ids({'query': 'street rack'}), [])
        self.assertEqual(self.ids({'query': 'machines'}), [])  # categories are a filter, not search text
        self.assertEqual(self.ids({'query': 'r', 'source': 'user'}), ['street-lantern', 'broken'])

    def test_card_facts(self):
        self.assertEqual(js('categories(%s)' % json.dumps(CATALOG)), ['furniture', 'lighting', 'plants', 'machines', 'characters'])
        self.assertEqual(js('[sourceLabel("package"), sourceLabel("library"), sourceLabel("user"), sourceLabel("authored")]'),
                         ['World', 'Library', 'Mine', 'World'])
        self.assertEqual(js('sizeText(%s)' % json.dumps(entry()['bounds'])), '1.2 × 2.2 × 1.3 m')
        self.assertEqual(js("sizeText({min:[0,0,0],max:[0.45,0.9,0.456]})"), '0.45 × 0.9 × 0.46 m')
        self.assertEqual(js("sizeText({min:[0,0,0],max:[1,2,0.5]}, 2)"), '2 × 4 × 1 m')
        self.assertEqual(js('sizeText(null)'), '')
        self.assertEqual(js('[trianglesText(4210), trianglesText(880), trianglesText(52000), trianglesText(null)]'),
                         ['4.2k triangles', '880 triangles', '52k triangles', ''])
        self.assertEqual(js('costText(%s)' % json.dumps(entry())), '4.2k triangles  ·  1 MiB GPU')
        self.assertEqual(js('costText(%s)' % json.dumps(BROKEN)), '1 MiB GPU')  # triangles not measured
        self.assertEqual(js('costText(%s)' % json.dumps({**BROKEN, 'gpuBytes': None})), '')
        chips = js('traitChips(%s)' % json.dumps(['seat', 'decorative', 'machine', 'movable', 'collidable']))
        self.assertEqual([c['id'] for c in chips], ['movable', 'collidable', 'decorative', 'seat', 'machine'])
        self.assertTrue(all(c['glyph'] and c['label'] for c in chips))

    def test_notes_and_add(self):
        self.assertEqual(js('entryNote(%s)' % json.dumps(BROKEN)), {'level': 'error', 'lines': BROKEN['errors']})
        self.assertEqual(js('entryNote(%s)' % json.dumps({**BROKEN, 'errors': []})), {'level': 'error', 'lines': [BROKEN['reason']]})
        self.assertEqual(js('entryNote(%s)' % json.dumps(FERN)), {'level': 'muted', 'lines': [FERN['reason']]})
        self.assertEqual(js('entryNote(%s)' % json.dumps(entry())), {'level': '', 'lines': []})
        self.assertEqual(js('[%s].map(canAdd)' % ','.join(json.dumps(e) for e in CATALOG)), [False, True, True, False, False])
        self.assertEqual(js('entryFor(%s, "user/street-lantern").name' % json.dumps(CATALOG)), 'Street lantern')
        self.assertIsNone(js('entryFor(%s, null)' % json.dumps(CATALOG)))

    def test_grid_cursor(self):
        cases = [(0, 10, 4, 'next', 1), (9, 10, 4, 'next', 9), (0, 10, 4, 'previous', 0), (1, 10, 4, 'rowDown', 5),
                 (8, 10, 4, 'rowDown', 9), (5, 10, 4, 'rowUp', 1), (2, 10, 4, 'rowUp', 0), (5, 10, 4, 'home', 0), (2, 10, 4, 'end', 9),
                 (-1, 10, 4, 'next', 0), (3, 0, 4, 'next', -1), (7, 10, 4, 'other', 7)]
        got = js('[%s]' % ','.join('gridMove(%d,%d,%d,%s)' % (i, n, c, json.dumps(k)) for i, n, c, k, _ in cases))
        self.assertEqual(got, [want for *_, want in cases])


class Placed(unittest.TestCase):
    """The Placed list and the configure panel: section order, actions and transform params."""

    def test_section_order_includes_the_reserved_data_slot(self):
        self.assertEqual(js('SECTIONS'), ['transform', 'lock', 'remove', 'data'])
        for subject in [instance(), ARMILLARY, instance(locked=True, movable=False), instance(source='authored', id='statue', movable=False)]:
            sections = js('panelSections(%s)' % json.dumps(subject))
            self.assertEqual([s['id'] for s in sections], ['transform', 'lock', 'remove', 'data'])
            data = sections[3]
            self.assertEqual((data['title'], data['visible']), ('Data', False))  # listed; shown only for machines (with their catalog entry)
        self.assertEqual(js('panelSections(null)'), [])

    def test_instance_id_and_machine_data_source(self):
        self.assertEqual(js('idText(%s)' % json.dumps(instance())), 'ID  u-7c2e91')
        self.assertEqual(js('[idText(null), idText({})]'), ['', ''])
        rack = js('dataSource(%s, %s)' % (json.dumps(instance()), json.dumps(entry())))
        self.assertEqual(rack, {'id': 'u-7c2e91', 'sourceId': 'com.hyprune.sources.u-7c2e91', 'publishable': True,
                                'line': 'Data source id: u-7c2e91', 'hint': 'Publish to it from sources.json.'})
        self.assertIsNone(js('dataSource(%s, %s)' % (json.dumps(instance(ref='user/street-lantern')), json.dumps(LANTERN))))
        self.assertIsNone(js('dataSource(%s, null)' % json.dumps(instance())))
        # An authored id that is not a sources.json slug: bind it in machines.json instead.
        odd = js('dataSource(%s, %s)' % (json.dumps(instance(id='Court.Rack_1', source='authored')), json.dumps(entry())))
        self.assertEqual((odd['publishable'], odd['line'], odd['hint']),
                         (False, 'Data source id: Court.Rack_1', 'Bind it to a source in machines.json.'))
        data = js('panelSections(%s, %s)' % (json.dumps(instance()), json.dumps(entry())))[3]
        # A 0.22 / 0.23 catalog entry declares no inputs: the section shows the source and the editor.
        self.assertEqual((data['id'], data['title'], data['visible'], data['source'], data['declared']), ('data', 'Data source', True, rack, False))
        other = js('panelSections(%s, %s)' % (json.dumps(instance()), json.dumps(LANTERN)))[3]
        self.assertEqual((other['visible'], 'source' in other), (False, False))

    def test_sections_follow_source_lock_and_movable(self):
        user = {s['id']: s for s in js('panelSections(%s)' % json.dumps(instance()))}
        self.assertTrue(user['transform']['editable'])
        self.assertEqual([a['id'] for a in user['remove']['actions']], ['remove', 'reset'])
        self.assertEqual(user['remove']['title'], 'Remove / Reset')
        locked = {s['id']: s for s in js('panelSections(%s)' % json.dumps(instance(locked=True, movable=False)))}
        self.assertFalse(locked['transform']['editable'])
        self.assertIn('unlock', locked['transform']['note'].lower())
        self.assertEqual([a['enabled'] for a in locked['remove']['actions']], [False, False])
        self.assertTrue(locked['lock']['visible'] and locked['lock']['locked'])
        authored = {s['id']: s for s in js('panelSections(%s)' % json.dumps(ARMILLARY))}
        self.assertEqual([(a['id'], a['label']) for a in authored['remove']['actions']], [('hide', 'Hide'), ('reset', 'Reset')])
        self.assertEqual(authored['remove']['title'], 'Hide / Reset')
        hidden = {s['id']: s for s in js('panelSections(%s)' % json.dumps({**ARMILLARY, 'state': 'hidden', 'movable': False}))}
        self.assertEqual(hidden['remove']['actions'][0]['label'], 'Show')
        fixed = {s['id']: s for s in js('panelSections(%s)' % json.dumps(instance(source='authored', id='statue', movable=False)))}
        self.assertFalse(fixed['transform']['editable'])
        self.assertFalse(fixed['lock']['visible'])
        self.assertEqual([a['id'] for a in fixed['remove']['actions']], ['reset'])  # authored is never deleted or hidden

    def test_state_text(self):
        self.assertEqual(js('stateText(%s)' % json.dumps(instance(state='blocked', rule='walls'))), 'Blocked · inside a wall')
        self.assertEqual(js('[%s].map(stateLevel)' % ','.join(json.dumps(instance(state=s)) for s in ['active', 'hidden', 'missing', 'loading'])),
                         ['ok', 'muted', 'warning', 'busy'])
        self.assertEqual(js('selectedInstance(%s, "sun-court-armillary").name' % json.dumps(STATE['instances'])), 'Armillary')

    def test_yaw_round_trip_keeps_tilt(self):
        self.assertAlmostEqual(js('yawDegrees(%s)' % json.dumps(POSE['rotation'])), 30, places=3)
        q = js('withYaw([0,0,0,1], -90)')
        self.assertAlmostEqual(js('yawDegrees(%s)' % json.dumps(q)), -90, places=6)
        tilted = js('normalize([0.2, 0.3, 0.1, 0.9])')
        turned = js('withYaw(%s, 45)' % json.dumps(tilted))
        self.assertAlmostEqual(js('yawDegrees(%s)' % json.dumps(turned)), 45, places=4)
        self.assertAlmostEqual(sum(v * v for v in turned), 1, places=9)
        # The turn is about world Y: the object's up axis keeps its angle to world up.
        up = lambda q: 1 - 2 * (q[0] * q[0] + q[2] * q[2])  # y of the rotated +Y axis
        self.assertAlmostEqual(up(turned), up(tilted), places=9)

    def test_transform_params(self):
        user = instance()
        draft = js('transformDraft(%s)' % json.dumps(user))
        self.assertEqual(draft, {'x': 3.2, 'y': 0, 'z': -4.5, 'yaw': 30, 'scale': 1})
        self.assertEqual(js('transformParams(%s, %s)' % (json.dumps(user), json.dumps(draft))), {'params': None})
        moved = js('transformParams(%s, {x: "4,5", y: "0", z: -4.5, yaw: 30, scale: 1}).params' % json.dumps(user))
        self.assertEqual(moved, {'id': 'u-7c2e91', 'pose': {'position': [4.5, 0, -4.5], 'rotation': POSE['rotation']}})  # yaw kept exactly
        scaled = js('transformParams(%s, {x: 3.2, y: 0, z: -4.5, yaw: 30, scale: 9}, [0.5, 2]).params' % json.dumps(user))
        self.assertEqual(scaled['scale'], 2)
        self.assertEqual(js('transformParams(%s, {x: 3.2, y: 0, z: -4.5, yaw: 30, scale: 0.1}).params.scale' % json.dumps(user)), 0.25)
        turned = js('transformParams(%s, {x: 3.2, y: 0, z: -4.5, yaw: 120, scale: 1}).params' % json.dumps(user))
        self.assertNotIn('scale', turned)
        self.assertAlmostEqual(js('yawDegrees(%s)' % json.dumps(turned['pose']['rotation'])), 120, places=6)
        # Authored scale outside 0.25..4 is left alone while it is not edited.
        tiny = instance(source='authored', id='pebble', scale=0.1)
        self.assertNotIn('scale', js('transformParams(%s, {x: 9, y: 0, z: -4.5, yaw: 30, scale: 0.1}).params' % json.dumps(tiny)))
        for bad in [{'x': 'abc'}, {'y': ''}, {'z': 200000}, {'yaw': 'NaN'}]:
            self.assertIn('error', js('transformParams(%s, %s)' % (json.dumps(user), json.dumps({**draft, **bad}))), bad)

    def test_usage_rows(self):
        rows = js('usageRows(%s, %s)' % (json.dumps(USAGE), json.dumps(LIMITS)))
        self.assertEqual([r['text'] for r in rows], ['3 / 128', '12k / 400k', '4.2 / 192'])
        self.assertEqual(js('usageText(%s, %s)' % (json.dumps(USAGE), json.dumps(LIMITS))),
                         '3 / 128 placements  ·  12k / 400k triangles  ·  4.2 / 192 MiB GPU')
        full = js('usageRows(%s, %s)[0].fraction' % (json.dumps({**USAGE, 'placements': 128}), json.dumps(LIMITS)))
        self.assertEqual(full, 1)
        self.assertEqual(js('usageRows(null, null)'), [])


class Feedback(unittest.TestCase):
    def test_error_toasts_use_core_words_and_rule(self):
        toast = js('errorToast("objects.transform", {code: -32007, message: "the shape is inside a wall", rule: "walls"}, "")')
        self.assertEqual((toast['kind'], toast['category'], toast['tone']), ('toast', 'objects', 'warning'))
        self.assertEqual(toast['line'], 'the shape is inside a wall')
        self.assertEqual(toast['detail'], 'Rule: inside a wall')
        self.assertLessEqual(toast['durationMs'], 5000)
        budget = js('errorToast("objects.pocket", {code: -32008, message: "user placements: 128 per world", rule: "budget"}, "")')
        self.assertEqual((budget['line'], budget['detail']), ('user placements: 128 per world', ''))
        fallback = js('errorToast("libraries.install", null, "-32602: archive hash mismatch")')
        self.assertEqual((fallback['title'], fallback['line']), ('Library', 'archive hash mismatch'))

    def test_pocket_toast_and_results(self):
        toast = js('pocketToast("Server rack")')
        self.assertEqual((toast['title'], toast['line']), ('Server rack', 'In your pocket — place it with tool 5'))
        self.assertEqual(js('resultText("objects.remove", {all: true})'), 'Your objects in this world are removed.')
        self.assertEqual(js('resultText("objects.reset", {all: true})'), 'Authored objects are shown and reset.')
        self.assertEqual(js('resultText("objects.hide", {id: "a", hidden: false})'), 'Shown again.')
        self.assertIsNone(js('resultText("objects.catalog", {})'))


class PocketHud(unittest.TestCase):
    """Tool 5 HUD: object items share the pocket queue after the windows (editor.unplaced)."""

    WINDOWS = [{'surfaceId': 'w1', 'title': 'Terminal', 'appClass': 'foot', 'logicalSize': [800, 600]}]

    def presentation(self, unplaced):
        return evaluate(MANIPULATION, 'presentation(%s).placement' % json.dumps({'editor': {'tool': 5, 'unplaced': unplaced}}))

    def test_selected_object_item(self):
        placement = self.presentation({'count': 3, 'windows': self.WINDOWS, 'selectedId': 'pocket-2', 'preview': True,
                                       'objects': [{'itemId': 'pocket-1', 'ref': RACK, 'name': 'Server rack'},
                                                   {'itemId': 'pocket-2', 'ref': 'user/street-lantern', 'name': 'Street lantern'}]})
        self.assertEqual(placement['index'], 2)
        self.assertIsNone(placement['app'])
        self.assertEqual(placement['object'], {'itemId': 'pocket-2', 'ref': 'user/street-lantern', 'name': 'Street lantern', 'selected': True})
        self.assertEqual([o['selected'] for o in placement['objects']], [False, True])
        self.assertEqual(placement['count'], 3)

    def test_selected_window_and_older_peers(self):
        placement = self.presentation({'count': 2, 'windows': self.WINDOWS, 'selectedId': 'w1', 'preview': False,
                                       'objects': [{'itemId': 'pocket-1', 'ref': RACK, 'name': 'Server rack'}]})
        self.assertEqual((placement['index'], placement['app']['title'], placement['object']), (0, 'Terminal', None))
        old = self.presentation({'count': 1, 'windows': self.WINDOWS, 'selectedId': 'w1', 'preview': False})  # 0.21: no objects
        self.assertEqual((old['index'], old['objects'], old['object']), (0, [], None))
        self.assertEqual(js('[isObjectItem("pocket-3"), isObjectItem("w1"), isObjectItem(null)]'), [True, False, False])
        self.assertEqual(js('pocketObjects(%s)' % json.dumps({'selectedId': 'pocket-1', 'objects': STATE['pocket']})),
                         [{**STATE['pocket'][0], 'selected': True}])
        self.assertEqual(js('pocketObjects(null)'), [])


class Presentation(unittest.TestCase):
    """The Objects tab and HUD wiring in QML (source checks; the nested captures render them)."""

    def read(self, name): return (ROOT / 'qml' / name).read_text()

    def test_tab_after_quests_and_named_controls(self):
        director = self.read('components/Director.qml')
        self.assertRegex(director, r"'Quests', 'Objects', '")  # Library (RFC-0015) follows Objects
        self.assertIn('DirectorObjects { anchors.fill: parent; visible: ShellState.tab === ShellState.tabObjects }', director)
        page = self.read('components/DirectorObjects.qml')
        for name in ["objectName: 'directorObjects'", "objectName: 'objectsView'", "objectName: 'objectsSource'", "objectName: 'objectsCategory'",
                     "objectName: 'objectsSearch'", "objectName: 'objectsCatalog'", "objectName: 'objectsPlaced'", "'placedRow:' + modelData.id",
                     "objectName: 'objects-reset-all'", "objectName: 'objects-remove-all'", "objectName: 'objectsUsage'"]:
            self.assertIn(name, page)
        card = self.read('components/ObjectCard.qml')
        self.assertIn("objectName: 'objectAdd:' + (card.entry ? card.entry.ref : '')", card)
        self.assertIn("'file://' + card.entry.thumbnail", card)
        self.assertIn("ShellState.objectsCan('objects.pocket')", card)

    def test_panel_is_built_from_the_section_list(self):
        panel = self.read('components/ObjectConfigure.qml')
        self.assertIn('Objects.panelSections(instance, entry)', panel)
        self.assertIn('onEntryChanged: refreshSections()', panel)
        for name in ["objectName: 'objectId'", 'Objects.idText(panel.instance)', 'ObjectDataSource {']:
            self.assertIn(name, panel)
        body = self.read('components/ObjectDataSource.qml')  # the Data source section (tests/test_sources.py)
        for name in ["objectName: 'objectDataSource'", "objectName: 'objectDataHint'", 'body.source.line', 'body.source.hint']:
            self.assertIn(name, body)
        page = self.read('components/DirectorObjects.qml')
        self.assertIn("objectName: 'placedId'", page)
        self.assertIn("text: row.modelData.id", page)
        self.assertRegex(panel, r"Repeater \{\s*id: sectionRepeater\s*model: panel\.sections")
        self.assertIn("objectName: 'objectSection:' + modelData.id", panel)

    def test_state_refreshes_catalog_and_toasts_errors(self):
        state = self.read('ShellState.qml')
        self.assertIn("action('objects.catalog', {})", state)
        self.assertIn('objectsState.catalogRevision !== objectCatalogFor', state)
        self.assertIn("onObjectsVisibleChanged", state)
        self.assertRegex(state, r"/\^\(objects\|libraries\)\\\\?\.\/\.test\(msg\.method")
        self.assertIn('Objects.errorToast(msg.method, msg.error || null, msg.message)', state)

    def test_hud_lists_pocket_objects(self):
        deck = self.read('components/ToolDeck.qml')
        self.assertIn("objectName: 'hudPocketObjects'", deck)
        self.assertIn('CubeGlyph', deck)
        self.assertIn('CubeGlyph', self.read('components/PlacementInfo.qml'))


if __name__ == '__main__':
    unittest.main()
