"""RFC-0015 phase 1: Director > Library over the hyprune CLI's JSON contract. The pure helpers
in qml/Library.js (tested with node), fed with the documents and JSON lines the development
fake CLI (dev/fake-hyprune-cli.py) prints, and the page's plain-text and confirmation rules."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
LIBRARY = (ROOT / 'qml/Library.js').read_text()
FAKE = [sys.executable, str(ROOT / 'dev/fake-hyprune-cli.py')]


def js(expression, *args):
    return json.loads(subprocess.check_output(
        ['node', '-e', LIBRARY + '\nconsole.log(JSON.stringify(' + expression + '));', *args], text=True))


class FakeCli:
    """The fake CLI on a private state directory, without delays."""

    def __init__(self):
        self.dir = tempfile.TemporaryDirectory(prefix='hyprune-fake-cli-test-')
        self.env = {**os.environ, 'HYPRUNE_FAKE_CLI_STATE': self.dir.name, 'HYPRUNE_FAKE_CLI_DELAY': '0'}
        subprocess.check_call(FAKE + ['reset'], env=self.env)

    def __enter__(self): return self
    def __exit__(self, *exc): self.dir.cleanup()

    def run(self, *args):
        done = subprocess.run(FAKE + list(args), env=self.env, capture_output=True, text=True)
        return done.returncode, done.stdout, done.stderr

    def doc(self, *args):
        code, out, _ = self.run(*args)
        assert code == 0, out
        return json.loads(out)

    def lines(self, *args):
        code, out, err = self.run(*args)
        return code, [l for l in out.splitlines() if l.strip()], err


def replay(job, lines, code, stderr=''):
    """Feed JSON lines and the exit code through jobEvent / jobFinished."""
    return js('(function(){ var j = %s; %s.forEach(function(l){ j = jobEvent(j, l); }); return jobFinished(j, %d, %s); })()'
              % (json.dumps(job), json.dumps(lines), code, json.dumps(stderr)))


class Command(unittest.TestCase):
    def test_cli_command_from_environment(self):
        self.assertEqual(js('cliCommand("")'), ['hyprune'])
        self.assertEqual(js('cliCommand(undefined)'), ['hyprune'])
        self.assertEqual(js('cliCommand("  node  /opt/sdk/dist/src/cli.js ")'), ['node', '/opt/sdk/dist/src/cli.js'])

    def test_job_arguments(self):
        self.assertEqual(js('jobArgs("install", "a.b", "community", "plan")'), ['install', 'a.b', '--from', 'community', '--plan', '--json'])
        self.assertEqual(js('jobArgs("install", "a.b", "community", "yes")'), ['install', 'a.b', '--from', 'community', '--yes', '--json'])
        self.assertEqual(js('jobArgs("install", "a.b", "custom", "yes", true)'),
                         ['install', 'a.b', '--from', 'custom', '--yes', '--accept-source-change', '--json'])
        self.assertEqual(js('jobArgs("update", "a.b", "", "plan")'), ['update', 'a.b', '--plan', '--json'])
        self.assertEqual(js('jobArgs("remove", "a.b", "", "yes")'), ['remove', 'a.b', '--yes', '--json'])


class Browse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cli = FakeCli()
        cls.addClassCleanup(cls.cli.dir.cleanup)
        cls.entries = cls.cli.doc('browse', '--json')['entries']
        cls.sources = cls.cli.doc('source', 'list', '--json')['sources']

    def entry(self, source, id):
        return next(e for e in self.entries if e['sourceId'] == source and e['id'] == id)

    def test_listing_documents_carry_the_contract_fields(self):
        for e in self.entries:
            self.assertLessEqual({'sourceId', 'display', 'tier', 'id', 'type', 'name', 'summary', 'creator', 'repo', 'tags', 'latest',
                                  'licenceNote', 'thumbnail', 'installed', 'update', 'versions'}, set(e))
            self.assertLessEqual({'tag', 'version', 'formatVersion', 'license', 'bytes', 'expandedBytes', 'published', 'loadable'}, set(e['latest']))
        for s in self.sources:
            self.assertLessEqual({'id', 'kind', 'label', 'display', 'enabled', 'builtin', 'system', 'lastRefresh', 'serial', 'entries', 'error'}, set(s))
        for i in self.cli.doc('content', 'list', '--json')['installs']:
            self.assertLessEqual({'id', 'type', 'sourceId', 'display', 'tag', 'version', 'previous', 'pinned', 'managed', 'removedFromSource',
                                  'newerTag', 'license', 'path'}, set(i))

    def test_labels_and_licence_wording(self):
        self.assertEqual(js('licenceText("CC-BY-4.0", "reviewed")'), 'CC-BY-4.0  ·  reviewed by Hyprune')
        self.assertEqual(js('licenceText("CC-BY-SA-4.0", "declared")'), 'CC-BY-SA-4.0  ·  declared by the creator, not reviewed')
        self.assertEqual(js('licenceText("MIT", "unchecked")'), 'MIT  ·  declared by the package, not checked')
        self.assertEqual(js('licenceText(null, "unchecked")'), 'No licence declared  ·  declared by the package, not checked')
        labels = js('%s.map(tierLabel)' % json.dumps(self.entries))
        self.assertEqual(sorted(set(labels)), ['Community registry', 'Custom: Frank\'s stuff', 'Official'])
        # The CLI's display text wins; content can't relabel itself (no display: kind-based fallback).
        self.assertEqual(js('tierLabel({tier: "custom", sourceId: "x", name: "Official"})'), 'Custom: x')
        self.assertEqual(js('[tierOf({display: "Official"}), tierOf({display: "Custom: Official"}), tierOf({tier: "community"})]'),
                         ['official', 'custom', 'community'])

    def test_sizes_hashes_and_times(self):
        self.assertEqual(js('[sizeText(512), sizeText(2048), sizeText(3 * 1048576 + 40000), sizeText(61 * 1048576), sizeText(null)]'),
                         ['512 bytes', '2.0 KiB', '3.0 MiB', '61 MiB', ''])
        self.assertEqual(js('shortHash("76312e322e3076312e322e30")'), '76312e322e30…')
        self.assertEqual(js('[timeText("2026-10-12T07:58:11Z"), timeText(null)]'), ['2026-10-12 07:58 UTC', ''])

    def test_filters_and_search(self):
        def ids(f): return [e['sourceId'] + '/' + e['id'] for e in js('filterEntries(%s, %s)' % (json.dumps(self.entries), json.dumps(f)))]
        self.assertEqual(len(ids({})), 8)
        self.assertEqual(ids({})[:3], ['official/com.hyprune.lumen-reach', 'official/com.hyprune.starter', 'official/com.hyprune.street'])
        self.assertEqual(len(ids({'type': 'library'})), 4)
        self.assertEqual(ids({'source': 'franks-stuff', 'type': 'world'}), ['franks-stuff/io.github.ada.tidepool'])
        self.assertEqual(ids({'query': 'COAST'}), ['official/com.hyprune.lumen-reach', 'community/io.github.ada.tidepool', 'franks-stuff/io.github.ada.tidepool'])
        self.assertEqual(ids({'query': 'boardwalk tide'}), ['community/io.github.ada.tidepool'])  # summary words
        self.assertEqual(ids({'query': 'ada'}), [])  # the creator is not search text
        choices = js('sourceChoices(%s, %s)' % (json.dumps(self.sources), json.dumps(self.entries)))
        self.assertEqual([c['id'] for c in choices], ['all', 'official', 'community', 'franks-stuff'])  # enabled sources with entries

    def test_badges_and_actions(self):
        def facts(source, id):
            e = self.entry(source, id)
            return [b['label'] for b in js('entryBadges(%s)' % json.dumps(e))], js('entryAction(%s)' % json.dumps(e))
        badges, action = facts('official', 'com.hyprune.lumen-reach')
        self.assertEqual(badges, ['Installed  lumen-reach-v0.9.1', 'Update  lumen-reach-v0.10.0'])
        self.assertEqual(action, {'kind': 'update', 'label': 'Update to lumen-reach-v0.10.0', 'enabled': True})
        self.assertEqual(facts('official', 'com.hyprune.street'), ([], {'kind': 'install', 'label': 'Install', 'enabled': True}))
        self.assertEqual(facts('community', 'io.github.cy.orbital'),
                         (['Needs a newer Hyprune'], {'kind': 'unavailable', 'label': 'Needs a newer Hyprune', 'enabled': False}))
        self.assertEqual(facts('official', 'com.hyprune.starter'),
                         (['Installed  ·  system'], {'kind': 'system', 'label': 'Installed by the system', 'enabled': False}))
        self.assertEqual(facts('franks-stuff', 'io.github.ada.tidepool'),
                         (['Installed from another source'], {'kind': 'switch', 'label': 'Install from this source', 'enabled': True}))


class Installed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cli = FakeCli()
        cls.addClassCleanup(cli.dir.cleanup)
        cls.installs = {i['id']: i for i in cli.doc('content', 'list', '--json')['installs']}
        cls.entries = cli.doc('browse', '--json')['entries']

    def actions(self, id): return [(a['id'], a['label'], a['enabled']) for a in js('installActions(%s)' % json.dumps(self.installs[id]))]

    def test_actions_per_install(self):
        self.assertEqual(self.actions('com.hyprune.lumen-reach'), [
            ('update', 'Update to lumen-reach-v0.10.0', True), ('rollback', 'Roll back to lumen-reach-v0.9.0', True),
            ('pin', 'Pin to lumen-reach-v0.9.1', True), ('remove', 'Remove', True)])
        # Pinned: the newer tag shows, Update waits for Unpin; no previous: no rollback.
        self.assertEqual(self.actions('io.github.ada.tidepool'), [
            ('update', 'Update to v1.2.0', False), ('rollback', 'No previous version', False), ('unpin', 'Unpin', True), ('remove', 'Remove', True)])
        self.assertEqual(self.actions('com.hyprune.starter'), [])  # system-managed: read only

    def test_rows(self):
        self.assertEqual([b['label'] for b in js('installBadges(%s)' % json.dumps(self.installs['io.github.ada.tidepool']))], ['PINNED', 'NEWER v1.2.0'])
        self.assertEqual([b['label'] for b in js('installBadges(%s)' % json.dumps(self.installs['io.github.dee.lanterns']))], ['REMOVED FROM SOURCE'])
        self.assertEqual(js('installSource(%s)' % json.dumps(self.installs['com.hyprune.starter'])), 'system')
        self.assertEqual(js('installSource({sourceId: null, managed: "user"})'), 'local')
        self.assertEqual(js('installName(%s, %s)' % (json.dumps(self.installs['io.github.ada.tidepool']), json.dumps(self.entries))), 'Tidepool')
        self.assertEqual(js('installName(%s, %s)' % (json.dumps(self.installs['io.github.dee.lanterns']), json.dumps(self.entries))), 'io.github.dee.lanterns')
        facts = {f['label']: f['value'] for f in js('installFacts(%s)' % json.dumps(self.installs['com.hyprune.lumen-reach']))}
        self.assertEqual(facts['Current'], 'lumen-reach-v0.9.1  (0.9.1)')
        self.assertEqual(facts['Previous'], 'lumen-reach-v0.9.0  (0.9.0)')
        self.assertEqual(facts['Source'], 'Official')


class Sources(unittest.TestCase):
    def form(self, url, label='', sha=''): return js('sourceForm(%s, %s, %s)' % (json.dumps(url), json.dumps(label), json.dumps(sha)))

    def test_add_source_form(self):
        self.assertEqual(self.form('github:frank/hyprune-stuff', "Frank's stuff")['args'],
                         ['source', 'add', 'github:frank/hyprune-stuff', '--label', "Frank's stuff", '--json'])
        self.assertTrue(self.form('github:hyprune/worlds/lumen-reach')['ok'])
        self.assertEqual(self.form('https://example.org/hyprune/v0.1/index.json')['args'],
                         ['source', 'add', 'https://example.org/hyprune/v0.1/index.json', '--json'])
        self.assertFalse(self.form('')['ok'])
        self.assertEqual(self.form('')['error'], '')
        for bad in ['http://example.org/index.json', 'github:frank', 'github:frank/stuff/Name With Space', 'ftp://x', 'example.org/index.json']:
            self.assertIn('https://', self.form(bad)['error'], bad)
        archive = self.form('https://example.org/x-1.0.0.tar.zst')
        self.assertTrue(archive['needsHash'] and not archive['ok'] and 'sha256' in archive['error'], archive)
        good = self.form('https://example.org/x-1.0.0.tar.zst', '', 'AB' * 32)
        self.assertEqual(good['args'], ['source', 'add', 'https://example.org/x-1.0.0.tar.zst', '--sha256', 'ab' * 32, '--json'])
        self.assertIn('48', self.form('github:a/b', 'x' * 49)['error'])
        self.assertIn('printable', self.form('github:a/b', 'a\u0007b')['error'])

    def test_source_rows(self):
        with FakeCli() as cli:
            sources = {s['id']: s for s in cli.doc('source', 'list', '--json')['sources']}
        self.assertEqual(js('sourceLocation(%s)' % json.dumps(sources['ada-worlds'])), 'github:ada/tidepool-world')
        self.assertEqual(js('sourceKind(%s)' % json.dumps(sources['studio-mirror'])), 'Index  ·  system')
        self.assertEqual(js('sourceStatus(%s)' % json.dumps(sources['official'])), {'level': 'muted', 'text': '3 entries  ·  refreshed 2026-10-12 07:58 UTC'})
        self.assertEqual(js('sourceStatus(%s)' % json.dumps(sources['ada-worlds']))['level'], 'warning')
        self.assertEqual(js('[%s].map(removable)' % ','.join(json.dumps(sources[k]) for k in ['official', 'community', 'franks-stuff', 'studio-mirror'])),
                         [False, False, True, False])
        self.assertIn('nobody has reviewed them', js('CUSTOM_NOTICE'))


class Jobs(unittest.TestCase):
    def setUp(self):
        self.cli = FakeCli()
        self.addCleanup(self.cli.dir.cleanup)

    def job(self, kind, id, source=''):
        return js('newJob(%s, %s, jobArgs(%s, %s, %s, "plan"))' % (json.dumps(kind), json.dumps({'id': id, 'sourceId': source, 'type': 'library', 'name': id}),
                                                                 json.dumps(kind), json.dumps(id), json.dumps(source)))

    def test_plan_then_confirm(self):
        code, lines, _ = self.cli.lines('install', 'com.hyprune.street', '--from', 'official', '--plan', '--json')
        job = replay(self.job('install', 'com.hyprune.street', 'official'), lines, code)
        self.assertEqual(job['phase'], 'confirm')
        rows = {r['id']: r['value'] for r in js('provenance(%s, [])' % json.dumps(job['plan']['packages'][0]))}
        self.assertEqual(set(rows), {'name', 'id', 'version', 'type', 'source', 'creator', 'licence', 'size', 'hash'})
        self.assertEqual(rows['licence'], 'CC0-1.0  ·  reviewed by Hyprune')
        self.assertEqual(rows['source'], 'Official  ·  https://hyprune.github.io/registry/v0.1/official.json')
        self.assertTrue(rows['hash'].endswith('…') and len(rows['hash']) == 13)
        self.assertEqual(rows['size'], '3.0 MiB download  ·  7.0 MiB installed')
        self.assertIsNone(js('sourceChange(%s)' % json.dumps(job['plan'])))
        self.assertIn('no code', js('DATA_ONLY'))
        # Then the confirmed run: stages and progress to done.
        code, lines, _ = self.cli.lines('install', 'com.hyprune.street', '--from', 'official', '--yes', '--json')
        done = replay(dict(job, phase='running'), lines, code)
        self.assertEqual(done['phase'], 'done')
        self.assertEqual(done['stages'], ['resolving', 'downloading', 'verifying', 'extracting', 'validating', 'committing'])
        self.assertEqual(done['result']['type'], 'library')
        self.assertEqual([r['state'] for r in js('stageRows(%s)' % json.dumps(done))], ['done'] * 6)
        self.assertEqual(js('resultText(%s, "Street furniture")' % json.dumps(done)), 'Installed Street furniture v1.2.0.')

    def test_requirements_listed(self):
        code, lines, _ = self.cli.lines('update', 'com.hyprune.lumen-reach', '--plan', '--json')
        job = replay(self.job('update', 'com.hyprune.lumen-reach'), lines, code)
        self.assertEqual(job['phase'], 'confirm')
        self.assertEqual([r['id'] for r in js('requirements(%s)' % json.dumps(job['plan']))], ['com.hyprune.street'])
        self.assertEqual(js('planTotal(%s)' % json.dumps(job['plan'])), 61 * 1048576 + 3 * 1048576 + 40000)

    def test_source_change_waits_for_explicit_confirmation(self):
        code, lines, _ = self.cli.lines('install', 'io.github.ada.tidepool', '--from', 'franks-stuff', '--plan', '--json')
        job = replay(self.job('install', 'io.github.ada.tidepool', 'franks-stuff'), lines, code)
        self.assertEqual(js('sourceChange(%s)' % json.dumps(job['plan'])),
                         {'id': 'io.github.ada.tidepool', 'from': 'Community registry', 'to': "Custom: Frank's stuff"})
        # --yes alone is refused by rule source.change (the plan event came first): still a confirmation.
        code, lines, _ = self.cli.lines('install', 'io.github.ada.tidepool', '--from', 'franks-stuff', '--yes', '--json')
        self.assertEqual(code, 3)
        self.assertEqual(replay(self.job('install', 'io.github.ada.tidepool', 'franks-stuff'), lines, code)['phase'], 'confirm')
        code, lines, _ = self.cli.lines('install', 'io.github.ada.tidepool', '--from', 'franks-stuff', '--yes', '--accept-source-change', '--json')
        self.assertEqual(replay(dict(job, phase='running'), lines, code)['phase'], 'done')

    def test_errors_keep_their_rule(self):
        code, lines, _ = self.cli.lines('install', 'org.example.frank.lamps', '--yes', '--json')
        job = replay(dict(self.job('install', 'org.example.frank.lamps'), phase='running'), lines, code)
        self.assertEqual((job['phase'], job['error']['rule']), ('failed', 'hash.mismatch'))
        self.assertEqual([r['state'] for r in js('stageRows(%s)' % json.dumps(job))], ['done', 'done', 'failed', 'pending', 'pending', 'pending'])
        text = js('errorText(%s)' % json.dumps(job['error']))
        self.assertIn('pinned sha256', text['line'])
        self.assertEqual(text['detail'], 'Rule: hash.mismatch  ·  the download doesn\'t match its pinned hash')
        code, lines, _ = self.cli.lines('install', 'io.github.cy.orbital', '--plan', '--json')
        job = replay(self.job('install', 'io.github.cy.orbital'), lines, code)
        self.assertEqual((job['phase'], job['error']['rule']), ('failed', 'format.unsupported'))
        code, lines, _ = self.cli.lines('remove', 'com.hyprune.starter', '--yes', '--json')
        self.assertEqual(replay(dict(self.job('remove', 'com.hyprune.starter'), phase='running', panel=False), lines, code)['error']['rule'], 'managed.system')

    def test_process_failures(self):
        missing = replay(self.job('install', 'a.b'), [], -1)
        self.assertEqual((missing['phase'], missing['error']['rule']), ('failed', 'cli.missing'))
        self.assertEqual([r['state'] for r in js('stageRows(%s)' % json.dumps(missing))][:2], ['failed', 'pending'])
        crashed = replay(self.job('install', 'a.b'), ['not json', '{"event":"stage","stage":"resolving"}'], 1, 'warning\nTypeError: x is undefined\n')
        self.assertEqual(crashed['error'], {'rule': '', 'message': 'TypeError: x is undefined'})
        self.assertEqual(crashed['stage'], 'resolving')
        progress = js('jobEvent(newJob("install", {}, []), %s)' % json.dumps(json.dumps({'event': 'progress', 'bytes': 1572864, 'total': 3145728})))
        self.assertEqual(js('progressText(%s)' % json.dumps(progress['progress'])), '1.5 MiB  /  3.0 MiB')
        self.assertEqual(js('progressFraction(%s)' % json.dumps(progress['progress'])), 0.5)

    def test_simple_jobs(self):
        code, lines, _ = self.cli.lines('rollback', 'com.hyprune.lumen-reach', '--yes', '--json')
        job = replay(js('newJob("rollback", {id: "com.hyprune.lumen-reach", name: "Lumen Reach"}, [])'), lines, code)
        self.assertEqual(job['phase'], 'done')
        self.assertFalse(job['panel'])
        self.assertEqual(js('resultText(%s, "Lumen Reach")' % json.dumps(job)), 'Rolled back Lumen Reach to lumen-reach-v0.9.0 and pinned it.')
        installs = {i['id']: i for i in self.cli.doc('content', 'list', '--json')['installs']}
        self.assertTrue(installs['com.hyprune.lumen-reach']['pinned'])
        toast = js('toast(%s, "Lumen Reach")' % json.dumps(job))
        self.assertEqual((toast['title'], toast['tone'], toast['category']), ('Library', 'info', 'objects'))


class Page(unittest.TestCase):
    """Wiring rules that live in QML."""

    def test_plain_text_and_no_links(self):
        for name in ['DirectorLibrary.qml', 'LibraryCard.qml', 'LibraryJob.qml']:
            text = (ROOT / 'qml/components' / name).read_text()
            self.assertNotRegex(text, r'RichText|StyledText|MarkdownText|openUrlExternally|onLinkActivated', name)
        self.assertIn('textFormat: Text.PlainText', (ROOT / 'qml/components/HudLabel.qml').read_text())

    def test_thumbnails_only_from_local_paths(self):
        card = (ROOT / 'qml/components/LibraryCard.qml').read_text()
        self.assertIn("charAt(0) === '/' ? 'file://' + card.entry.thumbnail : ''", card)

    def test_confirmation_before_yes(self):
        state = (ROOT / 'qml/ShellState.qml').read_text()
        plan = re.search(r'function libraryPlan\(.*?\n    }\n', state, re.S).group(0)
        self.assertIn("'plan'", plan)
        self.assertNotIn("'yes'", plan)
        confirm = re.search(r'function libraryConfirm\(.*?\n    }\n', state, re.S).group(0)
        self.assertIn("job.phase !== 'confirm'", confirm)
        self.assertIn('if (change && !acceptChange) return false;', confirm)
        job = (ROOT / 'qml/components/LibraryJob.qml').read_text()
        self.assertIn('if (change && !changeAsked) { changeAsked = true; return; }', job)


if __name__ == '__main__':
    unittest.main()
