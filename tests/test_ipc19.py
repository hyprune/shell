"""IPC 0.19 player settings, reticle and overlay colours: allowlist, wire payloads, patches.

Helper logic is tested with node; wire checks against the vendored 0.19 pin run once
protocol/v0.19 exists (the contract is pinned in a separate commit)."""
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bridge'))
from launch import shell_actions  # noqa: E402
from protocol import VALIDATORS, SUPPORTED_PROTOCOLS, frame  # noqa: E402

SCRIPT = (ROOT / 'qml/PlayerSettings.js').read_text()
PINNED = '0.19' in SUPPORTED_PROTOCOLS
OLDER = [v for v in SUPPORTED_PROTOCOLS if int(v.split('.')[1]) < 19]
PREVIOUS = OLDER[-1]
MOVEMENT = ['walk_speed', 'run_speed', 'view_bob', 'reach_grab', 'reach_mount', 'reach_placement']
RETICLE = ['reticle_style', 'reticle_size', 'reticle_thickness', 'reticle_gap', 'reticle_opacity',
           'reticle_outline', 'reticle_colour', 'reticle_dynamic']
TOKENS = ("{mono:'DejaVu Sans Mono',accent:{r:.84,g:.9,b:.98},text:{r:.95,g:.96,b:.98},gold:{r:.87,g:.78,b:.6},"
          "reticle:{r:.965,g:.961,b:.918},positive:{r:.349,g:.949,b:.6},warning:{r:1,g:.62,b:.349}}")
RANGES = "{ranges:{walk_speed:[0.5,20],run_speed:[0.5,30],reach_grab:[1,100]}}"
PATCH_CASES = [
    ("patch(%s,'walk_speed',4.26)" % RANGES, {'walk_speed': 4.3}),
    ("patch(%s,'run_speed',99)" % RANGES, {'run_speed': 30}),  # clamped to core's range
    ("patch(null,'reach_grab',0.2)", {'reach_grab': 1}),       # spec fallback range
    ("patch(null,'reticle_opacity',0.333)", {'reticle_opacity': 0.33}),
    ("patch(null,'reticle_thickness',2.5)", {'reticle_thickness': 2.5}),
    ("patch(null,'view_bob','off')", {'view_bob': 'off'}),
    ("patch(null,'reticle_style','chevron')", {'reticle_style': 'chevron'}),
    ("patch(null,'reticle_outline',false)", {'reticle_outline': False}),
    ("patch(null,'reticle_dynamic',true)", {'reticle_dynamic': True}),
    ("patch(null,'walk_speed',null)", {'walk_speed': None}),
]


def evaluate(expression):
    return json.loads(subprocess.check_output(
        ['node', '-e', SCRIPT + '\nconsole.log(JSON.stringify(' + expression + '));'], text=True))


def request(method, params, rid='r'):
    return {'jsonrpc': '2.0', 'id': rid, 'method': method, 'params': params}


def player_set(patch):
    return request('player.set', {'patch': patch})


class Allowlist(unittest.TestCase):
    def test_no_player_methods_before_0_19(self):
        for version in OLDER + ['0.99']:  # 0.99: unvendored, never assumed newer
            self.assertNotIn('player.get', shell_actions(version))
            self.assertNotIn('player.set', shell_actions(version))

    @unittest.skipUnless(PINNED, 'IPC 0.19 not vendored yet')
    def test_player_methods_from_0_19(self):
        self.assertEqual(set(shell_actions('0.19')) - set(shell_actions(PREVIOUS)), {'player.get', 'player.set'})
        self.assertIn('graphics.set', shell_actions('0.19'))  # older actions are inherited


