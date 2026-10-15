"""Director > Objects > Data sources (data sources phase 2, RFC-0013 draft): the bridge's
whole-entry writes, full-definition tests and secret stores (bridge/sources.py, against
dev/sources_fake.py on a real Unix socket), and the page's pure helpers (qml/DataSources.js,
with node)."""
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
from sources import ConfigError, Sources  # noqa: E402
from sources_fake import FakeHelper, TEST_HTTP, SECRETS  # noqa: E402

DS = (ROOT / 'qml/DataSources.js').read_text()


def js(expression):
    return json.loads(subprocess.check_output(['node', '-e', DS + '\nconsole.log(JSON.stringify(' + expression + '));'], text=True))


def call(name, *args):
    return js('%s(%s)' % (name, ', '.join(json.dumps(a) for a in args)))


HTTP = {'id': 'ingest', 'kind': 'http', 'url': 'https://api.example.com/lag?key={secret:api-key}', 'method': 'POST',
        'headers': {'Authorization': {'secret': 'ci-token', 'prefix': 'Bearer '}, 'Accept': 'application/json'},
        'body': {'q': 'lag'}, 'intervalS': 30, 'ttlMs': 9000, 'fields': [{'name': 'name', 'pointer': '/name'}],
        'map': {'value': {'path': '$.items[*].lag', 'reduce': 'max', 'max': 60}, 'level': {'warn': 50, 'fail': 90},
                'display': '{raw} s behind', 'label': 'Ingest'}}


class Entries(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'sources.json'

    def tearDown(self):
        self.tmp.cleanup()

    def read(self):
        return json.loads(self.path.read_text())

    def test_put_creates_updates_and_keeps_other_keys(self):
        sources.put_entry(self.path, dict(HTTP))
        self.assertEqual(self.read()['sources'], [HTTP])
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        edited = {'id': 'ingest', 'kind': 'http', 'url': 'https://api.example.com/v2', 'method': None, 'body': None,
                  'headers': None, 'map': {'label': 'Ingest v2'}, 'enabled': False}
        sources.put_entry(self.path, edited, 'ingest')
        entry = self.read()['sources'][0]
        self.assertEqual(entry, {'id': 'ingest', 'kind': 'http', 'url': 'https://api.example.com/v2', 'intervalS': 30, 'ttlMs': 9000,
                                 'fields': HTTP['fields'], 'map': {'label': 'Ingest v2'}, 'enabled': False})

    def test_rename_and_duplicates(self):
        sources.put_entry(self.path, dict(HTTP))
        sources.put_entry(self.path, {'id': 'cpu', 'kind': 'command', 'argv': ['hyprune-system-gauges', 'cpu']})
        with self.assertRaisesRegex(ConfigError, 'Another source is called cpu'):
            sources.put_entry(self.path, {**HTTP, 'id': 'cpu'}, 'ingest')
        sources.put_entry(self.path, {**HTTP, 'id': 'ingest-lag'}, 'ingest')
        self.assertEqual([e['id'] for e in self.read()['sources']], ['ingest-lag', 'cpu'])

    def test_rejections(self):
        bad = [{'id': 'Bad', 'kind': 'http', 'url': 'https://x'}, {'id': 'a', 'kind': 'timer'}, {'id': 'a', 'kind': 'http', 'url': 'ftp://x'},
               {'id': 'a', 'kind': 'http', 'url': 'https://x', 'method': 'DELETE'}, {'id': 'a', 'kind': 'http', 'url': 'https://x', 'body': 'b'},
               {'id': 'a', 'kind': 'http', 'url': 'https://x', 'headers': {'Bad Name': 'x'}},
               {'id': 'a', 'kind': 'http', 'url': 'https://x', 'headers': {'K': {'secret': 'no spaces'}}},
               {'id': 'a', 'kind': 'command', 'argv': []}, {'id': 'a', 'kind': 'command', 'argv': ['x'], 'intervalS': -1},
               {'id': 'a', 'kind': 'command', 'argv': ['x'], 'output': 'xml'}, {'id': 'a', 'kind': 'command', 'argv': ['x'], 'map': []}]
        for entry in bad:
            with self.assertRaises(ConfigError, msg=entry):
                sources.check_source(entry)


class SecretFile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'hyprune' / 'secrets.json'

    def tearDown(self):
        self.tmp.cleanup()

    def test_create_update_remove(self):
        sources.set_secret_file(self.path, 'api-key', 'k-123456')
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        sources.set_secret_file(self.path, 'ci-token', 't-abcdef')
        self.assertEqual(json.loads(self.path.read_text()), {'api-key': 'k-123456', 'ci-token': 't-abcdef'})
        sources.set_secret_file(self.path, 'api-key', None)
        self.assertEqual(json.loads(self.path.read_text()), {'ci-token': 't-abcdef'})

    def test_refuses_loose_files_and_bad_input(self):
        sources.set_secret_file(self.path, 'a', 'v')
        os.chmod(self.path, 0o644)
        with self.assertRaisesRegex(ConfigError, 'mode 0600'):
            sources.set_secret_file(self.path, 'b', 'v')
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o644)  # never loosened or rewritten
        for name, value in [('bad name', 'v'), ('a', ''), ('a', 'x' * 5000), ('a', 3)]:
            with self.assertRaises(ConfigError):
                sources.set_secret_file(Path(self.tmp.name) / 'other.json', name, value)

    def test_keyring(self):
        done = subprocess.CompletedProcess([], 0, b'', b'')
        with mock.patch('shutil.which', return_value='/usr/bin/secret-tool'), mock.patch('subprocess.run', return_value=done) as run:
            sources.set_secret_keyring('api-key', 'k-123456')
        args, kwargs = run.call_args
        self.assertEqual(args[0], ['/usr/bin/secret-tool', 'store', '--label', 'Hyprune: api-key', 'application', 'hyprune', 'secret', 'api-key'])
        self.assertEqual(kwargs['input'], b'k-123456')  # on stdin, never on the command line
        with mock.patch('shutil.which', return_value=None), self.assertRaisesRegex(ConfigError, 'secret-tool'):
            sources.set_secret_keyring('api-key', 'k')


