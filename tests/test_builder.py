"""RFC-0014 world folders (phase 1 as amended): Director > Builder over the hyprune CLI's
`builder` commands. The pure helpers in qml/Builder.js (tested with node): validation, the
command lines, JSON-line jobs and what the page says. The CLI is covered by the SDK's tests,
core's editor mode by its catalog tests, and the whole flow by the nested --builder-shell check."""
import json
from pathlib import Path
import re
import subprocess
import unittest
ROOT = Path(__file__).resolve().parents[1]
BUILDER = (ROOT / 'qml/Builder.js').read_text()


def call(name, *args):
    return json.loads(subprocess.check_output(['node', '-e', BUILDER + '\nconsole.log(JSON.stringify(' + name + '(' + ', '.join(json.dumps(a) for a in args) + ')));'], text=True))


STATUS = {'projectId': 'harbour', 'worldId': 'local.harbour', 'name': 'Harbour', 'folder': '/home/u/.local/share/hyprune/projects/harbour',
          'version': '0.1.0', 'placements': 2, 'branch': 'main', 'head': 'abc', 'pending': {'added': 3, 'modified': 1, 'deleted': 0, 'total': 4},
          'lastSave': {'commit': 'abc', 'at': '2026-10-14T20:00:00Z', 'message': 'Save 2026-10-14 20:00 · placed 2 objects'},
          'lastVersion': None, 'suggestedVersion': '0.1.0', 'remote': None, 'identity': {'name': 'Ada', 'email': 'ada@example.com'},
          'sky': {'image': 'sky/panorama.jpg', 'license': 'CC0-1.0', 'author': 'Hyprune contributors', 'source': 'Generated'}}


class Validation(unittest.TestCase):
    def test_names_versions_remotes_identity_sky(self):
        self.assertEqual(call('nameError', '  Harbour plaza '), '')
        self.assertIn('name', call('nameError', '   '))
        self.assertIn('64', call('nameError', 'x' * 65))
        self.assertEqual([call('versionError', v) for v in ['', '0.2.0', '1.0.0-rc.1']], ['', '', ''])
        self.assertNotEqual(call('versionError', '1.0'), '')
        self.assertNotEqual(call('versionError', 'v1.0.0'), '')
        for good in ['git@github.com:ada/hyprune-world-harbour.git', 'https://github.com/ada/x', 'ssh://git@host:22/x.git', '']:
            self.assertEqual(call('remoteError', good), '', good)
        for bad in ['/srv/git/x', 'file:///x', 'ext::sh -c id', 'http://insecure/x']:
            self.assertNotEqual(call('remoteError', bad), '', bad)
        self.assertEqual(call('identityErrors', None), [])
        self.assertEqual(len(call('identityErrors', {'name': '', 'email': 'nope'})), 2)
        self.assertEqual(call('identityErrors', {'name': 'Ada', 'email': 'ada@example.com'}), [])
        self.assertTrue(call('skyImage', '/x/Dusk.JPG'))
        self.assertTrue(call('skyImage', '/x/dusk.hdr'))
        self.assertTrue(call('skyImage', '/x/studio.EXR'))
        self.assertFalse(call('skyImage', '/x/dusk.webp'))
        self.assertTrue(call('floorImage', '/x/tiles.jpg'))
        self.assertFalse(call('floorImage', '/x/tiles.exr'))
        self.assertEqual(call('skyErrors', {'preset': 'sunset'}), [])
        self.assertEqual(call('floorErrors', {'preset': 'grass', 'tile': None}), [])
        self.assertEqual(len(call('floorErrors', {'preset': 'grass', 'tile': '0.1'})), 1)
        self.assertEqual(len(call('floorErrors', {'path': '/x/t.jpg', 'license': '', 'author': '', 'source': '', 'tile': 2})), 3)
        self.assertEqual([call('tileError', t) for t in ['2', 0.25, 100]], ['', '', ''])
        self.assertNotEqual(call('tileError', ''), '')
        self.assertEqual(len(call('skyErrors', {'path': '/x/a.png', 'license': '', 'author': '', 'source': ''})), 3)
        self.assertEqual(call('skyErrors', {'path': '/x/a.png', 'license': 'CC0-1.0', 'author': 'Me', 'source': 'my camera'}), [])


