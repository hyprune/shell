"""Director > Objects > Shapes (RFC-0014 amendment: primitives and materials, IPC 0.31): the pure
helpers in qml/Shapes.js (tested with node): shape forms and checks, the CLI command lines in a
world folder and in the user's folders, the material editor, swaps after a rebuild and a placed
primitive's form. The CLI is covered by the SDK's tests, core's keys and swaps by nested
--builder-shell."""
import json
from pathlib import Path
import subprocess
import unittest
ROOT = Path(__file__).resolve().parents[1]
SHAPES = (ROOT / 'qml/Shapes.js').read_text()


def call(name, *args):
    return json.loads(subprocess.check_output(['node', '-e', SHAPES + '\nconsole.log(JSON.stringify(' + name + '(' + ', '.join(json.dumps(a) for a in args) + ')));'], text=True))


class Forms(unittest.TestCase):
    def test_shapes_sizes_and_checks(self):
        self.assertEqual([s['id'] for s in call('(()=>SHAPES)')], ['cube', 'box', 'cylinder', 'sphere', 'plane', 'ramp', 'stairs'])
        box = call('newForm', 'box')
        self.assertEqual(box['size'], [2, 1, 1])
        self.assertEqual(call('sizeErrors', box), [])
        self.assertEqual(call('withShape', box, 'stairs')['size'], [1.2, 1.8, 3])
        self.assertEqual(call('stepsFor', call('withShape', box, 'stairs')), 10)
        cube = call('setSize', call('newForm', 'cube'), 1, '2')
        self.assertEqual(cube['size'], ['2', '2', '2'], 'a cube keeps equal sides')
        self.assertEqual(len(call('sizeErrors', dict(box, size=['0', '1', '200']))), 2)
        self.assertIn('cube', call('sizeErrors', dict(call('newForm', 'cube'), size=[1, 2, 1]))[0])
        self.assertTrue(call('sizeErrors', dict(call('newForm', 'stairs'), steps='70')))
        self.assertTrue(call('sizeErrors', dict(box, material={'kind': 'colour', 'colour': 'red'})))
        self.assertTrue(call('sizeErrors', dict(box, material={'kind': 'key', 'key': ''})))
        self.assertEqual(call('hex', 'ABC'), '#aabbcc')
        self.assertEqual(call('hex', 'nope'), '')

    def test_command_lines(self):
        box = dict(call('newForm', 'box'), size=['2', '0.2', '1'], material={'kind': 'key', 'key': 'oak'})
        self.assertEqual(call('primitiveArgs', 'yard', box), ['builder', 'primitive', 'yard', '--shape', 'box', '--size', '2,0.2,1', '--material', 'oak', '--json'])
        glow = dict(call('newForm', 'cylinder'), material={'kind': 'colour', 'colour': '#202020', 'glow': {'colour': '#30e0ff', 'strength': '4'}})
        self.assertEqual(call('primitiveArgs', '', glow), ['object', 'primitive', '--shape', 'cylinder', '--size', '1,2,1', '--colour', '#202020',
                                                         '--emissive', '#30e0ff', '--emissive-strength', '4', '--json'])
        stairs = dict(call('newForm', 'stairs'), steps='8')
        self.assertIn('--steps', call('primitiveArgs', 'yard', stairs))
        self.assertEqual(call('materialsArgs', ''), ['object', 'materials', '--json'])
        self.assertEqual(call('rebuildArgs', 'yard', 'oak'), ['builder', 'rebuild', 'yard', '--material', 'oak', '--json'])


class Materials(unittest.TestCase):
    def test_editor(self):
        m = call('newMaterial', '')
        self.assertTrue(call('materialErrors', m))
        m = dict(m, key='oak', texture={'kind': 'preset', 'preset': 'paving'}, tile='1.5')
        self.assertEqual(call('materialErrors', m), [])
        self.assertEqual(call('materialArgs', 'yard', m), ['builder', 'material', 'yard', 'oak', '--colour', '#ffffff', '--texture-preset', 'paving', '--tile', '1.5', '--json'])
        image = dict(m, texture={'kind': 'image', 'path': '/x/oak.jpg', 'license': '', 'author': '', 'source': ''})
        self.assertEqual(len(call('materialErrors', image)), 3)
        image['texture'].update(license='CC0-1.0', author='Me', source='my photo')
        self.assertIn('--texture', call('materialArgs', '', image))
        self.assertIn('Only a textured', ' '.join(call('materialErrors', dict(m, texture={'kind': 'none'}))))
        self.assertTrue(call('materialErrors', dict(m, roughness='2')))
        self.assertEqual(call('materialFrom', {'key': 'oak', 'name': 'Oak', 'colour': '#ffeedd', 'textured': True, 'tile': 1.5})['tile'], '1.5')
        off = dict(m, glow=None, glowOff=True)
        self.assertIn('--no-emissive', call('materialArgs', 'yard', off))


class Placed(unittest.TestCase):
    def test_swaps_and_forms(self):
        instances = [{'id': 'u-000001', 'source': 'user', 'ref': 'world/box-aaa'}, {'id': 'u-000002', 'source': 'user', 'ref': 'world/box-bbb'},
                     {'id': 'desk', 'source': 'authored', 'ref': 'world/box-aaa'}]
        self.assertEqual(call('swapsFor', instances, [{'from': 'world/box-aaa', 'to': 'world/box-ccc'}]), [{'id': 'u-000001', 'ref': 'world/box-ccc'}])
        entry = {'primitive': {'shape': 'box', 'size': [2, 0.2, 1], 'material': {'key': 'oak', 'name': 'Oak', 'colour': '#ffffff', 'textured': True}}}
        form = call('formFromEntry', entry)
        self.assertEqual(form['material'], {'kind': 'key', 'key': 'oak', 'colour': '#ffffff', 'glow': None})
        self.assertTrue(call('sameShape', form, entry))
        self.assertFalse(call('sameShape', call('setSize', form, 1, '0.3'), entry))
        self.assertIsNone(call('formFromEntry', {'primitive': None}))
        self.assertEqual(call('keyError', 'cpu-tower'), '')
        self.assertNotEqual(call('keyError', 'CPU tower'), '')
        self.assertEqual(call('summary', form, [{'key': 'oak', 'name': 'Oak planks'}]), 'Box 2 × 0.2 × 1 m · Oak planks')
        self.assertEqual(call('errorText', {'code': 'primitive.invalid', 'message': 'There is no shape "torus"', 'hint': 'Shapes: cube, box'}),
                         'There is no shape "torus". Shapes: cube, box.')


class Wiring(unittest.TestCase):
    def test_views_and_state(self):
        page = (ROOT / 'qml/components/ObjectShapes.qml').read_text() + (ROOT / 'qml/components/ShapeForm.qml').read_text()
        edit = (ROOT / 'qml/components/ObjectConfigure.qml').read_text()
        for name in ['shape-make', 'material-new', 'material-save', 'materialKey', 'materialTexture', "form.prefix + ':'", "form.prefix + 'Size'", "form.prefix + '-material:'"]:
            self.assertIn(name, page, name)
        for name in ['objectShapeEdit', 'objectKey', 'object-key-set', 'shape-apply']:
            self.assertIn(name, edit, name)
        state = (ROOT / 'qml/ShellState.qml').read_text()
        self.assertIn("objectAction('objects.configure', {id: job.id, patch: {ref: r.ref}})", state)
        self.assertIn('supportsProtocol(31)', state)


if __name__ == '__main__':
    unittest.main()
