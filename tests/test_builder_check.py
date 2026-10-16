"""RFC-0014 Phase D in the Director: the Builder page's checklist (`builder check`), Release
refused by open blocking items with Release anyway, the official-publishing line; imports from a
.zip with a model chooser and licence-file suggestions; an import's Model section (`object
fit|adjust|simplify`) and Repair on invalid entries. Pure helpers run with node."""
import json
from pathlib import Path
import subprocess
import unittest
ROOT = Path(__file__).resolve().parents[1]


def run(src, name, *args):
    code = (ROOT / src).read_text() + '\nconsole.log(JSON.stringify(' + name + '(' + ', '.join(json.dumps(a) for a in args) + ')));'
    return json.loads(subprocess.check_output(['node', '-e', code], text=True))


CHECK = {'ready': False, 'items': [
    {'id': 'spawn.floor', 'label': 'Spawn on the floor', 'done': True, 'blocks': True, 'level': 'done', 'message': 'ok'},
    {'id': 'screen.approach', 'label': 'Screen approach clear: Wall', 'done': False, 'blocks': True, 'level': 'open', 'message': 'blocked', 'target': 'u-000001', 'show': {'position': [0, 0, -3]}},
    {'id': 'rights', 'label': 'Record licences', 'done': False, 'blocks': False, 'level': 'warning', 'message': 'unknown'},
    {'id': 'save', 'label': 'Save', 'done': True, 'blocks': False, 'level': 'done', 'message': 'saved'}]}


class Checklist(unittest.TestCase):
    def test_args_marks_summary(self):
        self.assertEqual(run('qml/Builder.js', 'checkArgs', 'harbour'), ['builder', 'check', 'harbour', '--json'])
        self.assertEqual([run('qml/Builder.js', 'checkMark', i) for i in CHECK['items']], ['✓', '✗', '!', '✓'])
        self.assertEqual(run('qml/Builder.js', 'checkSummary', CHECK), '2 of 4 done · 1 to fix before Release')
        self.assertEqual(run('qml/Builder.js', 'checkSummary', None), 'Checking…')
        self.assertEqual([i['id'] for i in run('qml/Builder.js', 'checkBlocking', CHECK)], ['screen.approach'])

    def test_release_anyway(self):
        self.assertEqual(run('qml/Builder.js', 'releaseArgs', 'harbour', '0.2.0', '', True), ['builder', 'release', 'harbour', '0.2.0', '--json', '--skip-check'])
        self.assertNotIn('--skip-check', run('qml/Builder.js', 'releaseArgs', 'harbour', '', '', False))
        refused = {'kind': 'release', 'phase': 'failed', 'error': {'code': 'release.check', 'message': '1 checklist item is open'}}
        self.assertTrue(run('qml/Builder.js', 'releaseRefused', refused))
        self.assertFalse(run('qml/Builder.js', 'releaseRefused', dict(refused, error={'code': 'release.unsaved'})))
        self.assertIn('official bar', run('qml/Builder.js', 'publishingText', {'publishing': {'officialEligible': True}}))
        self.assertIn('2 parts', run('qml/Builder.js', 'publishingText', {'publishing': {'officialEligible': False, 'notOfficial': [{}, {}]}}))

    def test_page_wiring(self):
        page = (ROOT / 'qml/components/DirectorBuilder.qml').read_text()
        for name in ['builderCheckSummary', "'builderCheck:'", 'builder-release-anyway', 'builderPublishing', 'ShellState.builderShow']:
            self.assertIn(name, page)
        state = (ROOT / 'qml/ShellState.qml').read_text()
        self.assertIn('builderCheckTimer.restart()', state)
        self.assertIn("waypoint({id: 'builder-check'", state)


class Zip(unittest.TestCase):
    def test_zip_choose_and_hints(self):
        self.assertTrue(run('qml/Import.js', 'importable', '/x/Pack.ZIP'))
        self.assertEqual(run('qml/Import.js', 'inspectArgs', '/x/p.zip', 'a/b.gltf'), ['object', 'import', '/x/p.zip', '--inspect', '--json', '--entry', 'a/b.gltf'])
        job = run('qml/Import.js', 'newJob', 'inspecting', '/x/p.zip')
        line = json.dumps({'event': 'error', 'error': {'rule': 'import.entry', 'message': 'two', 'models': ['a.glb', 'b/c.gltf']}})
        chosen = run('qml/Import.js', 'jobEvent', job, line)
        self.assertEqual([chosen['phase'], chosen['models']], ['choose', ['a.glb', 'b/c.gltf']])
        form = run('qml/Import.js', 'defaultForm', {'name': 'P'})
        self.assertEqual(run('qml/Import.js', 'jobArgs', '/x/p.zip', form, 'a.glb')[-2:], ['--entry', 'a.glb'])
        insp = {'archive': {'name': 'p.zip', 'entry': 'a.glb', 'files': 3, 'models': ['a.glb'], 'licenseFiles': [{'path': 'LICENSE', 'text': 'CC0  1.0\nUniversal'}]}}
        self.assertEqual(run('qml/Import.js', 'licenceHints', insp), ['LICENSE: CC0 1.0 Universal'])
        self.assertEqual(run('qml/Import.js', 'archiveNote', insp), 'From p.zip: a.glb (3 files)')


class ModelSection(unittest.TestCase):
    def test_edit_args_and_texts(self):
        self.assertEqual(run('qml/Objects.js', 'editArgs', 'adjust', 'world/barrel', 'harbour', {'units': 'cm', 'yaw': '90'}),
                         ['object', 'adjust', 'world/barrel', '--project', 'harbour', '--units', 'cm', '--yaw', '90', '--json'])
        self.assertEqual(run('qml/Objects.js', 'editArgs', 'simplify', 'user/barrel', 'harbour', {'maxTriangles': '2000', 'maxTexture': '1024'}),
                         ['object', 'simplify', 'user/barrel', '--max-triangles', '2000', '--max-texture', '1024', '--json'])
        self.assertEqual(run('qml/Objects.js', 'editArgs', 'fit', 'user/barrel', '', None), ['object', 'fit', 'user/barrel', '--json'])
        self.assertTrue(run('qml/Objects.js', 'editable', {'ref': 'world/barrel'}, {'imported': {'at': 'x'}}))
        self.assertFalse(run('qml/Objects.js', 'editable', {'ref': 'library/x@1/y'}, {'imported': {'at': 'x'}}))
        self.assertFalse(run('qml/Objects.js', 'editable', {'ref': 'user/box'}, {'imported': None}))
        self.assertEqual(run('qml/Objects.js', 'fitText', {'fit': {'units': 'cm', 'scale': 0.01, 'up': 'z', 'yaw': 90, 'surface': 'floor'}}),
                         'Fitted as cm, Z up, turned 90°, on the floor.')
        self.assertEqual(run('qml/Objects.js', 'editResultText', 'simplify', {'before': {'triangles': 900, 'maxTexture': 2048}, 'after': {'triangles': 400, 'maxTexture': 1024}}),
                         'Simplified: 900 → 400 triangles; textures 2048 → 1024 px.')

    def test_wiring(self):
        self.assertIn('ObjectFitPanel', (ROOT / 'qml/components/ObjectConfigure.qml').read_text())
        self.assertIn("objectEditRun('repair'", (ROOT / 'qml/components/ObjectCard.qml').read_text())
        self.assertIn("builderOpen(builderState.projectId); else refreshCatalog()", (ROOT / 'qml/ShellState.qml').read_text())


if __name__ == '__main__':
    unittest.main()