class Commands(unittest.TestCase):
    def test_arguments(self):
        self.assertEqual(call('createArgs', ' Harbour ', None), ['builder', 'create', 'Harbour', '--json'])
        self.assertEqual(call('createArgs', 'Harbour', {'name': ' Ada ', 'email': 'ada@example.com'}),
                         ['builder', 'create', 'Harbour', '--json', '--git-name', 'Ada', '--git-email', 'ada@example.com'])
        self.assertEqual(call('saveArgs', 'harbour', '  '), ['builder', 'save', 'harbour', '--json'])
        self.assertEqual(call('saveArgs', 'harbour', ' Add the quay '), ['builder', 'save', 'harbour', '--json', '-m', 'Add the quay'])
        self.assertEqual(call('releaseArgs', 'harbour', '', ''), ['builder', 'release', 'harbour', '--json'])
        self.assertEqual(call('releaseArgs', 'harbour', '0.2.0', 'Notes'), ['builder', 'release', 'harbour', '0.2.0', '--json', '--notes', 'Notes'])
        self.assertEqual(call('skyArgs', 'harbour', {'path': '/x/a.jpg', 'license': 'CC0-1.0', 'author': 'Me', 'source': 'mine'}),
                         ['builder', 'sky', 'harbour', '/x/a.jpg', '--license', 'CC0-1.0', '--author', 'Me', '--source', 'mine', '--json'])
        self.assertEqual(call('remoteArgs', 'harbour', ''), ['builder', 'remote', 'harbour', '--clear', '--json'])
        self.assertEqual(call('skyArgs', 'harbour', {'preset': 'night'}), ['builder', 'sky', 'harbour', '--preset', 'night', '--json'])
        self.assertEqual(call('floorArgs', 'harbour', {'preset': 'sand'}), ['builder', 'floor', 'harbour', '--preset', 'sand', '--json'])
        self.assertEqual(call('floorArgs', 'harbour', {'tile': '3'}), ['builder', 'floor', 'harbour', '--tile', '3', '--json'])
        self.assertEqual(call('floorArgs', 'harbour', {'path': '/x/t.jpg', 'license': 'CC0-1.0', 'author': 'Me', 'source': 'mine', 'tile': 1.5}),
                         ['builder', 'floor', 'harbour', '/x/t.jpg', '--license', 'CC0-1.0', '--author', 'Me', '--source', 'mine', '--tile', '1.5', '--json'])
        wizard = dict(call('newWizard'), name='Garden', sky={'path': '/x/s.exr', 'license': 'CC0-1.0', 'author': 'Me', 'source': 'mine'},
                      floor={'preset': 'grass', 'tile': '3'}, facing='sun')
        self.assertEqual(call('createArgs', 'Garden', None, wizard),
                         ['builder', 'create', 'Garden', '--json', '--starter', 'open-plain', '--sky-image', '/x/s.exr', '--sky-license', 'CC0-1.0',
                          '--sky-author', 'Me', '--sky-source', 'mine', '--floor', 'grass', '--tile', '3', '--facing', 'sun'])
        self.assertEqual(call('skiesArgs'), ['builder', 'skies', '--json'])


class Wizard(unittest.TestCase):
    def test_steps(self):
        w = call('newWizard')
        self.assertEqual(call('wizardStep', w), 'name')
        self.assertIn('name', call('wizardErrors', w, None)[0])
        self.assertEqual(call('wizardErrors', dict(w, name='Garden'), None), [])
        self.assertEqual(len(call('wizardErrors', dict(w, name='Garden'), {'name': '', 'email': ''})), 2)
        w = call('wizardMove', dict(w, name='Garden'), 1)
        self.assertEqual(call('wizardStep', w), 'sky')
        self.assertEqual(call('wizardErrors', w, None), [])
        self.assertEqual(len(call('wizardErrors', dict(w, sky={'path': '', 'license': '', 'author': '', 'source': ''}), None)), 4)
        w = call('wizardMove', call('wizardMove', w, 1), 5)
        self.assertEqual(call('wizardStep', w), 'spawn')
        self.assertTrue(call('wizardLast', w))
        self.assertEqual(call('wizardStep', call('wizardMove', w, -9)), 'name')
        skies = [{'id': 'clear-day', 'name': 'Clear day'}]
        floors = [{'id': 'grid', 'name': 'Grid'}]
        self.assertEqual(call('wizardSummary', w, skies, floors), 'Open Plain · Clear day sky · Grid floor · sun behind you')
        self.assertEqual(call('floorLabel', {'preset': 'grid', 'tile': 5}, floors), 'Grid, every 5 m')
        hint = call('errorText', {'code': 'floor.invalid', 'message': 'There is no floor "lava"', 'hint': 'Floors: grid, grass'})
        self.assertEqual(hint, 'There is no floor "lava". Floors: grid, grass.')
        self.assertEqual(call('worldId', 'harbour'), 'local.harbour')


