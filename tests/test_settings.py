"""Director Settings (IPC 0.30 presets and overrides): the categories, every row against the
schema, values and override state from each store, the requests that set and reset a row,
reset all, search, counts and the preset bar. SettingsModel.js runs under node."""
import json
import subprocess
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bridge'))
from launch import shell_actions  # noqa: E402
from preferences import DEFAULTS, validate  # noqa: E402
from protocol import VALIDATORS, frame  # noqa: E402

MODEL = (ROOT / 'qml/SettingsModel.js').read_text()
V30 = VALIDATORS['0.30']


def js(expression, **values):
    prelude = ''.join(f'var {k} = {json.dumps(v)};\n' for k, v in values.items())
    return json.loads(subprocess.check_output(['node', '-e', MODEL + '\n' + prelude + 'console.log(JSON.stringify(' + expression + '));'], text=True))


def entry(value, default, source='preset'):
    return {'value': value, 'default': default, 'source': source}


SETTINGS = {'preset': 'medium', 'overrides': 2, 'path': '/x/settings.json', 'error': '',
            'presets': [{'id': 'medium', 'name': 'Medium', 'description': 'Most GPUs.', 'values': {'graphics.quality': 'medium'},
                         'defaults': {'graphics.msaa': 1, 'graphics.target_fps': 60, 'player.walk_speed': 4}},
                        {'id': 'ultra', 'name': 'Ultra', 'description': 'Fastest.', 'values': {'graphics.quality': 'ultra'},
                         'defaults': {'graphics.msaa': 4, 'graphics.target_fps': 60, 'player.walk_speed': 4}}],
            'settings': {'graphics.msaa': entry(1, 1), 'graphics.target_fps': entry(110, 60, 'user'), 'player.walk_speed': entry(4, 4),
                         'player.run_speed': entry(12, 10, 'user'), 'graphics.outline_width_px': entry(3, None, 'user')},
            'keymapDefaults': {'longHoldMs': 1000, 'scopeVignette': True, 'invert_y': False, 'show_area_markers': False,
                               'modes': {'world': {'sprint': ['Shift_L'], 'down': ['Control_L']}}}}
KEYMAP = {'config': {'longHoldMs': 1000, 'scopeVignette': True, 'invert_y': True, 'show_area_markers': False,
                     'modes': {'world': {'sprint': ['Control_L'], 'down': ['Control_L']}}}}
GRAPHICS = {'config': {'msaa': None, 'target_fps': 110, 'quality': 'medium', 'outline_width_px': 3}, 'effective': {'msaa': 1, 'target_fps': 110},
            'overrides': {'target_fps': 110, 'msaa': None}}
PLAYER = {'config': {'walk_speed': 4, 'run_speed': 12, 'look_inertia': .03, 'move_inertia': .05}, 'defaults': {'walk_speed': 4, 'run_speed': 10}, 'overrides': {'run_speed': 12}}
GUIDANCE = {'config': {'markers.reveal_ms': 6000}, 'defaults': {'markers.reveal_ms': 4000}, 'overrides': {'markers.reveal_ms': 6000},
            'ranges': {'markers.reveal_ms': [1000, 15000]}, 'options': {}}
PREFS = dict(concept='Minimal', resource='gpu', worldStyles=True, curved=True, curvature=.8, theme='night')


def ctx(protocol='0.30', settings=SETTINGS):
    return {'protocol': protocol, 'settings': settings, 'graphics': GRAPHICS, 'player': PLAYER, 'guidance': GUIDANCE,
            'keymap': KEYMAP, 'prefs': PREFS}


