"""Machine data sources (RFC-0013 draft): the bridge's sources.json writes and source helper
client (bridge/sources.py, against dev/sources_fake.py on a real Unix socket), and the pure
helpers behind Director > Objects > Placed > Data source (qml/Sources.js, with node).

IPC 0.24 adds catalog `machine` and state `live`; the checks against that pin run once it is
vendored (protocol/v0.24) and are skipped before."""
import asyncio
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bridge'))
sys.path.insert(0, str(ROOT / 'dev'))
import sources  # noqa: E402
from sources import ConfigError, HelperError, HelperUnavailable, Sources  # noqa: E402
from sources_fake import FakeHelper, TEST  # noqa: E402
from protocol import SUPPORTED_PROTOCOLS, VALIDATORS, validate_response  # noqa: E402

SOURCES = (ROOT / 'qml/Sources.js').read_text()
OBJECTS = (ROOT / 'qml/Objects.js').read_text()

# The gauge machines' inputs as the 0.24 catalog carries them (object.json traits.machine).
GAUGE = {'primary': 'level', 'inputs': [
    {'id': 'value', 'type': 'number', 'min': 0, 'max': 100, 'default': 0, 'label': 'Value', 'explain': 'The liquid height.'},
    {'id': 'display', 'type': 'text', 'maxLength': 12, 'label': 'Display', 'explain': 'The large text.'},
    {'id': 'label', 'type': 'text', 'maxLength': 16, 'label': 'Label', 'explain': 'What it measures.'},
    {'id': 'level', 'type': 'enum', 'values': ['ok', 'warn', 'fail'], 'default': 'ok', 'label': 'Level', 'explain': 'The colour.'},
    {'id': 'average', 'type': 'number', 'min': 0, 'max': 100, 'label': 'Average (optional)', 'explain': 'A running average.'}]}
RACK = {'primary': None, 'inputs': [
    {'id': 'health', 'type': 'enum', 'values': ['ok', 'warn', 'fail', 'off'], 'repeat': 3, 'label': 'Health', 'explain': 'One light per unit.'},
    {'id': 'name', 'type': 'text', 'maxLength': 24, 'label': 'Name', 'explain': 'The rack name.'},
    {'id': 'units', 'type': 'int', 'min': 0, 'max': 42, 'label': 'Units', 'explain': 'Used units.'},
    {'id': 'on', 'type': 'bool', 'label': 'Power', 'explain': 'Mains.'},
    {'id': 'started', 'type': 'event', 'label': 'Started', 'explain': 'A job started.'}]}
NOW = 1791800000000
LIVE = {'instances': [{'id': 'u-3f9a1c', 'asset': 'gauge-tube', 'ref': 'library/com.hyprune.starter@0.2.0/gauge-tube',
                       'source': 'com.hyprune.sources.u-3f9a1c', 'status': 'ok', 'error': None, 'stale': False, 'inputs': {
    'value': {'source': 'com.hyprune.sources.u-3f9a1c', 'key': 'value', 'value': 71, 'raw': 71, 'condition': 'fresh', 'publishedAt': NOW - 4000},
    'display': {'source': 'com.hyprune.sources.u-3f9a1c', 'key': 'display', 'value': '71%', 'raw': '71%', 'condition': 'fresh', 'publishedAt': NOW - 4000},
    'level': {'source': 'com.hyprune.sources.u-3f9a1c', 'key': 'level', 'value': 'ok', 'raw': 'OK', 'condition': 'stale', 'publishedAt': NOW - 125000},
    'label': {'source': 'com.hyprune.sources.u-3f9a1c', 'key': 'label', 'value': None, 'raw': None, 'condition': 'missing', 'publishedAt': None}}}]}


def js(expression, script=SOURCES):
    return json.loads(subprocess.check_output(['node', '-e', script + '\nconsole.log(JSON.stringify(' + expression + '));'], text=True))


def call(name, *args, script=SOURCES):
    return js('%s(%s)' % (name, ', '.join(json.dumps(a) for a in args)), script)


