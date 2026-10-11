"""IPC 0.20 pocket actions and blueprint map levels: allowlist, wire payloads, Director helpers.

Helper logic (qml/Blueprint.js, qml/DirectorModel.js) is tested with node; wire checks run
against the vendored 0.20 pin."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from urllib.parse import unquote
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bridge'))
from launch import shell_actions  # noqa: E402
from protocol import VALIDATORS, SUPPORTED_PROTOCOLS, frame, validate_response  # noqa: E402

BLUEPRINT = (ROOT / 'qml/Blueprint.js').read_text()
MODEL = (ROOT / 'qml/DirectorModel.js').read_text()
FIXTURES = ROOT / 'dev/blueprint'
OLDER = [v for v in SUPPORTED_PROTOCOLS if int(v.split('.')[1]) < 20]
PREVIOUS = OLDER[-1]
TOKENS = ("{text:'#f1f4fb',muted:'#afbed1',accent:'#d7e6fa',gold:'#dec89a',line:'#3a5068',ink:'#0b1420',"
          "positive:'#8fdcaa',warning:'#f3a46b'}")


def evaluate(script, expression, *args):
    return json.loads(subprocess.check_output(
        ['node', '-e', script + '\nconsole.log(JSON.stringify(' + expression + '));', *args], text=True))


def blueprint(expression, *args):
    return evaluate(BLUEPRINT, expression, *args)


def model(expression):
    return evaluate(MODEL, expression)


def themed(svg):
    return blueprint('themed(process.argv[1], palette(%s))' % TOKENS, svg)


def request(method, params, rid='r'):
    return {'jsonrpc': '2.0', 'id': rid, 'method': method, 'params': params}


def level(id, name, low, high, path):
    svg = (FIXTURES / path).read_text()
    return {'id': id, 'name': name, 'minY': low, 'maxY': high, 'svg': svg, 'sha256': hashlib.sha256(svg.encode()).hexdigest()}


LEVELS = [level('ground', 'Ground', -2.0, 4.5, 'ground.svg'), level('upper', 'Upper decks', 4.5, 40.0, 'upper.svg')]


class Allowlist(unittest.TestCase):
    def test_pocket_methods_only_from_0_20(self):
        for version in OLDER + ['0.99']:  # 0.99: unvendored, never assumed newer
            self.assertNotIn('surface.pocket', shell_actions(version))
            self.assertNotIn('surface.unpocket', shell_actions(version))
        self.assertEqual(set(shell_actions('0.20')) - set(shell_actions(PREVIOUS)), {'surface.pocket', 'surface.unpocket'})
        self.assertIn('player.set', shell_actions('0.20'))  # older actions are inherited


class Wire(unittest.TestCase):
    """The shell's pocket payloads validate against the 0.20 pin and are refused by 0.19."""

    def setUp(self):
        self.v20 = VALIDATORS['0.20']

    def test_pocket_requests(self):
        for method in ['surface.pocket', 'surface.unpocket']:
            message = request(method, {'surfaceId': 'surface-terminal'})
            frame(message, self.v20)
            with self.assertRaises(Exception):
                VALIDATORS[PREVIOUS].validate(message)
            with self.assertRaises(Exception):
                self.v20.validate(request(method, {'surfaceId': 'x', 'extra': 1}))

    def test_pocket_results(self):
        validate_response({'jsonrpc': '2.0', 'id': 'r', 'result': {'revision': 4}}, 'surface.pocket', self.v20)
        for placed in [True, False]:
            validate_response({'jsonrpc': '2.0', 'id': 'r', 'result': {'revision': 5, 'placed': placed}}, 'surface.unpocket', self.v20)
        with self.assertRaises(Exception):
            validate_response({'jsonrpc': '2.0', 'id': 'r', 'result': {'revision': 5}}, 'surface.unpocket', self.v20)

    def test_fixture_levels_are_valid_map_levels(self):
        overview = (FIXTURES / 'overview.svg').read_text()
        value = {'svg': overview, 'sha256': hashlib.sha256(overview.encode()).hexdigest(), 'bounds': [-30, -30, 30, 30],
                 'worldToMap': [1 / 60, 0, 0, 1 / 60, 0.5, 0.5], 'levels': LEVELS}
        self.v20.evolve(schema={'$ref': self.v20.schema['$id'] + '#/$defs/map'}).validate(value)
        with self.assertRaises(Exception):
            VALIDATORS[PREVIOUS].evolve(schema={'$ref': VALIDATORS[PREVIOUS].schema['$id'] + '#/$defs/map'}).validate(value)
        for entry in LEVELS:  # the spec's class vocabulary only
            classes = set(__import__('re').findall(r'class="([^"]*)"', entry['svg']))
            self.assertLessEqual(classes, set(blueprint('ROLES')))


