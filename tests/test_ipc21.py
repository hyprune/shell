"""IPC 0.21 (RFC-0012): quest.control grant negotiation, quest/focus/guidance actions, the
markers/quests/focus state keys, quest.progress and focus.phase events, the clock offset,
and the pure helpers in qml/Quests.js (tested with node).

Wire checks run against the vendored 0.21 pin; older pins must refuse the new shapes."""
import asyncio
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bridge'))
from client import Client, GRANTS, QUEST_EVENTS, capabilities  # noqa: E402
from launch import QUEST_ACTIONS, action_event, action_notice, shell_actions  # noqa: E402
from protocol import VALIDATORS, SUPPORTED_PROTOCOLS, frame, read_frame, validate_response  # noqa: E402

QUESTS = (ROOT / 'qml/Quests.js').read_text()
PLAYER = (ROOT / 'qml/PlayerSettings.js').read_text()
OLDER = [v for v in SUPPORTED_PROTOCOLS if int(v.split('.')[1]) < 21]
PREVIOUS = OLDER[-1]
V21 = VALIDATORS['0.21']
REF = {'source': 'personal', 'id': 'release-notes'}


def evaluate(script, expression, *args):
    return json.loads(subprocess.check_output(
        ['node', '-e', script + '\nconsole.log(JSON.stringify(' + expression + '));', *args], text=True))


def js(expression, *args):
    return evaluate(QUESTS, expression, *args)


def request(method, params, rid='r'):
    return {'jsonrpc': '2.0', 'id': rid, 'method': method, 'params': params}


def definition(validator, name):
    return validator.evolve(schema={'$ref': validator.schema['$id'] + '#/$defs/' + name})


def minor(version):
    return int(version.split('.')[1])


DETAIL = {
    'questRef': REF, 'title': 'Release notes', 'summary': 'Ship them', 'category': 'personal', 'state': 'active',
    'tracked': True, 'sequential': True, 'expires': None, 'createdAt': '2026-10-12T09:00', 'updatedAt': '2026-10-12T10:00',
    'completedAt': None, 'personal': True,
    'steps': [
        {'id': 'draft', 'title': 'Draft', 'optional': False, 'any': False, 'state': 'done', 'target': None,
         'objectives': [{'id': 'done', 'type': 'manual', 'label': 'Done', 'count': 1, 'done': 1}]},
        {'id': 'write', 'title': 'Write', 'optional': False, 'any': False, 'state': 'current', 'target': {'areaId': 'sun-court'},
         'objectives': [{'id': 'focus', 'type': 'focus', 'label': '2 focus sessions', 'count': 1, 'done': 1, 'sessions': 2, 'creditedMinutes': 21.5},
                        {'id': 'done', 'type': 'manual', 'label': 'Done', 'count': 1, 'done': 0}]},
        {'id': 'publish', 'title': 'Publish', 'optional': False, 'any': False, 'state': 'pending', 'target': {'placeId': 'lookout'},
         'objectives': [{'id': 'done', 'type': 'manual', 'label': 'Done', 'count': 1, 'done': 0}]}]}


def summary(id, state, tracked=False, updated='2026-10-12T10:00', title=None):
    return {'questRef': {'source': 'personal', 'id': id}, 'title': title or id.title(), 'category': 'personal', 'state': state,
            'tracked': tracked, 'step': None, 'progress': [0, 1], 'offWorld': False, 'updatedAt': updated}


FOCUS = {'state': 'work', 'pausedState': None, 'sessionId': 'focus-1a2b', 'phaseStartedAtMs': 100000, 'phaseEndsAtMs': 1600000,
         'phaseMs': 1500000, 'remainingMs': 1500000, 'creditedMs': 300000, 'crediting': True, 'cycle': 2, 'cycles': 4,
         'breakKind': None, 'countMode': 'focus', 'target': {'kind': 'any', 'label': 'Any window'}, 'calm': True}
MARKERS = {'reveal': {'startedAtMs': 5000, 'holdMs': 4000, 'fadeMs': 600, 'reason': 'tap'}, 'persistent': 'edge', 'calm': False,
           'coreDraw': True,
           'list': [{'id': 'quest:personal/release-notes/write/done', 'kind': 'quest', 'tier': 1, 'label': 'Write', 'icon': 'quest',
                     'target': {'areaId': 'sun-court'}, 'position': [4, 3.2, -10], 'areaId': 'sun-court', 'range': [2, 400],
                     'labelRange': 120, 'occlusion': 'through', 'tracked': True,
                     'source': {'questId': 'personal/release-notes', 'stepId': 'write', 'objectiveId': 'done'}},
                    {'id': 'workspace:21', 'kind': 'workspace', 'tier': 3, 'label': 'Workshop', 'icon': 'workspace',
                     'target': {'workspaceId': 21}, 'position': [9, 2, 1], 'areaId': None, 'range': [0, 150],
                     'labelRange': 120, 'occlusion': 'edge', 'tracked': False, 'source': {'workspaceId': 21}}]}
