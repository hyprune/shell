"""Director > Objects > Placed > Behaviours (RFC-0014 amendment: data-driven behaviours, IPC 0.31):
the pure helpers in qml/Behaviours.js (tested with node): new behaviours and their keys, the
editor's form and checks, the behaviour core takes, capturing A and B against the rest pose,
the list edits and what the panel says. Core's runtime is covered by its tests/behaviours.cpp,
the flow by nested --builder-shell."""
import json
from pathlib import Path
import math
import subprocess
import unittest
ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'qml/Behaviours.js').read_text()


def call(name, *args):
    return json.loads(subprocess.check_output(['node', '-e', SRC + '\nconsole.log(JSON.stringify(' + name + '(' + ', '.join(json.dumps(a) for a in args) + ')));'], text=True))


class Behaviours(unittest.TestCase):
    def test_new_and_keys(self):
        grow = call('newBehaviour', 'scale', [])
        self.assertEqual(grow, {'key': 'grow', 'property': 'scale', 'from': [1, 0.05, 1], 'to': [1, 1, 1], 'anchor': 'bottom'})
        self.assertEqual(call('newBehaviour', 'scale', [grow])['key'], 'grow-2')
        self.assertIsNone(call('newBehaviour', 'spin', []))

    def test_draft_round_trip_and_checks(self):
        b = {'key': 'height', 'property': 'scale', 'input': {'source': 'com.hyprune.sources.cpu', 'max': 400}, 'from': [1, 0.1, 1], 'to': [1, 3, 1],
             'anchor': 'bottom', 'easing': 'ease-out', 'smoothing': 0.5}
        d = call('draftFrom', b)
        self.assertEqual(d['from'], ['1', '0.1', '1'])
        self.assertEqual(call('draftErrors', d), [])
        self.assertEqual(call('fromDraft', d), b)
        plain = call('fromDraft', call('draftFrom', call('newBehaviour', 'colour', [])))
        self.assertNotIn('input', plain, 'defaults are left out')
        self.assertTrue(call('draftErrors', dict(d, **{'from': ['1', '0', '1']})))
        self.assertTrue(call('draftErrors', dict(d, min='5', max='5')))
        self.assertTrue(call('draftErrors', dict(d, source='Not a source')))
        vis = call('draftFrom', {'key': 'show', 'property': 'visible', 'above': 50})
        self.assertEqual(call('fromDraft', vis), {'key': 'show', 'property': 'visible', 'above': 50})
        self.assertTrue(call('draftErrors', dict(vis, above='', below='')))
        glow = call('draftFrom', call('newBehaviour', 'glow', []))
        self.assertEqual(call('fromDraft', glow), {'key': 'glow', 'property': 'glow', 'from': 0, 'to': 6, 'colour': '#30e0ff'})
        tex = call('draftFrom', call('newBehaviour', 'texture', []))
        self.assertEqual(call('fromDraft', tex)['mode'], 'scroll')

    def test_capture_against_rest(self):
        q = lambda deg: [0, math.sin(math.radians(deg) / 2), 0, math.cos(math.radians(deg) / 2)]
        rest = {'position': [10, 0, 5], 'rotation': q(90), 'scale': 1}
        moved = {'pose': {'position': [10, 1, 3], 'rotation': q(90)}, 'scale': 1}
        # The object faces +X after a 90 degree turn: 2 m towards -Z in the world is its own +X.
        self.assertEqual(call('capture', rest, moved, 'move'), [2, 1, 0])
        turned = {'pose': {'position': [10, 0, 5], 'rotation': q(135)}, 'scale': 2}
        self.assertEqual(call('capture', rest, turned, 'rotate'), [0, 45, 0])
        self.assertEqual(call('capture', rest, turned, 'scale'), [2, 2, 2])
        self.assertTrue(call('moved', rest, turned))
        self.assertFalse(call('moved', rest, {'pose': {'position': [10, 0, 5], 'rotation': q(90)}, 'scale': 1}))
        self.assertEqual(call('restParams', 'u-000001', rest)['scale'], 1)

    def test_list_and_texts(self):
        a, b = {'key': 'a', 'property': 'move', 'from': [0, 0, 0], 'to': [0, 1, 0]}, {'key': 'b', 'property': 'visible', 'above': 80}
        self.assertEqual([x['key'] for x in call('withBehaviour', [a, b], dict(a, key='a2'), 'a')], ['a2', 'b'], 'an edit keeps its place')
        self.assertEqual([x['key'] for x in call('without', [a, b], 'a')], ['b'])
        self.assertEqual(call('configureParams', 'u-000001', [b]), {'id': 'u-000001', 'patch': {'behaviours': [b]}})
        inst = {'id': 'u-000001', 'behaviours': [{'key': 'a', 'property': 'move', 'condition': 'fresh', 'value': 72, 't': 0.72, 'behaviour': a}]}
        self.assertEqual(call('listOf', inst), [a])
        self.assertEqual(call('stateText', call('stateOf', inst, 'a')), 'value 72 → 72%')
        self.assertEqual(call('stateText', None), 'not running')
        self.assertEqual(call('summaryText', a), 'Move: 0, 0, 0 → 0, 1, 0')
        self.assertEqual(call('summaryText', b), 'Show / hide: shown from 80')
        self.assertIn("this object's data source", call('inputText', 'u-000001', a))
        self.assertEqual(call('entryOf', 'com.hyprune.sources.cpu'), 'cpu')
        self.assertEqual(call('entryOf', 'org.example.ci'), '')

    def test_wiring(self):
        panel = (ROOT / 'qml/components/ObjectBehaviours.qml').read_text()
        for name in ['behaviour-add:', 'behaviour-save', 'behaviour-capture-', 'behaviour-source', 'behaviour-edit:', 'behaviour-remove:', 'behaviourEditor']:
            self.assertIn(name, panel, name)
        self.assertIn('ObjectBehaviours', (ROOT / 'qml/components/ObjectConfigure.qml').read_text())
        self.assertIn('focusSource', (ROOT / 'qml/components/DataSources.qml').read_text())


if __name__ == '__main__':
    unittest.main()
