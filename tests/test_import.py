"""RFC-0014 imports (as amended): Director > Objects > Import… over the hyprune CLI's `object
import`. The pure helpers in qml/Import.js (tested with node): arguments, the review form,
the size preview, JSON-line events and outcomes. The CLI and core are covered by the SDK's
tests and the nested --import-shell check."""
import json
from pathlib import Path
import subprocess
import unittest
ROOT = Path(__file__).resolve().parents[1]
IMPORT = (ROOT / 'qml/Import.js').read_text()


def call(name, *args):
    return json.loads(subprocess.check_output(['node', '-e', IMPORT + '\nconsole.log(JSON.stringify(' + name + '(' + ', '.join(json.dumps(a) for a in args) + ')));'], text=True))


INSPECTION = {'file': '/home/u/barrel.gltf', 'name': 'Barrel', 'id': 'barrel', 'format': 'gltf', 'backend': 'gltf', 'bytes': 2046,
              'triangles': 12544, 'meshes': 1, 'materials': 1, 'textures': [{'name': 'staves', 'width': 2048, 'height': 1024, 'mimeType': 'image/png'}],
              'maxTexture': 2048, 'extent': [82, 82, 120], 'unitsGuess': 'cm', 'up': 'y', 'warnings': []}


class Form(unittest.TestCase):
    def test_files_and_defaults(self):
        self.assertTrue(call('importable', '/x/Model.GLB'))
        self.assertTrue(call('importable', '/x/crate.obj'))
        self.assertFalse(call('importable', '/x/scene.blend'))
        form = call('defaultForm', INSPECTION)
        self.assertEqual((form['name'], form['units'], form['up'], form['maxTriangles'], form['licence'], form['collision']),
                         ('Barrel', 'auto', 'y', '50000', 'unknown', 'convex'))

    def test_size_preview_follows_units_up_and_turn(self):
        form = call('defaultForm', INSPECTION)
        self.assertEqual(call('sizeText', call('sizeMetres', INSPECTION, form)), '0.82 × 0.82 × 1.2 m  (width × height × depth)')
        zup = dict(form, up='z')
        self.assertEqual([round(v, 6) for v in call('sizeMetres', INSPECTION, zup)], [0.82, 1.2, 0.82])
        self.assertEqual([round(v, 4) for v in call('sizeMetres', INSPECTION, dict(zup, units='m'))], [82, 120, 82])
        self.assertIn('Larger than 32 m', call('sizeWarning', call('sizeMetres', INSPECTION, dict(zup, units='m'))))
        self.assertIn('Very small', call('sizeWarning', call('sizeMetres', dict(INSPECTION, extent=[10, 10, 10]), dict(zup, units='mm'))))
        self.assertEqual(call('sizeWarning', [0.82, 1.2, 0.82]), '')
        self.assertTrue(call('unitsNote', INSPECTION, form).startswith('Auto: centimetres'))
        self.assertEqual(call('trianglesNote', INSPECTION, dict(form, maxTriangles='5000')), '12,544 triangles: simplified to about 5,000.')

    def test_errors_never_about_the_licence(self):
        form = call('defaultForm', INSPECTION)
        self.assertEqual(call('formErrors', form), [])
        self.assertEqual(call('formErrors', dict(form, licence='unknown', author='', source='')), [])
        self.assertEqual(len(call('formErrors', dict(form, name=' '))), 1)
        self.assertEqual(len(call('formErrors', dict(form, maxTriangles='50'))), 1)
        self.assertEqual(len(call('formErrors', dict(form, licence='other', licenceOther=''))), 1)

    def test_file_size(self):
        self.assertEqual([call('fileSize', b) for b in [500, 2046, 5 * 1048576, 3 * 1073741824]], ['500 bytes', '2 KiB', '5 MiB', '3 GiB'])

    def test_arguments(self):
        form = dict(call('defaultForm', INSPECTION), up='z', maxTriangles='5000', licence='CC0-1.0', author=' A. Modeller ', source='')
        self.assertEqual(call('inspectArgs', '/x/b.gltf'), ['object', 'import', '/x/b.gltf', '--inspect', '--json'])
        args = call('jobArgs', '/x/b.gltf', form)
        self.assertEqual(args[:4], ['object', 'import', '/x/b.gltf', '--json'])
        pairs = dict(zip(args[4::2], args[5::2]))
        self.assertEqual(pairs['--up'], 'z'); self.assertEqual(pairs['--max-triangles'], '5000'); self.assertEqual(pairs['--license'], 'CC0-1.0')
        self.assertEqual(pairs['--author'], 'A. Modeller'); self.assertNotIn('--source', pairs)
        unknown = call('jobArgs', '/x/b.gltf', call('defaultForm', INSPECTION))
        self.assertNotIn('--license', unknown)
        other = call('jobArgs', '/x/b.gltf', dict(call('defaultForm', INSPECTION), licence='other', licenceOther='MIT OR Apache-2.0'))
        self.assertEqual(other[other.index('--license') + 1], 'MIT OR Apache-2.0')