QUESTS_STATE = {'enabled': True, 'tracked': REF, 'counts': {'available': 0, 'active': 1, 'completed': 3}, 'world': None,
                'active': [{'id': 'release-notes', 'source': 'personal', 'title': 'Release notes',
                            'step': {'id': 'write', 'title': 'Write', 'progress': [1, 2]}, 'progress': [1, 3]}]}
GUIDANCE = {
    'config': {'markers.reveal_ms': 4000, 'markers.reveal_mode': 'timer', 'markers.max_revealed': 12, 'markers.labels': 5,
               'markers.persistent': 'edge', 'markers.core_draw': True, 'quests.notifications': 'all', 'focus.work_min': 25,
               'focus.short_break_min': 5, 'focus.long_break_min': 15, 'focus.long_break_every': 4, 'focus.cycles': 4,
               'focus.auto_start_breaks': True, 'focus.auto_start_work': False, 'focus.count_mode': 'focus', 'focus.idle_s': 180,
               'focus.grace_s': 30, 'focus.calm': True, 'focus.calm_npc_distance': 6, 'focus.desktop_chip': False,
               'focus.history_days': 90},
    'ranges': {'markers.reveal_ms': [1000, 15000], 'markers.max_revealed': [4, 16], 'markers.labels': [2, 8], 'focus.work_min': [5, 120],
               'focus.short_break_min': [1, 30], 'focus.long_break_min': [5, 60], 'focus.long_break_every': [2, 12],
               'focus.cycles': [1, 12], 'focus.idle_s': [60, 900], 'focus.grace_s': [0, 120], 'focus.calm_npc_distance': [2, 20],
               'focus.history_days': [0, 365]},
    'options': {'markers.reveal_mode': ['timer', 'toggle'], 'markers.persistent': ['off', 'edge', 'always'],
                'quests.notifications': ['all', 'important', 'off'], 'focus.count_mode': ['focus', 'wall']},
    'path': '/tmp/guidance.json', 'error': ''}
GUIDANCE['defaults'] = dict(GUIDANCE['config'])
GUIDANCE['overrides'] = {}


class Grants(unittest.TestCase):
    """quest.control is requested only where the offered protocol defines it: an older core
    rejects an unknown capability (-32602), so every pin must accept the shell's hello."""

    def test_hello_validates_against_every_pin(self):
        for version in SUPPORTED_PROTOCOLS:
            hello = request('session.hello', {'protocols': [version], 'client': {'id': 'com.hyprune.shell', 'name': 'Hyprune shell'},
                                              'capabilities': capabilities(version)})
            frame(hello, VALIDATORS[version])

    def test_quest_control_only_from_0_21(self):
        for version in OLDER + ['0.99']:  # 0.99: unvendored, never assumed newer
            self.assertNotIn('quest.control', capabilities(version))
        self.assertIn('quest.control', capabilities('0.21'))
        self.assertEqual(capabilities('0.21')[:len(GRANTS)], GRANTS)
        self.assertEqual(set(capabilities('0.21')) - set(capabilities(PREVIOUS)), {'quest.control'})
        self.assertNotIn('input.control', capabilities('0.5'))
        self.assertIn('input.control', capabilities('0.6'))
        with self.assertRaises(Exception):  # why it matters: 0.20 rejects the capability
            VALIDATORS[PREVIOUS].validate(request('session.hello', {'protocols': [PREVIOUS], 'client': {'id': 'com.hyprune.shell', 'name': 'x'},
                                                                    'capabilities': capabilities('0.21')}))


class HelloOnTheWire(unittest.IsolatedAsyncioTestCase):
    """The bridge offers exactly its pin and requests quest.control only at 0.21."""

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

    async def test_0_21_requests_quest_control(self):
        params = await self.hello_params('0.21')
        self.assertEqual(params['protocols'], ['0.21'])
        self.assertIn('quest.control', params['capabilities'])
        self.assertIn('input.control', params['capabilities'])

    async def test_0_20_does_not(self):
        params = await self.hello_params(PREVIOUS)
        self.assertEqual(params['protocols'], [PREVIOUS])
        self.assertNotIn('quest.control', params['capabilities'])