class Helpers(unittest.TestCase):
    def test_reticle_colours_follow_protocol(self):
        old, new = evaluate('overlayStyle(%s,18)' % TOKENS), evaluate('overlayStyle(%s,19)' % TOKENS)
        self.assertNotIn('reticleColor', old)
        self.assertEqual(new['reticleColor'], [0.965, 0.961, 0.918])
        self.assertEqual(new['validColor'], [0.349, 0.949, 0.6])
        self.assertEqual(new['invalidColor'], [1, 0.62, 0.349])
        self.assertEqual({k: v for k, v in new.items() if k not in ['reticleColor', 'validColor', 'invalidColor']}, old)
        VALIDATORS[PREVIOUS].validate(request('overlay.style', {'leaseId': 'lease-1', 'style': old}))
        with self.assertRaises(Exception):
            VALIDATORS[PREVIOUS].validate(request('overlay.style', {'leaseId': 'lease-1', 'style': new}))

    def test_shell_state_sends_hud_theme_colours(self):
        qml = (ROOT / 'qml/ShellState.qml').read_text()
        self.assertIn('reticle:Tokens.hudForeground,positive:Tokens.hudPositive,warning:Tokens.hudWarning', qml)
        self.assertIn("action('overlay.style', {style:coreStyle()})", qml)

    def test_tokens_cover_both_themes_and_every_concept(self):
        tokens = (ROOT / 'qml/theme/Tokens.qml').read_text()
        for name in ['positive', 'warning']:
            self.assertRegex(tokens, r"property color %s: light \? '#[0-9a-f]{6}' : '#[0-9a-f]{6}'" % name)
        for name in ['hudPositive', 'hudWarning']:
            line = next(l for l in tokens.splitlines() if 'property color %s:' % name in l)
            self.assertIn("'Instrument'", line)
            self.assertIn("'Minimal'", line)
            self.assertEqual(len(re.findall("'#[0-9a-f]{6}'", line)), 3)

    def test_option_lists_follow_the_spec(self):
        self.assertEqual(evaluate('VIEW_BOB.map(o=>o.value)'), ['off', 'subtle', 'normal'])
        self.assertEqual(evaluate('RETICLE_STYLES.map(o=>o.value)'), ['cross_dot', 't_dot', 'circle_dot', 'dot', 'cross', 'chevron'])
        self.assertEqual(evaluate('RETICLE_STYLES.map(o=>o.name)'), ['Cross with dot', 'T with dot', 'Circle with dot', 'Dot', 'Cross', 'Chevron'])
        self.assertEqual(evaluate('MOVEMENT_KEYS'), MOVEMENT)
        self.assertEqual(evaluate('RETICLE_KEYS'), RETICLE)
        self.assertEqual(sorted(evaluate('Object.keys(DEFAULTS)')), sorted(MOVEMENT + RETICLE + evaluate('FEEL_KEYS')))  # feel: IPC 0.29
        self.assertEqual(evaluate('[FOV_RANGE,FOV_DEFAULT]'), [[30, 120], 65])

    def test_reset_patches_remove_overrides(self):
        self.assertEqual(evaluate('resetPatch(MOVEMENT_KEYS)'), {k: None for k in MOVEMENT})
        self.assertEqual(evaluate('resetPatch(RETICLE_KEYS)'), {k: None for k in RETICLE})

    def test_slider_and_choice_patches(self):
        for expression, expected in PATCH_CASES:
            self.assertEqual(evaluate(expression), expected, expression)

    def test_colour_presets_map_to_theme_or_rgb(self):
        presets = evaluate('RETICLE_COLOURS')
        self.assertEqual([p['name'] for p in presets], ['Theme', 'White', 'Yellow', 'Cyan', 'Magenta', 'Green'])
        self.assertEqual(presets[0]['value'], 'theme')
        self.assertTrue(all(len(p['value']) == 3 and all(0 <= c <= 1 for c in p['value']) for p in presets[1:]))
        self.assertEqual(evaluate("[colourIndex('theme'),colourIndex([1,1,1]),colourIndex([0.3,0.88,1]),colourIndex([0.1,0.2,0.3])]"), [0, 1, 3, -1])
        self.assertEqual(evaluate('colourNames([0.1,0.2,0.3])')[-1], 'Custom')  # set by Lua/SDK; kept until changed

    def test_display_formats(self):
        self.assertEqual(evaluate("[speed(4),metres(12.25),pixels(18),pixels(2.5),percent(0.9),degrees(64.6)]"),
                         ['4.0 m/s', '12.3 m', '18 px', '2.5 px', '90%', '65°'])

    def test_primary_hint_dims_only_when_the_action_cannot_land(self):
        states = ['hidden', 'neutral', 'typing', 'target', 'valid', 'out_of_range', 'invalid', 'holding']
        blocked = evaluate('%s.map(s=>reticleBlocked({interaction:{reticle:{state:s,action:"place"}}}))' % json.dumps(states))
        self.assertEqual(dict(zip(states, blocked)), {s: s in ['out_of_range', 'invalid'] for s in states})
        self.assertEqual(evaluate('[reticleBlocked(null),reticleBlocked({interaction:{mode:"world"}})]'), [False, False])  # < 0.19


@unittest.skipUnless(PINNED, 'IPC 0.19 not vendored yet')
class Wire(unittest.TestCase):
    """Every payload the shell builds validates against the 0.19 pin and is refused by older pins."""

    def setUp(self):
        self.v19 = VALIDATORS.get('0.19')
        self.patch_schema = self.v19.schema['$defs']['playerPatch']

    def test_player_requests(self):
        for message in [request('player.get', {}), player_set({'walk_speed': 5})]:
            frame(message, self.v19)
            with self.assertRaises(Exception):
                VALIDATORS[PREVIOUS].validate(message)
        with self.assertRaises(Exception):
            self.v19.validate(player_set({}))  # minProperties 1

    def test_options_ranges_and_keys_match_the_schema(self):
        props = self.patch_schema['properties']
        enum = lambda key: next(b['enum'] for b in props[key]['anyOf'] if 'enum' in b)
        self.assertEqual(evaluate('VIEW_BOB.map(o=>o.value)'), enum('view_bob'))
        self.assertEqual(evaluate('RETICLE_STYLES.map(o=>o.value)'), enum('reticle_style'))
        feel = evaluate('FEEL_KEYS')  # IPC 0.29 (tests/test_ipc29.py)
        for key, (low, high) in evaluate('RANGES').items():
            if key in feel:
                continue
            number = next(b for b in props[key]['anyOf'] if b.get('type') == 'number')
            self.assertEqual((number['minimum'], number['maximum']), (low, high), key)
        self.assertEqual(sorted(MOVEMENT + RETICLE), sorted(props))
        self.v19.validate(player_set({k: v for k, v in evaluate('DEFAULTS').items() if k not in feel}))

    def test_shell_patches_validate(self):
        patches = [evaluate('resetPatch(MOVEMENT_KEYS)'), evaluate('resetPatch(RETICLE_KEYS)')]
        patches += [evaluate(e) for e, _ in PATCH_CASES]
        patches += [{'reticle_colour': p['value']} for p in evaluate('RETICLE_COLOURS')]
        for patch in patches:
            self.v19.validate(player_set(patch))

    def test_overlay_style_and_fov(self):
        self.v19.validate(request('overlay.style', {'leaseId': 'lease-1', 'style': evaluate('overlayStyle(%s,19)' % TOKENS)}))
        wide = request('graphics.set', {'patch': {'fov': 120}})
        self.v19.validate(wide)
        with self.assertRaises(Exception):
            VALIDATORS[PREVIOUS].validate(wide)


if __name__ == '__main__':
    unittest.main()