class Colouring(unittest.TestCase):
    def test_classed_elements_without_colours_get_the_role(self):
        out = themed('<svg viewBox="0 0 10 10"><rect class="floor" x="0" y="0" width="5" height="5"/><line class="wall" x1="0" y1="0" x2="1" y2="1"/></svg>')
        self.assertIn('<rect class="floor" x="0" y="0" width="5" height="5" fill="#d7e6fa" fill-opacity="0.10" stroke="none" />', out)
        self.assertIn('<line class="wall" x1="0" y1="0" x2="1" y2="1" fill="#f1f4fb" stroke="#f1f4fb" />', out)

    def test_own_colours_win_and_unclassed_elements_are_untouched(self):
        out = themed("<svg viewBox='0 0 10 10'><path class='wall' fill='none' d='M0 0'/><circle class=\"waypoint\" stroke=\"#ff0000\" r=\"1\"/>"
                     "<rect fill='#123456' width='1' height='1'/><rect width='2' height='2'/><g class='nonsense'><text>A &gt; B</text></g></svg>")
        self.assertIn("<path class='wall' fill='none' d='M0 0' stroke=\"#f1f4fb\" />", out)  # only the missing stroke
        self.assertIn('<circle class="waypoint" stroke="#ff0000" r="1" fill="#dec89a" />', out)
        self.assertIn("<rect fill='#123456' width='1' height='1'/>", out)
        self.assertIn("<rect width='2' height='2'/>", out)
        self.assertIn("<g class='nonsense'><text>A &gt; B</text></g>", out)  # unknown class: own colours

    def test_groups_and_text_labels(self):
        out = themed('<svg viewBox="0 0 1 1"><g class="grid" stroke-width="0.6"><path d="M0 0"/></g><text class="label" x="1">Hall</text></svg>')
        self.assertIn('<g class="grid" stroke-width="0.6" fill="none" stroke="#3a5068" stroke-opacity="0.45">', out)
        self.assertIn('<text class="label" x="1" fill="#afbed1" stroke="none">Hall</text>', out)

    def test_every_role_has_colours_from_the_theme(self):
        roles = blueprint('palette(%s)' % TOKENS)
        self.assertEqual(sorted(roles), sorted(blueprint('ROLES')))
        for name, style in roles.items():
            self.assertIn('fill', style, name)
            self.assertIn('stroke', style, name)
        paper = blueprint("palette({text:'#ff152e32',ink:'#ffeff3ed',muted:'bogus'})")  # QML #aarrggbb, bad values
        self.assertEqual(paper['wall']['stroke'], '#152e32')
        self.assertEqual(paper['opening']['fill'], '#eff3ed')
        self.assertEqual(paper['label']['fill'], '#888888')

    def test_unsafe_or_foreign_svgs_are_refused(self):
        for svg in ['<?xml version="1.0"?><svg/>', '<!DOCTYPE svg><svg/>', '<svg><use href="#a"/></svg>',
                    '<svg><a xlink:href="https://x"/></svg>', '<svg><script>alert(1)</script></svg>',
                    '<svg><rect fill="url(#g)"/></svg>', '<svg><style>@import "x"</style></svg>',
                    '<svg><image x="0"/></svg>', '<svg><foreignObject/></svg>', '<html><svg/></html>', '', 'x' * 65537]:
            self.assertEqual(themed(svg), '', svg[:40])
        self.assertEqual(blueprint('dataUrl("<svg><script/></svg>", palette({}))'), '')

    def test_fixture_levels_round_trip_to_data_urls(self):
        for entry in LEVELS:
            url = blueprint('dataUrl(process.argv[1], palette(%s))' % TOKENS, entry['svg'])
            self.assertTrue(url.startswith('data:image/svg+xml,'))
            svg = unquote(url[len('data:image/svg+xml,'):])
            self.assertNotIn('class="floor"/>', svg)
            self.assertEqual(svg.count('<'), entry['svg'].count('<'))  # no elements added or lost