class Job(unittest.TestCase):
    def test_events(self):
        job = call('newJob', 'inspecting', '/x/b.gltf')
        job = call('jobEvent', job, json.dumps({'event': 'done', 'result': INSPECTION}))
        self.assertEqual((job['phase'], job['inspection']['id'], job['form']['name']), ('review', 'barrel', 'Barrel'))
        job = dict(job, phase='running')
        job = call('jobEvent', job, '{"event":"stage","stage":"simplify","message":"12544 -> 5000 triangles"}')
        self.assertEqual((job['stage'], job['stages'], job['message']), ('simplify', ['simplify'], '12544 -> 5000 triangles'))
        rows = call('stageRows', job)
        self.assertEqual([r['state'] for r in rows if r['id'] in ('read', 'simplify')], ['waiting', 'current'])
        self.assertEqual(call('jobEvent', job, 'not json'), job)
        result = {'id': 'barrel', 'ref': 'user/barrel', 'path': '/u/objects/barrel', 'warnings': [], 'manifest': {'name': 'Barrel'},
                  'before': {'triangles': 12544, 'maxTexture': 2048}, 'after': {'triangles': 4999, 'maxTexture': 1024, 'gpuBytes': 874983,
                  'collisionTriangles': 444, 'extent': [0.82, 1.2, 0.82]}}
        done = call('jobEvent', job, json.dumps({'event': 'done', 'result': result}))
        self.assertEqual(done['phase'], 'done')
        lines = call('resultLines', result)
        self.assertEqual(lines[0], 'Added to My objects as user/barrel')
        self.assertEqual(lines[1], '4,999 triangles (from 12,544)')
        self.assertIn('Collision proxy: 444 triangles', lines)
        self.assertIn('appears in the catalog', call('resultText', result))

    def test_failures(self):
        job = dict(call('newJob', 'running', '/x/b.blend'))
        failed = call('jobEvent', job, json.dumps({'event': 'error', 'error': {'message': 'b.blend: unsupported format', 'rule': 'import.unsupported'}}))
        self.assertEqual(failed['phase'], 'failed')
        self.assertTrue(call('errorText', failed['error']).startswith('That file type can\'t be imported'))
        crashed = call('jobFinished', job, 1, 'warning: x\nError: out of memory\n')
        self.assertEqual(crashed['error']['message'], 'out of memory')
        self.assertEqual(call('jobFinished', job, -1, '')['error']['rule'], 'cli.missing')
        self.assertEqual(call('jobFinished', dict(job, cancelled=True), 143, '')['error']['message'], 'Cancelled.')
        self.assertEqual(call('jobFinished', failed, 1, 'x'), failed)  # an error line already decided


if __name__ == '__main__':
    unittest.main()