class Config(unittest.TestCase):
    """sources.json: atomic, order-preserving saves and removes (spec C)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.path = self.dir / 'hyprune' / 'sources.json'

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, obj, mode=None):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(obj, indent=2) + '\n')
        if mode is not None: os.chmod(self.path, mode)

    def leftovers(self):
        return sorted(p.name for p in self.path.parent.iterdir() if p.name != 'sources.json')

    def test_paths(self):
        self.assertEqual(sources.control_path('/run/user/1000/hyprune/sig/control.sock'), '/run/user/1000/hyprune/sig/sources.sock')
        self.assertEqual(sources.control_path('/run/x/control.sock', '/run/x/other.sock'), '/run/x/other.sock')
        self.assertEqual(sources.default_config({'XDG_CONFIG_HOME': '/cfg', 'HOME': '/home/u'}), '/cfg/hyprune/sources.json')
        self.assertEqual(sources.default_config({'HOME': '/home/u'}), '/home/u/.config/hyprune/sources.json')
        self.assertEqual(sources.default_config({'XDG_CONFIG_HOME': 'relative', 'HOME': '/home/u'}), '/home/u/.config/hyprune/sources.json')

    def test_new_file_in_a_missing_directory(self):
        entry = sources.save_entry(self.path, 'u-3f9a1c', ['/home/u/bin/ram gauge', '--json'], 10)
        self.assertEqual(entry, {'id': 'u-3f9a1c', 'kind': 'command', 'argv': ['/home/u/bin/ram gauge', '--json'], 'intervalS': 10})
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertEqual(self.path.read_text(), json.dumps({'sources': [entry]}, indent=2) + '\n')
        self.assertEqual(self.leftovers(), [])

    def test_update_keeps_other_entries_keys_and_order(self):
        original = {'client': {'id': 'com.hyprune.sources'}, 'protocol': '0.2', 'sources': [
            {'id': 'ci', 'kind': 'command', 'argv': ['sims/ci.py'], 'intervalS': 30},
            {'id': 'u-3f9a1c', 'kind': 'command', 'argv': ['/old'], 'output': 'json', 'intervalS': 60, 'timeoutS': 5, 'env': {'A': 'b'}},
            {'id': 'status-page', 'kind': 'http', 'url': 'https://example.invalid/s.json', 'enabled': False}], 'devFastIntervals': False}
        self.write(original, 0o640)
        sources.save_entry(self.path, 'u-3f9a1c', ['/new', 'a b'], 15)
        saved = json.loads(self.path.read_text())
        self.assertEqual(list(saved), ['client', 'protocol', 'sources', 'devFastIntervals'])
        self.assertEqual([e['id'] for e in saved['sources']], ['ci', 'u-3f9a1c', 'status-page'])
        self.assertEqual(saved['sources'][0], original['sources'][0])
        self.assertEqual(saved['sources'][2], original['sources'][2])
        self.assertEqual(saved['sources'][1], {'id': 'u-3f9a1c', 'kind': 'command', 'argv': ['/new', 'a b'], 'output': 'json',
                                               'intervalS': 15, 'timeoutS': 5, 'env': {'A': 'b'}})
        self.assertEqual(list(saved['sources'][1]), ['id', 'kind', 'argv', 'output', 'intervalS', 'timeoutS', 'env'])
        self.assertEqual(self.path.read_text(), json.dumps(saved, indent=2) + '\n')
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o640)  # an existing file keeps its mode
        self.assertEqual(self.leftovers(), [])

    def test_insert_appends_and_remove_deletes_only_that_entry(self):
        self.write({'sources': [{'id': 'ci', 'kind': 'command', 'argv': ['ci'], 'intervalS': 30}]})
        sources.save_entry(self.path, 'u-0000aa', ['/bin/gauge'], 5)
        self.assertEqual([e['id'] for e in json.loads(self.path.read_text())['sources']], ['ci', 'u-0000aa'])
        self.assertTrue(sources.remove_entry(self.path, 'u-0000aa'))
        self.assertEqual(json.loads(self.path.read_text()), {'sources': [{'id': 'ci', 'kind': 'command', 'argv': ['ci'], 'intervalS': 30}]})
        before = self.path.stat().st_mtime_ns
        self.assertFalse(sources.remove_entry(self.path, 'u-0000aa'))  # nothing to remove: untouched
        self.assertEqual(self.path.stat().st_mtime_ns, before)
        self.assertFalse(sources.remove_entry(self.dir / 'none.json', 'u-0000aa'))
        self.assertFalse((self.dir / 'none.json').exists())
        self.assertEqual(self.leftovers(), [])

    def test_failed_write_leaves_the_file_and_no_temp(self):
        self.write({'sources': []})
        before = self.path.read_text()
        with mock.patch('sources.os.replace', side_effect=OSError(28, 'No space left on device')):
            with self.assertRaisesRegex(ConfigError, 'No space left'):
                sources.save_entry(self.path, 'u-1', ['/bin/x'], 60)
        self.assertEqual(self.path.read_text(), before)
        self.assertEqual(self.leftovers(), [])

    def test_refusals_leave_the_file_alone(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text('{"sources": [ broken')
        with self.assertRaisesRegex(ConfigError, 'not valid JSON'):
            sources.save_entry(self.path, 'u-1', ['/bin/x'], 60)
        self.assertEqual(self.path.read_text(), '{"sources": [ broken')
        self.write({'sources': [{'id': 'u-1', 'kind': 'http', 'url': 'https://example.invalid'}]})
        with self.assertRaisesRegex(ConfigError, 'http source'):
            sources.save_entry(self.path, 'u-1', ['/bin/x'], 60)
        for args, message in [(('Court.Rack_1', ['/bin/x'], 60), 'slug'), (('u-1', [], 60), 'command'), (('u-1', ['/bin/x', ''], 60), 'command'),
                              (('u-1', ['/bin/x'], 4), '5–86400'), (('u-1', ['/bin/x'], 86401), '5–86400'), (('u-1', ['/bin/x'], True), 'seconds'),
                              (('u-1', ['/bin/x'] * 65, 60), 'At most')]:
            with self.subTest(args=args), self.assertRaisesRegex(ConfigError, message):
                sources.save_entry(self.path, *args)
        self.assertEqual(self.leftovers(), [])

    def test_interval_limits_follow_the_helper_and_dev_intervals(self):
        self.assertEqual(sources.interval_bounds(None), [5, 86400])
        self.assertEqual(sources.interval_bounds({'command': {'intervalS': [10, 3600], 'devIntervalS': 2}}, dev=True), [2, 3600])
        self.write({'devFastIntervals': True, 'sources': []})
        self.assertEqual(sources.save_entry(self.path, 'u-1', ['/bin/x'], 1)['intervalS'], 1)
        with self.assertRaisesRegex(ConfigError, '1–3600'):  # devFastIntervals: the helper's devIntervalS (default 1)
            sources.save_entry(self.path, 'u-2', ['/bin/x'], 5000, {'command': {'intervalS': [10, 3600]}})
        self.write({'sources': []})
        with self.assertRaisesRegex(ConfigError, '10–3600'):
            sources.save_entry(self.path, 'u-2', ['/bin/x'], 5, {'command': {'intervalS': [10, 3600]}})

    def test_a_symlinked_file_stays_a_link(self):
        real = self.dir / 'dotfiles' / 'sources.json'
        real.parent.mkdir()
        real.write_text('{"sources": []}\n')
        self.path.parent.mkdir()
        self.path.symlink_to(real)
        sources.save_entry(self.path, 'u-1', ['/bin/x'], 60)
        self.assertTrue(self.path.is_symlink())
        self.assertEqual(json.loads(real.read_text())['sources'][0]['id'], 'u-1')

    def test_browse(self):
        base = self.dir / 'bin'
        (base / 'scripts').mkdir(parents=True)
        (base / '.hidden').mkdir()
        for name, mode in [('ram-gauge', 0o755), ('Readme.txt', 0o644), ('cpu', 0o700)]:
            (base / name).write_text('x'); os.chmod(base / name, mode)
        listing = sources.browse(str(base))
        self.assertEqual(listing['path'], str(base))
        self.assertEqual(listing['parent'], str(self.dir))
        self.assertEqual([(e['name'], e['dir'], e['executable']) for e in listing['entries']],
                         [('scripts', True, False), ('cpu', False, True), ('ram-gauge', False, True), ('Readme.txt', False, False)])
        self.assertIn('.hidden', [e['name'] for e in sources.browse(str(base), hidden=True)['entries']])
        picked = sources.browse(str(base / 'cpu'))
        self.assertEqual((picked['path'], picked['selected']), (str(base), 'cpu'))
        self.assertTrue(sources.browse(str(base), limit=2)['truncated'])
        self.assertIsNone(sources.browse('/')['parent'])
        with self.assertRaises(ConfigError): sources.browse('relative/path')
        with self.assertRaises(ConfigError): sources.browse(str(self.dir / 'missing'))


class Helper(unittest.IsolatedAsyncioTestCase):
    """The control socket client and the QML request handler against a fake helper."""

    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.socket = str(self.dir / 'sources.sock')
        self.config = str(self.dir / 'helper' / 'sources.json')
        self.default = str(self.dir / 'default' / 'sources.json')
        self.fake = None

    async def asyncTearDown(self):
        if self.fake: await self.fake.stop()
        self.tmp.cleanup()

    async def start(self, **kw):
        self.fake = await FakeHelper(config=self.config, **kw).start(self.socket)
        return Sources(self.socket, self.default, timeouts={'status': .5, 'reload': .5, 'test': .5, 'restart': .5, 'restart-all': .5})

    async def test_ops_on_the_wire(self):
        bridge = await self.start()
        status = await bridge.handle({'type': 'sources.status', 'seq': 4})
        self.assertEqual((status['type'], status['op'], status['seq'], status['ok'], status['helper']), ('sources', 'status', 4, True, 'ok'))
        self.assertEqual(status['status']['config'], self.config)
        test = await bridge.handle({'type': 'sources.test', 'seq': 5, 'id': 'u-3f9a1c', 'argv': ['/bin/gauge', '--json']})
        self.assertEqual((test['op'], test['id'], test['ok']), ('test', 'u-3f9a1c', True))
        self.assertEqual(test['result'], {k: TEST[k] for k in ('values', 'stdout', 'stderr', 'error', 'exitCode', 'durationMs')})
        restart = await bridge.handle({'type': 'sources.restart', 'id': 'u-3f9a1c', 'resetAverage': True})
        self.assertEqual((restart['ok'], restart['resetAverage']), (True, True))
        self.assertTrue((await bridge.handle({'type': 'sources.restartAll'}))['ok'])
        self.assertEqual(self.fake.requests, [
            {'op': 'status'},
            {'op': 'test', 'source': {'kind': 'command', 'argv': ['/bin/gauge', '--json'], 'output': 'json'}},
            {'op': 'restart', 'id': 'u-3f9a1c', 'resetAverage': True},
            {'op': 'restart-all'}])

    async def test_save_uses_the_helper_config_and_reloads(self):
        bridge = await self.start()
        saved = await bridge.handle({'type': 'sources.save', 'seq': 1, 'id': 'u-3f9a1c', 'argv': ['/bin/gauge'], 'intervalS': 10})
        self.assertEqual((saved['ok'], saved['path'], saved['reload']), (True, self.config, {'ok': True}))
        self.assertEqual([r['op'] for r in self.fake.requests], ['status', 'reload'])
        self.assertFalse(Path(self.default).exists())
        got = await bridge.handle({'type': 'sources.get', 'id': 'u-3f9a1c'})
        self.assertEqual((got['ok'], got['exists'], got['dev'], got['entry']['argv']), (True, True, False, ['/bin/gauge']))
        self.assertEqual(got['limits'], self.fake.answer({'op': 'status'})['limits'])
        removed = await bridge.handle({'type': 'sources.remove', 'id': 'u-3f9a1c'})
        self.assertEqual((removed['ok'], removed['removed'], removed['reload']), (True, True, {'ok': True}))
        self.assertEqual(json.loads(Path(self.config).read_text()), {'sources': []})

    async def test_without_a_helper(self):
        bridge = Sources(self.socket, self.default)
        status = await bridge.handle({'type': 'sources.status'})
        self.assertEqual((status['ok'], status['helper']), (False, 'missing'))
        self.assertIn('not running', status['error'])
        saved = await bridge.handle({'type': 'sources.save', 'id': 'u-1', 'argv': ['/bin/x'], 'intervalS': 60})
        self.assertEqual((saved['ok'], saved['path'], saved['reload']['ok'], saved['reload']['helper']), (True, self.default, False, 'missing'))
        self.assertTrue(Path(self.default).exists())
        for cmd in [{'type': 'sources.test', 'argv': ['/bin/x']}, {'type': 'sources.restart', 'id': 'u-1'}, {'type': 'sources.restartAll'}]:
            reply = await bridge.handle(cmd)
            self.assertEqual((reply['ok'], reply['helper']), (False, 'missing'), cmd)

    async def test_helper_errors_never_raise(self):
        bridge = await self.start(replies={'test': {'ok': False, 'error': 'argv[0] is not executable'}, 'restart': 'hang',
                                           'restart-all': 'garbage', 'reload': 'close', 'status': 'huge'})
        test = await bridge.handle({'type': 'sources.test', 'argv': ['/bin/x']})
        self.assertEqual((test['ok'], test['helper'], test['error']), (False, 'error', 'argv[0] is not executable'))
        hang = await bridge.handle({'type': 'sources.restart', 'id': 'u-1'})
        self.assertEqual((hang['ok'], hang['helper']), (False, 'error'))
        self.assertIn('did not answer', hang['error'])
        self.assertIn('not JSON', (await bridge.handle({'type': 'sources.restartAll'}))['error'])
        self.assertIn('64 KiB', (await bridge.handle({'type': 'sources.status'}))['error'])
        saved = await bridge.handle({'type': 'sources.save', 'id': 'u-1', 'argv': ['/bin/x'], 'intervalS': 60})
        self.assertTrue(saved['ok'])  # the file is written even when the helper misbehaves
        self.assertEqual(saved['path'], self.default)
        self.assertIn('without an answer', saved['reload']['error'])
        for cmd in [None, [], {'type': 'sources.nope'}, {'type': 'sources.save', 'id': 'u-1', 'argv': 'x', 'intervalS': 60},
                    {'type': 'sources.test', 'argv': None}, {'type': 'sources.restart', 'id': '../x'}, {'type': 'sources.browse', 'path': 3}]:
            reply = await bridge.handle(cmd)
            self.assertEqual((reply['type'], reply['ok']), ('sources', False), cmd)

    async def test_refuses_a_socket_that_is_not_ours(self):
        Path(self.socket).write_text('')
        with self.assertRaisesRegex(HelperError, 'not a socket'):
            await sources.request(self.socket, {'op': 'status'}, 1)
        with self.assertRaises(HelperUnavailable):
            await sources.request(str(self.dir / 'absent.sock'), {'op': 'status'}, 1)

    async def test_browse_request(self):
        bridge = Sources(self.socket, self.default)
        listing = await bridge.handle({'type': 'sources.browse', 'seq': 9, 'path': str(self.dir)})
        self.assertEqual((listing['op'], listing['seq'], listing['ok'], listing['path']), ('browse', 9, True, str(self.dir)))


class Launcher(unittest.TestCase):
    def test_the_bridge_routes_sources_requests(self):
        launch = (ROOT / 'bridge/launch.py').read_text()
        self.assertIn("cmd['type'].startswith('sources.')", launch)
        self.assertIn('emit(await sources.handle(cmd))', launch)
        self.assertIn("Sources(control_path(core_socket, args.sources_control), default_config())", launch)
        self.assertIn("'--sources-control', default=os.environ.get('HYPRUNE_SOURCES_CONTROL')", launch)


class Argv(unittest.TestCase):
    def test_quoting_and_preview(self):
        self.assertEqual(call('runsText', ['/home/u/bin/ram-gauge', '--json', 'a b', "it's", '', 'x=1,y:2', '$HOME', 'ü']),
                         "Runs: /home/u/bin/ram-gauge --json 'a b' 'it'\\''s' '' x=1,y:2 '$HOME' 'ü'")
        self.assertEqual(call('runsText', []), '')
        # The quoted line is a faithful shell rendering of the argv.
        argv = ['/bin/printf', '%s|', "it's", 'a b', '*', '$(x)', '']
        line = call('argvLine', argv)
        out = subprocess.check_output(['sh', '-c', 'set -- ' + line + '; for a in "$@"; do printf "%s\\0" "$a"; done'])
        self.assertEqual(out.split(b'\0')[:-1], [a.encode() for a in argv])

    def test_arguments_one_per_line(self):
        self.assertEqual(call('parseArgs', '--json\n\n  --unit GB \r\n'), ['--json', '--unit GB'])
        self.assertEqual(call('buildArgv', '  /bin/x ', '-a\n-b'), ['/bin/x', '-a', '-b'])
        self.assertEqual(call('buildArgv', ' ', '-a'), [])
        self.assertEqual(call('argsText', ['-a', '-b']), '-a\n-b')

    def test_interval_bounds_and_clamping(self):
        self.assertEqual(call('intervalBounds', None, False), {'min': 5, 'max': 86400})
        limits = {'command': {'intervalS': [10, 3600], 'devIntervalS': 1}}
        self.assertEqual(call('intervalBounds', limits, False), {'min': 10, 'max': 3600})
        self.assertEqual(call('intervalBounds', limits, True), {'min': 1, 'max': 3600})
        b = {'min': 5, 'max': 86400}
        self.assertEqual([call('clampInterval', v, b, 60) for v in [1, '30', ' 7.6 ', 100000, 'abc', '', None]], [5, 30, 8, 86400, 60, 60, 60])
        self.assertEqual(call('clampInterval', 'x', {'min': 120, 'max': 600}, 60), 120)
        self.assertEqual([call('intervalText', v) for v in [5, 90, 120, 7200]], ['5 s', '90 s', '2 min', '2 h'])

    def test_draft(self):
        b = {'min': 5, 'max': 86400}
        self.assertEqual(call('draftFrom', None, b), {'script': '', 'args': '', 'intervalS': 60, 'kind': 'command', 'editable': True, 'note': '', 'hint': '',
                                                      'exists': False})
        d = call('draftFrom', {'id': 'u-1', 'kind': 'command', 'argv': ['/bin/x', '-a', 'b c'], 'intervalS': 2}, b)
        self.assertEqual((d['script'], d['args'], d['intervalS'], d['editable']), ('/bin/x', '-a\nb c', 5, True))
        http = call('draftFrom', {'id': 'u-1', 'kind': 'http', 'url': 'https://example.invalid'}, b)
        self.assertEqual((http['editable'], http['note']), (False, 'This is a http source; edit it in sources.json.'))
        self.assertEqual(call('draftError', [], '60', b), 'Choose a command first.')
        self.assertEqual(call('draftError', ['/x'], '', b), 'Enter the interval in seconds.')
        self.assertEqual(call('draftError', ['/x'], '3', b), 'The interval is 5–86400 s.')
        self.assertEqual(call('draftError', ['/x'], '60', b), '')


class Validation(unittest.TestCase):
    def test_inputs_expand_repeats_and_describe_ranges(self):
        keys = call('expandInputs', RACK)
        self.assertEqual([i['key'] for i in keys], ['health.1', 'health.2', 'health.3', 'name', 'units', 'on', 'started'])
        self.assertEqual(keys[1]['label'], 'Health 2')
        self.assertEqual([call('rangeText', i) for i in GAUGE['inputs']], ['number 0–100', 'text ≤ 12', 'text ≤ 16', 'ok | warn | fail', 'number 0–100'])
        self.assertEqual(call('expandInputs', GAUGE)[3]['primary'], True)
        self.assertEqual(call('expandInputs', None), [])

    def test_a_good_output(self):
        v = call('validateTest', {'values': {'value': 71, 'display': '71%', 'label': 'RAM', 'level': 'ok', 'average': 64.5, '_status': 'ok'},
                                  'exitCode': 0, 'error': None}, GAUGE)
        self.assertTrue(v['ok'])
        self.assertEqual([r['level'] for r in v['rows']], ['ok'] * 5)
        self.assertEqual((v['unknown'], v['missing'], v['reserved']), ([], [], {'_status': 'ok'}))
        self.assertEqual(v['summary'], '5 of 5 inputs sent and fit')

    def test_mismatches_unknown_and_missing(self):
        v = call('validateTest', {'values': {'value': '71', 'display': '71 percent of RAM', 'level': 'busy', 'ram': 3, 'average': 140}, 'exitCode': 0}, GAUGE)
        rows = {r['key']: r for r in v['rows']}
        self.assertEqual((rows['value']['level'], rows['value']['problems']), ('error', ['expected a number, got text']))
        self.assertEqual((rows['display']['level'], rows['display']['problems']), ('warning', ['longer than 12 (cut)']))
        self.assertEqual((rows['label']['level'], rows['label']['problems']), ('muted', ['not sent']))
        self.assertEqual(rows['level']['problems'], ['not one of ok, warn, fail'])
        self.assertEqual(rows['average']['problems'], ['above 100'])
        self.assertEqual((v['unknown'], v['missing'], v['ok']), (['ram'], ['label'], False))
        self.assertEqual(v['summary'], '1 of 5 inputs sent and fit · 3 mismatches · 1 not sent · 1 unknown key')
        missing = call('validateTest', {'values': {}}, GAUGE)
        self.assertEqual(missing['rows'][0]['problems'], ['not sent: shows 0'])
        self.assertEqual(missing['rows'][3]['problems'], ['not sent: shows ok'])

    def test_types(self):
        v = call('validateTest', {'values': {'health.1': 'ok', 'health.2': 'warn', 'health.3': 3, 'name': 'r1', 'units': 4.5, 'on': 'yes', 'started': 12}}, RACK)
        rows = {r['key']: r['problems'] for r in v['rows']}
        self.assertEqual(rows, {'health.1': [], 'health.2': [], 'health.3': ['expected text, got number'], 'name': [],
                                'units': ['expected a whole number'], 'on': ['expected true or false'], 'started': []})
        self.assertEqual(call('checkValue', {'type': 'int', 'min': 0}, -1), ['below 0'])
        self.assertEqual(call('checkValue', {'type': 'text'}, None), ['not a single value'])

    def test_a_failed_run_and_no_declarations(self):
        v = call('validateTest', {'values': {'value': 1}, 'exitCode': 2, 'error': 'exited with status 2'}, GAUGE)
        self.assertTrue(v['failed'])
        self.assertFalse(v['ok'])
        self.assertTrue(v['summary'].startswith('exited with status 2 · '))
        plain = call('validateTest', {'values': {'a': 1, 'b': 'x', '_status': 'ok'}, 'exitCode': 0}, None)  # IPC 0.23: nothing declared
        self.assertEqual(([r['key'] for r in plain['rows']], plain['unknown'], plain['summary']), (['a', 'b'], [], '2 values'))

    def test_printed_json(self):
        self.assertEqual(call('printedText', {'stdout': '{"a":1}\n'}), '{\n  "a": 1\n}')
        self.assertEqual(call('printedText', {'stdout': 'not json\n\n'}), 'not json')
        self.assertEqual(call('printedText', None), '')


class Live(unittest.TestCase):
    def test_source_and_rows(self):
        entry = call('liveFor', LIVE, 'u-3f9a1c')
        self.assertEqual(entry['asset'], 'gauge-tube')
        self.assertIsNone(call('liveFor', None, 'u-3f9a1c'))
        self.assertEqual(call('sourceId', 'u-3f9a1c', None), 'com.hyprune.sources.u-3f9a1c')
        self.assertEqual(call('sourceId', 'u-3f9a1c', {**entry, 'source': 'com.hyprune.sources.ci'}), 'com.hyprune.sources.ci')
        self.assertEqual(call('sourceId', 'u-3f9a1c', {**entry, 'source': None}), '')
        self.assertEqual([call('helperSlug', s) for s in ['com.hyprune.sources.ci', 'org.example.feed', 'com.hyprune.sources.Bad', None]], ['ci', '', '', ''])
        rows = call('liveRows', GAUGE, entry, NOW)
        self.assertEqual([(r['key'], r['value'], r['raw'], r['condition'], r['age']) for r in rows], [
            ('value', '71', '', 'fresh', '4 s'), ('display', '71%', '', 'fresh', '4 s'), ('label', 'null', '', 'missing', ''),
            ('level', 'ok', 'OK', 'stale', '2 min'), ('average', '—', '', 'missing', '')])
        self.assertEqual(rows[3]['primary'], True)
        self.assertEqual(rows[0]['range'], 'number 0–100')
        self.assertEqual([r['key'] for r in call('liveRows', None, entry, NOW)], ['value', 'display', 'level', 'label'])
        self.assertEqual([r['condition'] for r in call('liveRows', GAUGE, None, NOW)], [''] * 5)
        self.assertEqual([call('ageText', NOW - ms, NOW) for ms in [200, 5000, 61000, 7200000, 90000000]], ['now', '5 s', '1 min', '2 h', '1 d'])

    def test_helper_states(self):
        self.assertEqual(call('helperState', None)['state'], 'unknown')
        missing = call('helperState', {'ok': False, 'helper': 'missing', 'error': 'The source helper is not running.'})
        self.assertEqual((missing['state'], missing['canTest'], missing['canRestart']), ('missing', False, False))
        self.assertIn('Save still writes sources.json', missing['text'])
        broken = call('helperState', {'ok': False, 'helper': 'error', 'error': 'did not answer'})
        self.assertEqual((broken['state'], broken['text']), ('error', 'The source helper is not answering: did not answer'))
        status = json.loads(subprocess.check_output([sys.executable, '-c', 'import sys, json; sys.path.insert(0, "dev"); import sources_fake; '
                                                     'print(json.dumps(sources_fake.status("/c/sources.json", now=%d)))' % NOW], cwd=ROOT, text=True))
        ok = call('helperState', {'ok': True, 'helper': 'ok', 'status': status})
        self.assertEqual((ok['state'], ok['canTest'], ok['text']), ('ok', True, 'Source helper connected · 1 source'))
        off = call('helperState', {'ok': True, 'helper': 'ok', 'status': {**status, 'connected': False}})
        self.assertEqual((off['state'], off['canTest'], off['canRestart']), ('disconnected', True, True))
        source = call('helperSource', {'ok': True, 'status': status}, 'u-3f9a1c')
        self.assertEqual(source['intervalS'], 10)
        self.assertIsNone(call('helperSource', {'ok': True, 'status': status}, 'u-other'))
        run = call('lastRunText', source, NOW)
        self.assertEqual(run, {'line': 'Last run 4 s ago · exit 0 · 42 ms · next in 6 s', 'values': 'value 71  ·  display 71%  ·  label RAM  ·  level ok',
                               'error': '', 'level': 'ok'})
        failed = call('lastRunText', {**source, 'resets': 2, 'lastRun': {**source['lastRun'], 'ok': False, 'exitCode': 1, 'error': 'exited with status 1'}}, NOW)
        self.assertEqual((failed['line'], failed['error'], failed['level']), ('Last run failed 4 s ago · exit 1 · 42 ms · next in 6 s · 2 resets', 'exited with status 1', 'warning'))
        self.assertEqual(call('lastRunText', {**source, 'lastRun': None, 'nextRunAt': None}, NOW)['line'], 'Not run yet')
        self.assertIsNone(call('lastRunText', None, NOW))

    def test_browse_rows_and_feedback(self):
        rows = call('browseRows', {'ok': True, 'path': '/home/u', 'parent': '/home', 'entries': [{'name': 'bin', 'dir': True, 'executable': False}, {'name': 'x', 'dir': False, 'executable': True}]})
        self.assertEqual([(r['name'], r['path'], r['parent']) for r in rows], [('..', '/home', True), ('bin', '/home/u/bin', False), ('x', '/home/u/x', False)])
        self.assertEqual(call('browseRows', {'ok': True, 'path': '/', 'parent': None, 'entries': [{'name': 'usr', 'dir': True}]})[0]['path'], '/usr')
        self.assertEqual(call('resultText', {'op': 'save', 'ok': True, 'path': '/c/sources.json', 'reload': {'ok': True}}), {'level': 'info', 'text': 'Saved to /c/sources.json.'})
        self.assertEqual(call('resultText', {'op': 'save', 'ok': True, 'path': '/c/s.json', 'reload': {'ok': False}})['text'],
                         'Saved to /c/s.json. The helper will read it when it runs.')
        self.assertEqual(call('resultText', {'op': 'restart', 'ok': True, 'resetAverage': True})['text'], 'Restarted; the average starts again.')
        self.assertEqual(call('resultText', {'op': 'remove', 'ok': False, 'error': 'Could not write'}), {'level': 'warning', 'text': 'Could not write'})


class Panel(unittest.TestCase):
    """The configure panel's Data source section (Objects.panelSections) and its QML."""

    def instance(self, **over):
        return {'id': 'u-3f9a1c', 'source': 'user', 'ref': 'library/com.hyprune.starter@0.2.0/gauge-tube', 'name': 'Gauge tube',
                'pose': {'position': [0, 0, 0], 'rotation': [0, 0, 0, 1]}, 'scale': 1, 'state': 'active', 'movable': True, 'locked': False, **over}

    def test_data_section(self):
        entry = {'ref': 'library/com.hyprune.starter@0.2.0/gauge-tube', 'traits': ['movable', 'machine'], 'machine': GAUGE}
        data = call('panelSections', self.instance(), entry, script=OBJECTS)[3]
        self.assertEqual((data['id'], data['title'], data['visible'], data['editable'], data['declared'], data['machine']),
                         ('data', 'Data source', True, True, True, GAUGE))
        older = call('panelSections', self.instance(), {k: v for k, v in entry.items() if k != 'machine'}, script=OBJECTS)[3]  # IPC 0.23
        self.assertEqual((older['visible'], older['declared'], older['machine'], older['source']['sourceId']),
                         (True, False, None, 'com.hyprune.sources.u-3f9a1c'))
        authored = call('panelSections', self.instance(id='Court.Rack_1', source='authored'), entry, script=OBJECTS)[3]
        self.assertEqual((authored['visible'], authored['editable']), (True, False))  # not a sources.json id
        plain = call('panelSections', self.instance(), {'traits': ['movable'], 'machine': None}, script=OBJECTS)[3]
        self.assertEqual((plain['visible'], plain['title']), (False, 'Data'))

    def test_qml_wiring(self):
        panel = (ROOT / 'qml/components/ObjectConfigure.qml').read_text()
        self.assertIn("active: section.modelData.id === 'data' && section.modelData.visible", panel)
        self.assertIn('sourceComponent: ObjectDataSource', panel)
        # Inside ObjectDataSource `section` names its own property: binding `section:
        # section.modelData` there binds it to itself (empty), so the Loader passes it on.
        self.assertIn('sourceComponent: ObjectDataSource {\n                    instance: panel.instance\n                    section: dataLoader.sectionData', panel)
        body = (ROOT / 'qml/components/ObjectDataSource.qml').read_text()
        for name in ['objectDataSource', 'objectDataReads', 'objectDataStatus', 'objectDataHint', 'objectDataNoInputs', 'objectDataHelper',
                     'objectDataLastRun', 'source-command', 'source-choose', 'source-args', 'source-interval', 'sourceRuns', 'source-test',
                     'source-save', 'source-remove', 'source-reset-average', 'source-restart', 'source-restart-helper', 'sourceTest', 'sourceFeedback']:
            self.assertIn("objectName: '%s'" % name, body)
        for request in ["'sources.get'", "'sources.test'", "'sources.save'", "'sources.remove'", "'sources.restart'", "'sources.restartAll'"]:
            self.assertIn(request, body)
        self.assertIn("'sources.browse'", (ROOT / 'qml/components/SourceFileBrowser.qml').read_text())
        state = (ROOT / 'qml/ShellState.qml').read_text()
        self.assertIn("case 'sources':", state)
        self.assertIn("running: root.sourcesWanted && root.objectsVisible && root.socket.connected", state)
        self.assertIn("readonly property var liveState: state && state.live ? state.live : null", state)