class Rows(unittest.TestCase):
    def test_categories_and_keys(self):
        categories = js('CATEGORIES.map(c => c.id)')
        self.assertEqual(categories, ['display', 'movement', 'controls', 'hud', 'world', 'guidance', 'data', 'recording',
                                      'accessibility', 'advanced'])
        rows = js('ROWS')
        keys = [r['key'] for r in rows]
        self.assertEqual(len(keys), len(set(keys)), 'a setting has one home')
        self.assertTrue(all(r['category'] in categories for r in rows))
        d = V30.schema['$defs']
        for r in rows:
            store, name = r['key'].split('.', 1)
            if store == 'graphics':
                self.assertIn(name, d['graphicsConfig']['properties'], r['key'])
            elif store == 'player':
                self.assertIn(name, d['playerConfig']['properties'], r['key'])
            elif store == 'input':
                self.assertIn(name, d['inputConfig']['properties'], r['key'])
            elif store == 'shell':
                self.assertIn(name, DEFAULTS, r['key'])
            self.assertIn(r['kind'], ['choice', 'toggle', 'slider', 'cap', 'colour'], r['key'])
        self.assertEqual(js('SHELL_DEFAULTS'), {k: v for k, v in DEFAULTS.items() if k != 'version'})


class Entries(unittest.TestCase):
    def test_core_rows_read_settings_get(self):
        self.assertEqual(js("entry(ROWS.find(r => r.key === 'graphics.target_fps'), c)", c=ctx()), entry(110, 60, 'user'))
        self.assertTrue(js("overridden(ROWS.find(r => r.key === 'player.run_speed'), c)", c=ctx()))
        self.assertFalse(js("overridden(ROWS.find(r => r.key === 'graphics.msaa'), c)", c=ctx()))

    def test_older_cores_read_their_own_files(self):
        old = ctx('0.29', None)
        self.assertEqual(js("entry(ROWS.find(r => r.key === 'graphics.target_fps'), c)", c=old)['source'], 'user')
        self.assertEqual(js("entry(ROWS.find(r => r.key === 'graphics.msaa'), c)", c=old), entry(1, 1))  # null = inherit
        self.assertEqual(js("entry(ROWS.find(r => r.key === 'player.run_speed'), c)", c=old), entry(12, 10, 'user'))

    def test_input_guidance_and_shell(self):
        self.assertTrue(js("overridden(ROWS.find(r => r.key === 'input.invert_y'), c)", c=ctx()))
        self.assertTrue(js("overridden(ROWS.find(r => r.key === 'shell.concept'), c)", c=ctx()))
        rows = js("guidanceRows([{key: 'markers.reveal_ms', group: 'MARKERS', name: 'Reveal time', unit: 's', scale: .001, step: 500, type: 'number'}])")
        self.assertEqual(rows[0]['key'], 'guidance.markers.reveal_ms')
        self.assertEqual(js("format(r, 6000)", r=rows[0]), '6 s')
        self.assertTrue(js("overridden(r, c)", r=rows[0], c=ctx()))


class Requests(unittest.TestCase):
    def test_set_and_reset(self):
        row = "ROWS.find(r => r.key === 'graphics.msaa')"
        self.assertEqual(js(f"setRequest({row}, 2, c)", c=ctx()), {'type': 'core', 'params': {'set': {'graphics.msaa': 2}}})
        self.assertEqual(js(f"resetRequest({row}, c)", c=ctx()), {'type': 'core', 'params': {'reset': ['graphics.msaa']}})
        self.assertEqual(js(f"setRequest({row}, 2, c)", c=ctx('0.29', None)), {'type': 'graphics', 'patch': {'msaa': 2}})
        self.assertEqual(js(f"resetRequest({row}, c)", c=ctx('0.29', None)), {'type': 'graphics', 'patch': {'msaa': None}})
        inv = js("resetRequest(ROWS.find(r => r.key === 'input.invert_y'), c)", c=ctx())
        self.assertEqual((inv['type'], inv['config']['invert_y']), ('input', False))
        self.assertEqual(js("resetRequest(ROWS.find(r => r.key === 'shell.concept'), c)", c=ctx()), {'type': 'shell', 'patch': {'concept': 'Adventure'}})
        for request in [js(f"setRequest({row}, 2, c)", c=ctx())['params'], js(f"resetRequest({row}, c)", c=ctx())['params'], {'resetAll': True}]:
            frame({'jsonrpc': '2.0', 'id': 's', 'method': 'settings.set', 'params': request}, V30)

    def test_reset_all(self):
        reqs = js('resetAllRequests(c)', c=ctx())
        self.assertEqual([r['type'] for r in reqs], ['core', 'guidance', 'shell'])
        self.assertEqual(reqs[0]['params'], {'resetAll': True})
        self.assertEqual(reqs[1]['patch'], {'markers.reveal_ms': None})
        validate(reqs[2]['patch'])
        old = js('resetAllRequests(c)', c=ctx('0.29', None))
        self.assertEqual([r['type'] for r in old], ['graphics', 'player', 'guidance', 'shell'])
        self.assertEqual(old[0]['patch'], {'target_fps': None, 'msaa': None})