class Allowlist(unittest.TestCase):
    def test_quest_methods_only_from_0_21(self):
        for version in OLDER + ['0.99']:
            self.assertFalse(set(QUEST_ACTIONS) & set(shell_actions(version)), version)
        self.assertEqual(set(shell_actions('0.21')) - set(shell_actions(PREVIOUS)), set(QUEST_ACTIONS))
        self.assertIn('surface.pocket', shell_actions('0.21'))  # older actions are inherited

    def test_every_quest_action_is_a_0_21_method(self):
        methods = V21.schema['$defs']['session.hello.result']['properties']['methods']['items']['enum']
        for method in QUEST_ACTIONS:
            self.assertIn(method, methods)
            self.assertIn(method + '.request', V21.schema['$defs'])
            self.assertNotIn(method + '.request', VALIDATORS[PREVIOUS].schema['$defs'])

    def test_results_echo_params_for_quest_methods_only(self):
        event = action_event('quests.get', {'questRef': REF}, {'quest': DETAIL})
        self.assertEqual(event['params'], {'questRef': REF})
        self.assertNotIn('params', action_event('player.get', {}, {}))
        notice = action_notice({'type': 'action', 'method': 'quests.mark', 'params': {'questRef': REF}}, RuntimeError('-32004: not current'))
        self.assertEqual(notice['params'], {'questRef': REF})
        self.assertEqual(notice['method'], 'quests.mark')
        self.assertNotIn('params', action_notice({'type': 'action', 'method': 'surface.pocket', 'params': {}}, RuntimeError('x')))


class Wire(unittest.TestCase):
    """The shell's quest, focus and guidance payloads validate against 0.21 only."""

    REQUESTS = [
        ('markers.reveal', {}), ('guidance.get', {}), ('guidance.set', {'patch': {'focus.work_min': 50, 'markers.labels': None}}),
        ('quests.list', {}), ('quests.get', {'questRef': REF}), ('quests.track', {'questRef': REF}), ('quests.track', {'questRef': None}),
        ('quests.accept', {'questRef': REF}), ('quests.abandon', {'questRef': REF}), ('quests.resume', {'questRef': REF}),
        ('quests.delete', {'questRef': REF}), ('quests.mark', {'questRef': REF, 'stepId': 'write', 'objectiveId': 'done'}),
        ('focus.start', {}), ('focus.start', {'questRef': REF}), ('focus.start', {'questRef': REF, 'objectiveId': 'focus'}),
        ('focus.pause', {}), ('focus.resume', {}), ('focus.skip', {}), ('focus.stop', {}), ('focus.history', {'days': 7})]

    def test_requests(self):
        for method, params in self.REQUESTS:
            message = request(method, params)
            frame(message, V21)
            with self.assertRaises(Exception, msg=method):
                VALIDATORS[PREVIOUS].validate(message)

    def test_results(self):
        cases = [('quests.list', {'quests': [summary('a', 'active', True), summary('b', 'completed')]}),
                 ('quests.get', {'quest': DETAIL}), ('guidance.get', GUIDANCE), ('guidance.set', GUIDANCE),
                 ('quests.create', {'revision': 4, 'questRef': REF}), ('quests.mark', {'revision': 5}),
                 ('focus.start', {'revision': 6, 'sessionId': 'focus-9f'}), ('focus.stop', {'revision': 7})]
        for method, result in cases:
            validate_response({'jsonrpc': '2.0', 'id': 'r', 'result': result}, method, V21)

    def test_state_keys(self):
        state = V21.schema['$defs']['state']
        for key in ['markers', 'quests', 'focus']:
            self.assertIn(key, state['required'])
            self.assertNotIn(key, VALIDATORS[PREVIOUS].schema['$defs']['state']['properties'])
        definition(V21, 'markersState').validate(MARKERS)
        definition(V21, 'questsState').validate(QUESTS_STATE)
        definition(V21, 'focusState').validate(FOCUS)

    def test_events_are_0_21_notifications(self):
        events = V21.schema['$defs']['session.hello.result']['properties']['events']['items']['enum']
        for name in QUEST_EVENTS:
            self.assertIn(name, events)
            self.assertIn(name + '.notification', V21.schema['$defs'])
            self.assertNotIn(name + '.notification', VALIDATORS[PREVIOUS].schema['$defs'])

    def test_overlay_style_quest_colour_from_0_21(self):
        tokens = ("{mono:'DejaVu Sans Mono',accent:{r:.84,g:.9,b:.98},text:{r:.95,g:.96,b:.98},gold:{r:.87,g:.78,b:.6},"
                  "reticle:{r:.965,g:.961,b:.918},positive:{r:.349,g:.949,b:.6},warning:{r:1,g:.62,b:.349},quest:{r:1,g:.7804,b:.302}}")
        new = evaluate(PLAYER, 'overlayStyle(%s, 21)' % tokens)
        old = evaluate(PLAYER, 'overlayStyle(%s, 20)' % tokens)
        self.assertEqual(new['questColor'], [1, 0.7804, 0.302])
        self.assertNotIn('questColor', old)
        frame(request('overlay.style', {'leaseId': 'lease-1', 'style': new}), V21)
        frame(request('overlay.style', {'leaseId': 'lease-1', 'style': old}), VALIDATORS[PREVIOUS])
        with self.assertRaises(Exception):
            VALIDATORS[PREVIOUS].validate(request('overlay.style', {'leaseId': 'lease-1', 'style': new}))