class Bridge(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.socket = str(self.dir / 'sources.sock')
        self.config = str(self.dir / 'helper' / 'sources.json')
        self.fake = await FakeHelper(config=self.config).start(self.socket)
        self.bridge = Sources(self.socket, str(self.dir / 'default.json'),
                              timeouts={'status': .5, 'reload': .5, 'test': .5, 'secrets': .5})

    async def asyncTearDown(self):
        await self.fake.stop()
        self.tmp.cleanup()

    async def test_list_put_test_secrets(self):
        put = await self.bridge.handle({'type': 'sources.put', 'seq': 1, 'entry': dict(HTTP)})
        self.assertEqual((put['op'], put['ok'], put['path'], put['reload']), ('put', True, self.config, {'ok': True}))
        listed = await self.bridge.handle({'type': 'sources.list', 'seq': 2})
        self.assertEqual((listed['op'], listed['exists'], [e['id'] for e in listed['entries']]), ('list', True, ['ingest']))
        self.assertTrue(listed['status']['ok'])
        test = await self.bridge.handle({'type': 'sources.testSource', 'seq': 3, 'source': {k: v for k, v in HTTP.items() if k != 'id'}})
        self.assertEqual(test['result']['raw'], TEST_HTTP['raw'])
        self.assertEqual(test['result']['secrets'], {'api-key': 'file'})
        sent = self.fake.requests[-1]
        self.assertEqual((sent['op'], sent['source']['url'], 'id' in sent['source']), ('test', HTTP['url'], False))
        secrets = await self.bridge.handle({'type': 'sources.secrets', 'seq': 4})
        self.assertEqual(secrets['secrets'], SECRETS)

    async def test_secret_set_never_echoes_the_value(self):
        path = self.dir / 'secrets.json'
        with mock.patch.dict(SECRETS, {'file': str(path)}):
            reply = await self.bridge.handle({'type': 'sources.secretSet', 'seq': 5, 'name': 'api-key', 'value': 'k-123456', 'store': 'file'})
        self.assertEqual((reply['ok'], reply['name'], reply['store']), (True, 'api-key', 'file'))
        self.assertNotIn('k-123456', json.dumps(reply))
        self.assertEqual(json.loads(path.read_text()), {'api-key': 'k-123456'})
        bad = await self.bridge.handle({'type': 'sources.secretSet', 'name': 'api-key', 'value': 'v', 'store': 'cloud'})
        self.assertFalse(bad['ok'])
        test = await self.bridge.handle({'type': 'sources.testSource', 'source': {'kind': 'http', 'url': 'gopher://x'}})
        self.assertFalse(test['ok'])


class Page(unittest.TestCase):
    LIST = {'path': '/home/u/.config/hyprune/sources.json', 'exists': True, 'entries': [
        HTTP, {'id': 'cpu', 'kind': 'command', 'argv': ['hyprune-system-gauges', 'cpu'], 'intervalS': 5},
        {'id': 'pulse', 'kind': 'timer', 'timer': 'pulse'}, {'id': 'old', 'kind': 'command', 'argv': ['x'], 'enabled': False}],
        'status': {'ok': True, 'sources': {'ingest': {'lastRun': {'ok': False, 'error': 'HTTP 401 Unauthorized'}},
                                            'cpu': {'lastRun': {'ok': True, 'values': {'value': 12}}}, 'pulse': {'lastRun': None}}}}

    def test_rows_and_ids(self):
        rows = call('rows', self.LIST)
        self.assertEqual([(r['id'], r['kindLabel'], r['state'], r['editable']) for r in rows],
                         [('ingest', 'HTTP', 'error', True), ('cpu', 'Command', 'ok', True), ('pulse', 'timer', 'waiting', False),
                          ('old', 'Command', 'disabled', True)])
        self.assertEqual((rows[0]['target'], rows[0]['error']), ('POST api.example.com/lag', 'HTTP 401 Unauthorized'))
        self.assertEqual(call('freeId', self.LIST, 'http'), 'http-1')

    def test_draft_round_trip(self):
        d = call('draft', HTTP)
        self.assertEqual((d['valuePath'], d['reduce'], d['max'], d['levelMode'], d['warn'], d['label']),
                         ('$.items[*].lag', 'max', '60', 'thresholds', '50', 'Ingest'))
        self.assertEqual(d['headers'][0], {'name': 'Authorization', 'secret': 'ci-token', 'prefix': 'Bearer ', 'text': ''})
        built = call('entryFrom', d)
        self.assertEqual(built['error'], '')
        e = built['entry']
        for key in ('url', 'method', 'headers', 'body', 'map', 'intervalS'):
            self.assertEqual(e[key], HTTP[key], key)
        self.assertEqual((e['enabled'], e['output'], e['argv'], e['local'], e['timeoutS']), (None, None, None, None, None))
        self.assertEqual(call('testSource', e), {k: HTTP[k] for k in ('kind', 'url', 'method', 'headers', 'body', 'intervalS', 'map')})
        self.assertEqual(call('secretNames', d), ['api-key', 'ci-token'])

    def test_entry_from_a_form(self):
        d = call('draft', None, 'http', 'status')
        d.update({'url': 'https://h/s', 'valuePath': 'cpu.load', 'min': '0', 'max': '4', 'levelMode': 'match', 'matchPath': '$.state',
                  'match': 'Degraded=warn, down=fail', 'otherwise': 'ok', 'labelPath': '$.host', 'display': '{raw:.2f}'})
        e = call('entryFrom', d)['entry']
        self.assertEqual(e['map'], {'value': {'path': '$.cpu.load', 'min': 0, 'max': 4},
                                    'level': {'path': '$.state', 'match': {'degraded': 'warn', 'down': 'fail'}},
                                    'display': '{raw:.2f}', 'label': {'path': '$.host'}})
        command = call('draft', {'id': 'fan', 'kind': 'command', 'argv': ['sensors', '-j'], 'output': 'number',
                                 'map': {'value': {'field': 'value', 'max': 5000}}})
        e = call('entryFrom', command)['entry']
        self.assertEqual((e['argv'], e['output'], e['map'], e['url']), (['sensors', '-j'], 'number', {'value': {'field': 'value', 'max': 5000}}, None))
        errors = [({'id': 'X'}, 'lower-case'), ({'url': 'http://example.com'}, 'Local network'), ({'url': 'ftp://x'}, 'https://'),
                  ({'url': 'https://h', 'body': 'x'}, 'POST'), ({'url': 'https://h', 'method': 'POST', 'body': '{bad'}, 'like JSON'),
                  ({'url': 'https://h', 'levelMode': 'thresholds'}, 'Thresholds'), ({'url': 'https://h', 'levelMode': 'match', 'matchPath': '$.s', 'match': 'x=red'}, 'text=ok'),
                  ({'url': 'https://h', 'valuePath': '$.a', 'min': '5', 'max': '5'}, 'differ'), ({'url': 'https://h', 'interval': 'soon'}, 'interval')]
        for patch, message in errors:
            self.assertIn(message, call('entryFrom', {**call('draft', None, 'http', 'x'), **patch})['error'], patch)

    def test_test_view_and_secret_rows(self):
        view = call('testView', TEST_HTTP)
        self.assertEqual(view['line'], 'HTTP 200 · application/json · 84 B · 112 ms')
        self.assertEqual([r['key'] for r in view['rows']], ['value', 'level', 'label', 'display', 'name'])
        self.assertEqual(view['preview'], {'value': 66.67, 'level': 'warn', 'display': '40 s behind', 'label': 'Ingest'})
        failed = call('testView', {'error': 'HTTP 401 Unauthorized', 'httpStatus': 401, 'raw': '{"error": "bad token"}', 'values': {}})
        self.assertEqual((failed['ok'], failed['raw'], failed['preview']['value']), (False, '{"error": "bad token"}', None))
        rows = call('secretRows', ['api-key', 'ci-token', 'other'], SECRETS['names'])
        self.assertEqual([(r['origin'], r['known']) for r in rows], [('file', True), (None, True), (None, False)])
        self.assertEqual(rows[1]['text'], 'Not set: store it below')

    def test_qml_wiring(self):
        page = (ROOT / 'qml/components/DataSources.qml').read_text()
        for needle in ["'sources.list'", "'sources.put'", "'sources.testSource'", "'sources.secrets'", "'sources.secretSet'",
                       'echoMode: TextInput.Password', "objectName: 'test-raw'", "objectName: 'test-gauge'"]:
            self.assertIn(needle, page)
        objects = (ROOT / 'qml/components/DirectorObjects.qml').read_text()
        self.assertIn("{id: 'sources', label: 'Data sources'}", objects)
        self.assertIn('DataSources {', objects)


if __name__ == '__main__':
    unittest.main()