V24 = VALIDATORS.get('0.24')


@unittest.skipUnless(V24, 'IPC 0.24 is not vendored yet (protocol/v0.24)')
class Ipc24(unittest.TestCase):
    """Catalog `machine` and state `live` against the vendored 0.24 pin; 0.23 refuses them."""

    def catalog(self, machine):
        sys.path.insert(0, str(ROOT / 'tests'))
        from test_ipc22 import entry
        return {'jsonrpc': '2.0', 'id': 'r', 'result': {'revision': 1, 'entries': [entry(machine=machine)]}}

    def test_catalog_machine(self):
        for machine in [None, GAUGE, RACK]:
            validate_response(self.catalog(machine), 'objects.catalog', V24)
        with self.assertRaises(Exception):
            validate_response(self.catalog(GAUGE), 'objects.catalog', VALIDATORS['0.23'])

    def test_live_state(self):
        V24.evolve(schema={'$ref': V24.schema['$id'] + '#/$defs/state/properties/live'}).validate(LIVE)
        V24.evolve(schema={'$ref': V24.schema['$id'] + '#/$defs/state/properties/live'}).validate({'instances': []})
        self.assertIn('0.24', SUPPORTED_PROTOCOLS)


if __name__ == '__main__':
    unittest.main()


class DemoSeed(unittest.TestCase):
    """A newly placed machine starts with core's demo source (hyprune-demo-source): its argv per
    input type, which placements get one, the bridge's add-only seed and the panel's hint."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'hyprune' / 'sources.json'

    def tearDown(self):
        self.tmp.cleanup()

    def test_argv_per_input_type(self):
        self.assertEqual(call('demoArgv', GAUGE), ['hyprune-demo-source', 'value=number:0:100', 'display=text:12', 'label=text:16',
                                                  'level=enum:ok|warn|fail', 'average=number:0:100'])
        self.assertEqual(call('demoArgv', RACK), ['hyprune-demo-source', 'health.1=enum:ok|warn|fail|off', 'health.2=enum:ok|warn|fail|off',
                                                 'health.3=enum:ok|warn|fail|off', 'name=text:24', 'units=int:0:42', 'on=bool', 'started=event'])
        self.assertEqual(call('demoArgv', {'inputs': [{'id': 'x', 'type': 'number'}, {'id': 'n', 'type': 'int'}]}),
                         ['hyprune-demo-source', 'x=number:0:1', 'n=int:0:100'])  # core's defaults
        self.assertIsNone(call('demoArgv', {'inputs': []}))
        self.assertIsNone(call('demoArgv', None))

    def test_the_script_accepts_every_spec(self):
        core = Path(os.environ.get('HYPRUNE_CORE_CHECKOUT', str(ROOT.parent / 'core')))
        script = core / 'dev/machines/scripts/demo-source.py'
        if not script.is_file():
            self.skipTest('no core checkout with demo-source.py (HYPRUNE_CORE_CHECKOUT)')
        for machine in (GAUGE, RACK):
            argv = call('demoArgv', machine)
            out = json.loads(subprocess.check_output([sys.executable, str(script), *argv[1:]], text=True))
            self.assertNotIn('_error', out)
            report = call('validateTest', {'values': out}, machine)
            self.assertFalse([r for r in report['rows'] if r['level'] == 'error'], report)

    def test_which_placements_get_one(self):
        catalog = [{'ref': 'library/a@1/gauge', 'machine': GAUGE}, {'ref': 'package/crate'}, {'ref': 'library/a@1/rack', 'machine': RACK}]
        instances = [{'id': 'u-1', 'source': 'user', 'ref': 'library/a@1/gauge', 'character': False},
                     {'id': 'u-2', 'source': 'user', 'ref': 'package/crate', 'character': False},
                     {'id': 'a-1', 'source': 'authored', 'ref': 'library/a@1/gauge', 'character': False},
                     {'id': 'u-3', 'source': 'user', 'ref': 'library/a@1/rack', 'character': False},
                     {'id': 'u-4', 'source': 'user', 'ref': 'library/b@1/new', 'character': False}]
        out = js('(function () { var known = {"u-3": true}; var seeds = demoSeeds(%s, %s, known); return {seeds: seeds, known: known}; })()'
                 % (json.dumps(instances), json.dumps(catalog)))
        self.assertEqual([s['id'] for s in out['seeds']], ['u-1'])  # machines only, new ones only, user placements only
        self.assertEqual(out['seeds'][0]['argv'][0], 'hyprune-demo-source')
        self.assertEqual(sorted(out['known']), ['u-1', 'u-2', 'u-3'])  # u-4 is not in the catalog yet: tried again

    def test_seed_adds_only_a_missing_entry(self):
        added = sources.seed_entry(self.path, 'u-1', ['hyprune-demo-source', 'v=number:0:100'], 5)
        self.assertEqual(added, {'id': 'u-1', 'kind': 'command', 'argv': ['hyprune-demo-source', 'v=number:0:100'], 'intervalS': 5})
        sources.save_entry(self.path, 'u-1', ['/bin/mine'], 30)  # the user's own command
        self.assertIsNone(sources.seed_entry(self.path, 'u-1', ['hyprune-demo-source', 'v=number:0:100'], 5))
        config = json.loads(self.path.read_text())
        self.assertEqual(config['sources'], [{'id': 'u-1', 'kind': 'command', 'argv': ['/bin/mine'], 'intervalS': 30}])

    def test_panel_hint_for_a_demo_entry(self):
        bounds = call('intervalBounds', None, False)
        demo = call('draftFrom', {'id': 'u-1', 'kind': 'command', 'argv': ['hyprune-demo-source', 'v=bool'], 'intervalS': 5}, bounds)
        self.assertEqual((demo['script'], demo['hint']), ('hyprune-demo-source', js('DEMO_HINT')))
        self.assertEqual(call('draftFrom', {'id': 'u-1', 'kind': 'command', 'argv': ['/bin/x'], 'intervalS': 5}, bounds)['hint'], '')
        self.assertIsNone(call('resultText', {'ok': True, 'op': 'seed', 'path': '/p'}))


class DemoSeedBridge(unittest.IsolatedAsyncioTestCase):
    async def test_seed_on_the_wire(self):
        with tempfile.TemporaryDirectory() as d:
            socket_path, config = str(Path(d) / 'sources.sock'), str(Path(d) / 'helper' / 'sources.json')
            fake = await FakeHelper(config=config).start(socket_path)
            try:
                bridge = Sources(socket_path, str(Path(d) / 'default.json'), timeouts={'status': .5, 'reload': .5, 'test': .5, 'restart': .5, 'restart-all': .5})
                first = await bridge.handle({'type': 'sources.seed', 'seq': 1, 'id': 'u-9', 'argv': ['hyprune-demo-source', 'on=bool'], 'intervalS': 5})
                again = await bridge.handle({'type': 'sources.seed', 'seq': 2, 'id': 'u-9', 'argv': ['hyprune-demo-source', 'on=bool'], 'intervalS': 5})
            finally:
                await fake.stop()
            self.assertEqual((first['op'], first['ok'], first['seeded'], first['reload']['ok']), ('seed', True, True, True))
            self.assertEqual((again['ok'], again['seeded']), (True, False))
            self.assertEqual(json.loads(Path(config).read_text())['sources'][0]['argv'], ['hyprune-demo-source', 'on=bool'])