class Events(unittest.IsolatedAsyncioTestCase):
    """quest.progress and focus.phase reach QML as transient hints for this session only."""

    def client(self, version='0.21'):
        events = []
        client = Client('/unused', events.append, protocol=version)
        client.session = 'session'
        client.ready = True
        client.hello = {'events': ['state.delta', 'runtime.notice', 'session.revoked'] + (QUEST_EVENTS if minor(version) >= 21 else []),
                        'methods': []}
        return client, events

    async def feed(self, client, *messages):
        reader = asyncio.StreamReader()
        for m in messages:
            data = json.dumps(m).encode()
            reader.feed_data(struct.pack('!I', len(data)) + data)
        reader.feed_eof()
        with self.assertRaises(asyncio.IncompleteReadError):
            await client.receive(reader)

    def note(self, method, params):
        return {'jsonrpc': '2.0', 'method': method, 'params': {**params, 'sessionId': 'session', 'revision': 3}}

    async def test_forwarded(self):
        client, events = self.client()
        step = {'questRef': REF, 'kind': 'step', 'title': 'Release notes', 'stepId': 'draft', 'stepTitle': 'Draft', 'nextStepTitle': 'Write'}
        phase = {'focusSessionId': 'focus-1a', 'phase': 'break', 'cycle': 1, 'cycles': 4, 'creditedMs': 1440000, 'breakKind': 'short',
                 'suggestion': {'markerId': 'break:lookout', 'label': 'North lookout'}}
        await self.feed(client, self.note('quest.progress', step), self.note('focus.phase', phase))
        self.assertEqual([e['type'] for e in events], ['quest.progress', 'focus.phase'])
        self.assertEqual(events[0]['value']['stepTitle'], 'Draft')
        self.assertEqual(events[1]['value']['suggestion']['label'], 'North lookout')

    async def test_other_session_and_invalid_are_dropped(self):
        client, events = self.client()
        other = self.note('quest.progress', {'questRef': REF, 'kind': 'completed', 'title': 'X'})
        other['params']['sessionId'] = 'old'
        bad = self.note('focus.phase', {'focusSessionId': 'nope', 'phase': 'work', 'cycle': 1, 'cycles': 4, 'creditedMs': 0})
        client.request_resync = lambda: None
        await self.feed(client, other, bad)
        self.assertEqual([e['type'] for e in events if e['type'] in QUEST_EVENTS], [])
        self.assertEqual(client.invalid_frames, 1)  # the invalid frame is quarantined, not presented

    async def test_unadvertised_before_0_21(self):
        client, events = self.client(PREVIOUS)
        client.request_resync = lambda: None
        await self.feed(client, self.note('quest.progress', {'questRef': REF, 'kind': 'completed', 'title': 'X'}))
        self.assertFalse([e for e in events if e['type'] in QUEST_EVENTS])


class Clock(unittest.IsolatedAsyncioTestCase):
    def test_local_estimate_then_ping_sample(self):
        events = []
        client = Client('/unused', events.append, protocol='0.21')
        with patch('client.time.monotonic', return_value=50.0), patch('client.time.time', return_value=1000.0):
            client.publish_clock()
        self.assertEqual(events[-1], {'type': 'clock', 'offsetMs': 50000 - 1000000})
        client.publish_clock(51234, 1000100)
        self.assertEqual(events[-1]['offsetMs'], 51234 - 1000100)
        count = len(events)
        client.publish_clock(51235, 1000100)  # sub-2 ms jitter is not republished
        self.assertEqual(len(events), count)

    async def test_ping_measures_offset(self):
        events = []
        client = Client('/unused', events.append, protocol='0.21')

        async def call(method, params, bootstrap=False):
            self.assertEqual(method, 'session.ping')
            return {'monotonicMs': 777000}
        client.call = call
        times = iter([2000.0, 2000.02])
        with patch('client.time.time', side_effect=lambda: next(times)):
            await client.ping()
        self.assertAlmostEqual(events[-1]['offsetMs'], 777000 - 2000010, places=0)