class Overview(unittest.TestCase):
    def test_counts_search_and_presets(self):
        counts = js('counts(c, [])', c=ctx())
        # display: target_fps + the outline width (a block key); movement: run_speed; controls: sprint rebound;
        # accessibility: invert_y; hud: the HUD concept.
        self.assertEqual({k: v for k, v in counts.items() if v}, {'display': 2, 'movement': 1, 'controls': 1, 'hud': 1, 'accessibility': 1, 'total': 6})
        self.assertEqual(js('reboundActions(c)', c=ctx()), [{'mode': 'world', 'action': 'sprint'}])
        self.assertEqual([r['key'] for r in js("search('smooth', c, [])", c=ctx())], ['player.look_inertia', 'player.move_inertia'])
        self.assertEqual(js("search('', c, [])", c=ctx()), [])
        self.assertEqual(js('presetList(c)', c=ctx()), [{'id': 'medium', 'name': 'Medium', 'description': 'Most GPUs.'},
                                                         {'id': 'ultra', 'name': 'Ultra', 'description': 'Fastest.'}])
        self.assertEqual(js("presetChanges(c, 'ultra')", c=ctx()), ['graphics.msaa'])  # target_fps is the user's
        self.assertEqual(js('presetList(c)', c=ctx('0.29', None)), [])


class Wiring(unittest.TestCase):
    def test_actions_preferences_and_director(self):
        self.assertIn('settings.set', shell_actions('0.30'))
        self.assertNotIn('settings.get', shell_actions('0.29'))
        self.assertEqual(validate({'theme': 'paper'}), {'theme': 'paper'})
        with self.assertRaises(ValueError):
            validate({'theme': 'neon'})
        director = (ROOT / 'qml/components/Director.qml').read_text()
        self.assertNotIn('"Performance"', director)
        self.assertNotIn('DirectorPerformance', director)
        settings = (ROOT / 'qml/components/DirectorSettings.qml').read_text()
        for name in ['settings-preset', 'settings-reset-all', 'settings-reset-all-confirm', 'settings-search', "'settings-category-' + modelData.id",
                     'InkSettings {', 'CompanionSettings {', 'ReticlePreview {', 'settings-open-data-sources']:
            self.assertIn(name, settings)
        row = (ROOT / 'qml/components/SettingRow.qml').read_text()
        for name in ["'overridden:' + root.row.key", "'reset:' + root.row.key", 'Model.resetRequest', 'Model.setRequest']:
            self.assertIn(name, row)
        # Renderer sliders apply when they settle, not on every step of a drag.
        for name in ["settles: root.row.key.startsWith('graphics.')", 'onSettled: v => { if (settles)', 'onMoved: if (!settles)', 'target: root.entry.value']:
            self.assertIn(name, row)
        self.assertIn('signal settled(real value)', (ROOT / 'qml/components/SettingSlider.qml').read_text())


if __name__ == '__main__':
    unittest.main()