class Levels(unittest.TestCase):
    LV = json.dumps([{k: v for k, v in l.items() if k != 'svg'} for l in LEVELS])
    GAP = '[{id:"a",minY:0,maxY:3},{id:"b",minY:6,maxY:9}]'

    def test_auto_level_follows_the_feet(self):
        # Eye height 1.7 above the feet: 1.7 = feet 0 (ground); 6.2 = feet 4.5 (upper, bands are [min, max)).
        cases = {1.7: 0, 6.19: 0, 6.2: 1, 41.0: 1, 100: 1, -10: 0}
        for eye, want in cases.items():
            self.assertEqual(blueprint('levelFor(%s,%r)' % (self.LV, eye)), want, eye)
        self.assertEqual(blueprint('[levelFor(%s,1.7+4.4),levelFor(%s,1.7+4.6)]' % (self.GAP, self.GAP)), [0, 1])  # nearest band
        self.assertEqual(blueprint('[levelFor([],1),levelFor(null,1),levelFor(%s,NaN)]' % self.LV), [-1, -1, 0])

    def test_manual_pick_overrides_until_it_disappears(self):
        self.assertEqual(blueprint('shownLevel(%s,"upper",1.7)' % self.LV), 1)
        self.assertEqual(blueprint('shownLevel(%s,"",8)' % self.LV), 1)
        self.assertEqual(blueprint('shownLevel(%s,"gone",1.7)' % self.LV), 0)
        self.assertEqual(blueprint('shownLevel([],"upper",1.7)'), -1)

    def test_map_key_tracks_overview_and_levels(self):
        self.assertEqual(blueprint('mapKey(null)'), '')
        self.assertEqual(blueprint('mapKey({sha256:"aa"})'), 'aa')
        self.assertEqual(blueprint('mapKey({sha256:"aa",levels:[{id:"g",sha256:"11"},{id:"u",sha256:"22"}]})'), 'aa|g:11,u:22')

    def test_zoom_and_pan_are_clamped(self):
        self.assertEqual(blueprint('[clampZoom(0.2),clampZoom(3),clampZoom(99),clampZoom(NaN)]'), [1, 3, 8, 1])
        self.assertEqual(blueprint('clampPan([500,-500],2,400,300)'), [200, -150])
        self.assertEqual(blueprint('clampPan([50,10],1,400,300)'), [0, 0])  # whole map in view: centred
        # Zooming about a point keeps it fixed: point 100 px right of centre at zoom 1 -> 2.
        self.assertEqual(blueprint('zoomAt([0,0],1,2,[100,0])'), {'zoom': 2, 'pan': [-100, 0]})
        self.assertEqual(blueprint('zoomAt([0,0],8,16,[100,0])'), {'zoom': 8, 'pan': [0, 0]})

    def test_view_box_ratio_and_scale_bar(self):
        self.assertEqual(blueprint('viewBoxRatio(\'<svg viewBox="0 0 600 300"/>\')'), 2)
        self.assertEqual(blueprint('viewBoxRatio(\'<svg width="300" height="600"/>\')'), 0.5)
        self.assertEqual(blueprint('viewBoxRatio("<svg/>", 1.25)'), 1.25)
        self.assertEqual(blueprint('scaleBar(12)'), {'meters': 10, 'pixels': 120})
        self.assertEqual(blueprint('scaleBar(1.1).meters'), 100)
        self.assertEqual(blueprint('scaleBar(50).meters'), 2)
        self.assertEqual(blueprint('[meters(10),meters(0.5)]'), ['10 m', '50 cm'])