class Helpers(unittest.TestCase):
    """qml/Quests.js: grouping, details, targets, the form, focus timing, notifications."""

    def test_grouping_tracked_first_and_collapsed_groups(self):
        quests = [summary('old', 'active', updated='2026-10-10T08:00'), summary('new', 'active', updated='2026-10-12T08:00'),
                  summary('mine', 'active', True, updated='2026-10-01T08:00'), summary('offer', 'available'),
                  summary('done', 'completed'), summary('gone', 'abandoned'), summary('late', 'failed', updated='2026-10-11T08:00')]
        groups = js('groupQuests(%s)' % json.dumps(quests))
        self.assertEqual([g['id'] for g in groups], ['active', 'available', 'completed', 'closed'])
        self.assertEqual([q['questRef']['id'] for q in groups[0]['quests']], ['mine', 'new', 'old'])
        self.assertEqual([q['questRef']['id'] for q in groups[3]['quests']], ['gone', 'late'])
        self.assertEqual([g['collapsed'] for g in groups], [False, False, True, True])
        rows = js('rows(groupQuests(%s), {})' % json.dumps(quests))
        self.assertEqual([r['type'] for r in rows], ['header', 'quest', 'quest', 'quest', 'header', 'quest', 'header', 'header'])
        self.assertEqual(rows[1]['key'], 'personal/mine')
        opened = js('rows(groupQuests(%s), {completed: true, active: false})' % json.dumps(quests))
        self.assertEqual([r.get('key') for r in opened], [None, None, 'personal/offer', None, 'personal/done', None])
        self.assertEqual(js('[move([1,2,3], -1, 1), move([1,2,3], 2, 1), move([1,2,3], 0, -1), move([], 0, 1)]'), [0, 2, 0, -1])
        self.assertEqual(js('groupQuests(null)[0].quests'), [])

    def test_objective_progress_and_keys(self):
        objectives = DETAIL['steps'][1]['objectives']
        self.assertEqual(js('objectiveProgress(%s)' % json.dumps(objectives[0])), '1 / 2 sessions')
        self.assertEqual(js("objectiveProgress({type:'focus',sessions:1,count:1,done:0})"), '0 / 1 session')
        self.assertEqual(js("[objectiveProgress({type:'manual',count:1,done:0}), objectiveProgress({type:'manual',count:1,done:1}),"
                            "objectiveProgress({type:'manual',count:3,done:2}), objectiveProgress({type:'reach',count:1,done:1})]"),
                         ['To do', 'Done', '2 / 3', 'Reached'])
        self.assertEqual(js('firstObjective(%s, "manual")' % json.dumps(DETAIL))['objectiveId'], 'done')
        self.assertEqual(js('firstObjective(%s, "focus")' % json.dumps(DETAIL)), {'stepId': 'write', 'objectiveId': 'focus', 'objective': objectives[0]})
        self.assertIsNone(js('firstObjective(%s, "reach")' % json.dumps(DETAIL)))
        actions = js('questActions(%s)' % json.dumps(DETAIL))
        self.assertEqual(actions, {'accept': False, 'abandon': True, 'resume': False, 'track': True, 'edit': True, 'remove': True})
        self.assertTrue(js("questActions({state:'abandoned',personal:false}).resume"))

    def test_targets_resolve_to_waypoints(self):
        ctx = {'markers': MARKERS, 'places': [{'id': 'lookout', 'name': 'North lookout', 'position': [1, 5, 2]}],
               'zones': [{'id': 'hall', 'name': 'Hall', 'bounds': {'min': [0, 0, 0], 'max': [10, 4, 6]}}], 'worldId': 'w'}
        cases = [({'areaId': 'sun-court'}, {'questKey': 'personal/release-notes', 'stepId': 'write'}, [4, 3.2, -10]),
                 ({'workspaceId': 21}, {}, [9, 2, 1]),  # resolved through core's workspace marker
                 ({'placeId': 'lookout'}, {}, [1, 5, 2]),
                 ({'zoneId': 'hall'}, {}, [5, 1.7, 3]),
                 ({'position': [7, 1, 7]}, {}, [7, 1, 7])]
        for target, extra, want in cases:
            got = js('resolveTarget(%s, %s)' % (json.dumps(target), json.dumps({**ctx, **extra})))
            self.assertEqual(got['position'], want, target)
        self.assertIsNone(js('resolveTarget({workspaceId: 99}, %s)' % json.dumps(ctx)))  # no home here
        self.assertIsNone(js('resolveTarget({position:[1,2,3], worldId:"other"}, %s)' % json.dumps(ctx)))
        wp = js('waypointParams(resolveTarget({zoneId:"hall"}, %s), "quest-x", "")' % json.dumps(ctx))
        self.assertEqual(wp, {'id': 'quest-x', 'label': 'Hall', 'target': {'zoneId': 'hall'}})
        frame(request('waypoint.set', wp), V21)
        wp = js('waypointParams(resolveTarget({workspaceId:21}, %s), "quest-y", "Workshop")' % json.dumps(ctx))
        frame(request('waypoint.set', wp), V21)
        self.assertEqual(wp['target'], {'position': [9, 2, 1]})
        self.assertEqual(js("targetText({workspaceId:21})"), 'Workspace 21')
        self.assertEqual(js("targetText({placeId:'lookout'}, %s)" % json.dumps(ctx)), 'North lookout')

    def test_form_one_step_per_line(self):
        self.assertEqual(js('parseSteps(process.argv[1])', '  - Draft  \n\n* Review it\n2) Publish\n\t\n• Celebrate'),
                         ['Draft', 'Review it', 'Publish', 'Celebrate'])
        self.assertEqual(len(js('parseSteps(process.argv[1])', '\n'.join('s%d' % i for i in range(20)))), 16)
        self.assertEqual(js('parseSteps(process.argv[1])', 'x' * 80), ['x' * 64])
        form = {'title': '  Release   notes ', 'summary': 'For 0.9', 'steps': 'Draft\nDraft\nPublish!', 'targetKind': 'workspace',
                'targetValue': '21', 'sessions': {'Draft': 2}}
        quest = js('questInput(%s)' % json.dumps(form))
        self.assertEqual(quest['title'], 'Release notes')
        self.assertEqual([s['id'] for s in quest['steps']], ['draft', 'draft-2', 'publish'])
        self.assertEqual(quest['steps'][0]['objectives'], [{'id': 'focus', 'type': 'focus', 'sessions': 2}])
        self.assertNotIn('objectives', quest['steps'][2])  # default: one manual objective
        self.assertTrue(all(s['target'] == {'workspaceId': 21} for s in quest['steps']))
        frame(request('quests.create', {'quest': quest}), V21)
        bare = js('questInput({title: "Call the bank", steps: ""})')
        self.assertEqual(bare, {'title': 'Call the bank', 'steps': [{'id': 'call-the-bank', 'title': 'Call the bank'}]})
        frame(request('quests.create', {'quest': bare}), V21)
        for kind, value in [('area', 'sun-court'), ('place', 'lookout')]:
            q = js('questInput(%s)' % json.dumps({'title': 'T', 'steps': 'A', 'targetKind': kind, 'targetValue': value}))
            frame(request('quests.create', {'quest': q}), V21)
        self.assertEqual(js("[formError({title:''}), formError({title:'x',targetKind:'workspace',targetValue:'0'}), formError({title:'x'})]"),
                         ['Give the quest a title.', 'Choose a workspace number.', ''])
        self.assertEqual(js("slugify('Écrire les notes — v2!')"), 'ecrire-les-notes-v2')
        self.assertEqual(js("slugify('!!!', 'step-3')"), 'step-3')

    def test_edit_keeps_step_ids_and_round_trips(self):
        form = js('formFromDetail(%s)' % json.dumps(DETAIL))
        self.assertEqual(form['steps'], 'Draft\nWrite\nPublish')
        self.assertEqual(form['sessions'], {'Write': 2})
        self.assertEqual((form['targetKind'], form['targetValue']), ('area', 'sun-court'))
        edited = dict(form, steps='Draft\nPolish\nWrite\nPublish')
        quest = js('questInput(%s, %s)' % (json.dumps(edited), json.dumps(DETAIL)))
        self.assertEqual([s['id'] for s in quest['steps']], ['draft', 'polish', 'write', 'publish'])
        self.assertEqual(quest['steps'][2]['objectives'], [{'id': 'focus', 'type': 'focus', 'sessions': 2}])
        frame(request('quests.update', {'questRef': REF, 'quest': quest}), V21)

    def test_focus_timing(self):
        self.assertEqual(js('[countdown(1500000), countdown(61001), countdown(999), countdown(0), countdown(7200000), countdown(-5)]'),
                         ['25:00', '01:02', '00:01', '00:00', '2:00:00', '00:00'])
        focus = json.dumps(FOCUS)
        self.assertEqual(js('remaining(%s, 1000000)' % focus), 600000)
        self.assertEqual(js('remaining(%s, 2000000)' % focus), 0)
        self.assertEqual(js('remaining(%s, null)' % focus), 1500000)  # no clock yet: the published remainder
        paused = dict(FOCUS, state='paused', pausedState='work', phaseStartedAtMs=None, phaseEndsAtMs=None, remainingMs=420000)
        self.assertEqual(js('remaining(%s, 9e9)' % json.dumps(paused)), 420000)
        self.assertAlmostEqual(js('ringProgress(%s, 600000)' % focus), 0.6)
        self.assertAlmostEqual(js('creditProgress(%s)' % focus), 0.2)
        self.assertEqual(js('creditProgress(%s)' % json.dumps(dict(FOCUS, state='break', breakKind='short'))), 0)
        labels = [dict(FOCUS), dict(FOCUS, state='break', breakKind='short'), dict(FOCUS, state='break', breakKind='long'),
                  dict(FOCUS, state='ready'), paused, dict(FOCUS, state='idle')]
        self.assertEqual(js('%s.map(phaseLabel)' % json.dumps(labels)), ['Work', 'Short break', 'Long break', 'Ready', 'Paused', ''])
        self.assertEqual(js('cycleDots(%s)' % focus), ['done', 'current', 'todo', 'todo'])
        self.assertEqual(js('cycleDots(%s)' % json.dumps(dict(FOCUS, state='break', breakKind='short'))), ['done', 'done', 'todo', 'todo'])
        self.assertEqual(js('cycleDots(%s)' % json.dumps(dict(FOCUS, state='ready', cycle=3))), ['done', 'done', 'current', 'todo'])
        self.assertEqual(js('[chipVisible(%s, true, null), chipVisible(%s, false, null), chipVisible(%s, false, {"focus.desktop_chip": true}),'
                            ' chipVisible({state:"idle"}, true, null)]' % (focus, focus, focus)), [True, False, True, False])

    def test_toasts(self):
        step = {'questRef': REF, 'kind': 'step', 'title': 'Release notes', 'stepTitle': 'Draft', 'nextStepTitle': 'Write'}
        toast = js('toastFor("quest.progress", %s)' % json.dumps(step))
        self.assertEqual((toast['kind'], toast['line'], toast['detail'], toast['durationMs']), ('toast', '✓ Draft', 'Next: Write', 3000))
        done = js('toastFor("quest.progress", %s)' % json.dumps(dict(step, kind='completed')))
        self.assertEqual((done['kind'], done['durationMs']), ('banner', 5000))
        self.assertIsNone(js('toastFor("quest.progress", %s)' % json.dumps(dict(step, kind='objective'))))
        brk = js('toastFor("focus.phase", %s, %s)' % (json.dumps({'phase': 'break', 'cycle': 1, 'cycles': 4, 'creditedMs': 0, 'breakKind': 'short',
                                                                  'suggestion': {'markerId': 'm', 'label': 'the north lookout'}}),
                                                     json.dumps(dict(FOCUS, state='break', phaseMs=300000))))
        self.assertEqual((brk['line'], brk['detail'], brk['durationMs']), ('Break · 5 min', 'Stretch, or walk to the north lookout.', 4000))
        ended = js('toastFor("focus.phase", %s)' % json.dumps({'phase': 'ended', 'cycle': 4, 'cycles': 4, 'creditedMs': 1380000, 'outcome': 'completed'}))
        self.assertEqual((ended['line'], ended['detail']), ('Session complete · 4 intervals', 'Last interval: 23 min credited'))
        for text in [toast, done, brk, ended]:
            self.assertNotIn('away', json.dumps(text).lower())  # never "you were away"

    def test_routing_calm_and_notifications(self):
        step, banner, focus = ("{category:'step'}", "{category:'completed'}", "{category:'focus'}")
        self.assertEqual(js('[route(%s,"all",false), route(%s,"important",false), route(%s,"important",false), route(%s,"off",false)]'
                            % (step, step, banner, focus)), ['show', 'drop', 'show', 'drop'])
        self.assertEqual(js('[route(%s,"all",true), route(%s,"all",true), route(%s,"important",true)]' % (step, banner, focus)),
                         ['defer', 'defer', 'show'])

    def test_queue_merges_and_caps_at_three(self):
        q = js("""(function() {
            var q = [];
            q = enqueue(q, {key:'a', durationMs: 3000, line: 'a1'}, 0);
            q = enqueue(q, {key:'b', durationMs: 3000}, 10);
            q = enqueue(q, {key:'b', durationMs: 3000, line: 'b2'}, 20);
            q = enqueue(q, {key:'c', durationMs: 3000}, 30);
            q = enqueue(q, {key:'d', durationMs: 3000}, 40);
            return q;
        })()""")
        self.assertEqual([(t['key'], t['count']) for t in q], [('a', 1), ('c', 1), ('d', 1)])  # b was the oldest waiting
        merged = js("enqueue(enqueue([], {key:'a', durationMs: 3000}, 0), {key:'a', durationMs: 3000, line:'x'}, 500)")
        self.assertEqual((len(merged), merged[0]['count'], merged[0]['line'], merged[0]['shownAt']), (1, 2, 'x', 500))
        after = js("advance(enqueue(enqueue([], {key:'a', durationMs: 3000}, 0), {key:'b', durationMs: 4000}, 1), 3000)")
        self.assertEqual([(t['key'], t['shownAt']) for t in after], [('b', 3000)])
        self.assertEqual(len(js("advance(enqueue([], {key:'a', durationMs: 3000}, 0), 2999)")), 1)

    def test_hold_ring_waits_for_the_tap_window(self):
        hold = {'durationMs': 1000, 'remainingMs': 1000}
        view = js('holdView(%s, 50)' % json.dumps(hold))
        self.assertEqual((view['visible'], view['waitMs']), (False, 130))
        view = js('holdView(%s, 0)' % json.dumps(dict(hold, remainingMs=800)))  # bridge saw 200 ms elapsed
        self.assertTrue(view['visible'])
        self.assertAlmostEqual(view['progress'], 20 / 820)
        self.assertEqual(view['fillMs'], 800)
        self.assertEqual(js('holdView(%s, 5000).progress' % json.dumps(hold)), 1)
        self.assertEqual(js('holdView(null, 0).visible'), False)
        self.assertEqual(js('holdView(%s, 100, 0).visible' % json.dumps(hold)), True)  # delay 0: legacy behaviour
        self.assertEqual(js('HOLD_RING_DELAY_MS'), 180)

    def test_error_text(self):
        self.assertEqual(js("errorText('focus.start', '-32004: session running')"), 'A focus session is already running.')
        self.assertEqual(js("errorText('quests.update', '-32007: not personal')"), 'Only personal quests can be edited or deleted.')
        self.assertEqual(js("errorText('quests.create', '-32008: too many')"), 'Limit reached (at most 64 personal quests).')
        self.assertEqual(js("errorText('quests.get', '-32003: unknown quest')"), 'That quest or step no longer exists.')

    def test_guidance_rows_and_patches(self):
        rows = js('guidanceRows(%s)' % json.dumps(GUIDANCE))
        self.assertEqual(len(rows), len(GUIDANCE['config']))
        types = {r['key']: r['type'] for r in rows}
        self.assertEqual(types['markers.reveal_ms'], 'number')
        self.assertEqual(types['quests.notifications'], 'enum')
        self.assertEqual(types['focus.calm'], 'bool')
        self.assertEqual([r['group'] for r in rows if r['first']], ['MARKERS', 'QUESTS', 'FOCUS SESSIONS'])
        patches = [js('guidancePatch(%s, "markers.reveal_ms", 4260)' % json.dumps(GUIDANCE)),
                   js('guidancePatch(%s, "focus.work_min", 500)' % json.dumps(GUIDANCE)),
                   js('guidancePatch(%s, "focus.count_mode", "wall")' % json.dumps(GUIDANCE)),
                   js('guidancePatch(%s, "focus.desktop_chip", true)' % json.dumps(GUIDANCE)),
                   js('guidancePatch(%s, "focus.calm", null)' % json.dumps(GUIDANCE))]
        self.assertEqual(patches, [{'markers.reveal_ms': 4500}, {'focus.work_min': 120}, {'focus.count_mode': 'wall'},
                                   {'focus.desktop_chip': True}, {'focus.calm': None}])
        for p in patches:
            frame(request('guidance.set', {'patch': p}), V21)
        self.assertEqual(js('guidanceValue(null, "markers.reveal_ms", 4500)'), '4.5 s')


if __name__ == '__main__':
    unittest.main()