class Jobs(unittest.TestCase):
    def test_events_and_outcomes(self):
        job = call('newJob', 'release', 'harbour')
        job = call('jobEvent', job, json.dumps({'event': 'stage', 'stage': 'push'}))
        self.assertEqual(call('busyText', job), 'Pushing to the remote…')
        done = call('jobEvent', job, json.dumps({'event': 'done', 'result': {'tag': 'v0.1.0', 'pushed': False, 'release': None, 'warnings': []}}))
        self.assertEqual(call('resultText', done), 'Released v0.1.0 as a local tag.')
        self.assertEqual(call('jobEvent', job, 'not json'), job)
        failed = call('jobEvent', call('newJob', 'save', 'harbour'), json.dumps({'event': 'error', 'error': {'code': 'save.nothing', 'message': 'Nothing to save: there are no changes since the last save'}}))
        self.assertEqual(call('errorText', failed['error']), 'Nothing to save: there are no changes since the last save')
        auth = {'code': 'remote.auth', 'message': 'push failed: fatal: could not read Username'}
        self.assertIn('Set up access', call('errorText', auth))
        self.assertEqual(call('jobFinished', call('newJob', 'save', 'h'), -1, '')['error']['code'], 'cli.missing')
        self.assertEqual(call('jobFinished', call('newJob', 'save', 'h'), 1, 'x\nError: boom\n')['error']['message'], 'boom')
        self.assertEqual(call('jobFinished', done, 0, ''), done)
        sky = call('jobEvent', call('newJob', 'sky', 'h'), json.dumps({'event': 'done', 'result': {'width': 4096, 'height': 2048}}))
        self.assertIn('4096 × 2048', call('resultText', sky))
        self.assertEqual(call('warningsOf', {'result': {'warnings': ['GPU allocation and image decode budgets require core validation; this is an authoring check.', 'big file']}}), ['big file'])

    def test_page_texts(self):
        self.assertEqual(call('pendingText', STATUS), '4 files not saved')
        self.assertEqual(call('pendingText', dict(STATUS, changes='placed 2 objects')), 'Unsaved: placed 2 objects (4 files)')
        self.assertEqual(call('pendingText', dict(STATUS, pending={'added': 1, 'modified': 0, 'deleted': 0, 'total': 1})), '1 file not saved')
        self.assertEqual(call('pendingText', dict(STATUS, pending={'added': 0, 'modified': 0, 'deleted': 0, 'total': 0})), 'Everything is saved')
        self.assertEqual(call('lastSaveText', STATUS), 'Last save: Save 2026-10-14 20:00 · placed 2 objects')
        self.assertEqual(call('versionText', STATUS), 'Not released yet')
        self.assertEqual(call('versionText', dict(STATUS, lastVersion={'tag': 'v0.1.0'})), 'Latest version v0.1.0 (local tag)')
        self.assertIn('No remote', call('remoteText', STATUS))


class Wiring(unittest.TestCase):
    def test_page_and_state(self):
        page = (ROOT / 'qml/components/DirectorBuilder.qml').read_text()
        state = (ROOT / 'qml/ShellState.qml').read_text()
        for name in ['builder-new', 'builder-wizard-next', 'builder-wizard-back', 'builder-wizard-cancel', 'builder-sky-preset:', 'builder-floor-preset:',
                     'builder-facing:', 'builderTile', 'builder-set-sky:', 'builder-set-floor:', 'builder-floor-image', 'builder-floor-apply', 'builderFloorTile',
                     'builder-wizard-sky-image', 'builder-wizard-floor-image', 'builderName', 'builder-create', 'builderMessage', 'builder-save', 'builderVersion', 'builder-release', 'builder-sky', 'builder-sky-apply',
                     'builderRemote', 'builder-remote-set', 'builderPending', 'builderFeedback', 'builderSkyBrowser']:
            self.assertIn("'" + name, page, name)
        # Git and the network stay in the CLI: the shell only loads the folder over IPC.
        self.assertNotRegex(state, r"command: \['git'")
        self.assertIn("action('world.load', {worldId: Builder.worldId(slug)})", state)
        self.assertTrue(re.search(r'tabBuilder: 4', state))


if __name__ == '__main__':
    unittest.main()