class Pocket(unittest.TestCase):
    STATE = ('{surfaces:[{id:"a",kind:"window",title:"A",logicalSize:[800,600],focused:true},'
             '{id:"w",kind:"workspace",title:"W",logicalSize:[1,1],focused:false},'
             '{id:"b",kind:"window",title:"B",logicalSize:[640,480],focused:false}],'
             'editor:{unplaced:{count:2,selectedId:null,preview:false,windows:['
             '{surfaceId:"b",title:"B",appClass:"foot",logicalSize:[640,480]},'
             '{surfaceId:"c",title:"C",appClass:"mpv",logicalSize:[320,200]}]}}}')

    def test_membership(self):
        self.assertEqual(model('pocketIds(%s)' % self.STATE), ['b', 'c'])
        self.assertEqual(model('[pocketIds(null),pocketIds({}),pocketIds({editor:{}})]'), [[], [], []])

    def test_pocketed_windows_come_first_and_keep_a_card(self):
        cards = model('surfaceCards(%s)' % self.STATE)
        self.assertEqual([c['id'] for c in cards['pocketed']], ['b', 'c'])
        self.assertEqual([c['id'] for c in cards['placed']], ['a'])  # workspaces are not surfaces cards
        self.assertTrue(all(c['pocketed'] for c in cards['pocketed']))
        self.assertFalse(cards['placed'][0]['pocketed'])
        self.assertEqual(cards['pocketed'][1], {'id': 'c', 'kind': 'window', 'title': 'C', 'logicalSize': [320, 200],
                                                'focused': False, 'pocketed': True, 'appClass': 'mpv'})
        self.assertEqual(model('surfaceCards(null)'), {'pocketed': [], 'placed': []})

    def test_results_and_errors(self):
        self.assertEqual(model('pocketResult("surface.unpocket",{revision:3,placed:false})')['text'],
                         'No free spot here — aim and click to place it (Placement tool selected)')
        self.assertEqual(model('pocketResult("surface.unpocket",{revision:3,placed:true}).level'), 'info')
        self.assertEqual(model('pocketResult("surface.pocket",{revision:3}).level'), 'info')
        self.assertIsNone(model('pocketResult("surface.focus",{})'))
        self.assertEqual(model('pocketError("surface.unpocket","-32004: window is not in the pocket")'), 'That window is not in the pocket.')
        self.assertEqual(model('pocketError("surface.pocket","-32005: window is locked")'), "This window can't go in the pocket (window is locked).")
        self.assertEqual(model('pocketError("surface.pocket","-32005: exploration inactive")'), 'Enter the world first.')
        self.assertEqual(model('pocketError("surface.pocket","-32003: unknown window")'), 'That window is gone.')
        self.assertEqual(model('pocketError("surface.pocket","Unknown shell action")'), 'Unknown shell action')


class Movement(unittest.TestCase):
    def test_segment_follows_core(self):
        cases = {'{movement:{modeId:"com.hyprune.walk",state:"grounded"}}': 'walk',
                 '{movement:{modeId:"com.hyprune.fly"}}': 'fly',
                 '{movement:{modeId:"com.hyprune.walk",state:"climbing"}}': 'climb',
                 '{movement:{modeId:"com.example.glide"}}': '', 'null': ''}
        for state, want in cases.items():
            self.assertEqual(model('movementSegment(%s)' % state), want, state)
        self.assertEqual(model('[modeFor("walk"),modeFor("fly"),modeFor("climb")]'), ['com.hyprune.walk', 'com.hyprune.fly', ''])

    def test_movement_set_payloads_validate(self):
        for mode in model('[modeFor("walk"),modeFor("fly")]'):
            frame(request('movement.set', {'modeId': mode}), VALIDATORS['0.20'])


if __name__ == '__main__':
    unittest.main()
