#!/usr/bin/env python3
"""Director captures for IPC 0.20: Help movement toggle, Surfaces pocket, Map blueprint levels.

Launched only by dev/run's validated nested lifetime: dev/run director
The SDK mock speaks IPC 0.2, so 0.20 fields (movement.state, editor.unplaced, map.levels)
and methods (movement.set, surface.pocket, surface.unpocket) come from the dev-only
`statePreview` hook (ShellState.dev); preview-only actions are recorded, never sent.
Level SVGs: HYPRUNE_BLUEPRINT_DIR (ground.svg/upper.svg) or the dev/blueprint fixtures.
Stills go to dev/.run/director; HYPRUNE_DIRECTOR_PUBLISH=1 also copies them to the
gallery's screenshots/director-<date>/ as mock-*.png (dot-temp name, then rename).
"""
import datetime
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'dev')); import devenv  # noqa: E402
session = json.loads((ROOT / 'dev/.run/session.json').read_text())
# dev/run already refused the parent session; confirm we still target its nested one.
assert session['WAYLAND_DISPLAY'] == os.environ['WAYLAND_DISPLAY']
assert session['HYPRLAND_INSTANCE_SIGNATURE'] == os.environ['HYPRLAND_INSTANCE_SIGNATURE']
pid = os.environ['HYPRUNE_SHELL_PID']
SHOTS = ROOT / 'dev/.run/director'
shutil.rmtree(SHOTS, ignore_errors=True); SHOTS.mkdir(parents=True)
SOURCE = pathlib.Path(os.environ.get('HYPRUNE_BLUEPRINT_DIR', ROOT / 'dev/blueprint'))
METHODS = 'movement.set,surface.pocket,surface.unpocket'


def call(*args): return subprocess.check_output(args, text=True).strip()
def ui(*args): return call('qs', 'ipc', '--pid', pid, 'call', 'preview', *map(str, args))
def ctl(code): return call('hyprctl', '-i', session['HYPRLAND_INSTANCE_SIGNATURE'], 'eval', code)
def status(): return json.loads(ui('status'))
def sha(text): return hashlib.sha256(text.encode()).hexdigest()


def svg(name):
    path = SOURCE / name
    return (path if path.exists() else ROOT / 'dev/blueprint' / name).read_text()


def yaw(degrees):  # map heading, clockwise from north (-Z): a turn of -degrees about +Y
    import math
    half = math.radians(-degrees) / 2
    return [0, math.sin(half), 0, math.cos(half)]


OVERVIEW = svg('overview.svg')
LEVELS = [{'id': 'ground', 'name': 'Ground', 'minY': -2.0, 'maxY': 4.5, 'svg': svg('ground.svg')},
          {'id': 'upper', 'name': 'Upper decks', 'minY': 4.5, 'maxY': 40.0, 'svg': svg('upper.svg')}]
for entry in LEVELS: entry['sha256'] = sha(entry['svg'])
MAP = {'svg': OVERVIEW, 'sha256': sha(OVERVIEW), 'bounds': [-30, -30, 30, 30], 'worldToMap': [1 / 60, 0, 0, 1 / 60, 0.5, 0.5], 'levels': LEVELS}
POCKET = [{'surfaceId': 'surface-music', 'title': 'Music · ambient', 'appClass': 'org.gnome.Lollypop', 'logicalSize': [600, 400]},
          {'surfaceId': 'surface-notes', 'title': 'Notes · field journal', 'appClass': 'org.gnome.TextEditor', 'logicalSize': [900, 700]}]
EDITOR = {'mode': 'world', 'tool': 1, 'submode': 'normal', 'selectedId': None, 'selectedKind': '', 'paths': [], 'objects': [],
          'locked': [], 'debug': False, 'carryFacing': None, 'contentScale': None, 'toolSlots': None,
          'unplaced': {'count': len(POCKET), 'windows': POCKET, 'selectedId': 'surface-music', 'preview': False}}


def preview(mode='com.hyprune.walk', state='grounded', position=(0, 1.7, 4), heading=40, editor=EDITOR, map=MAP):
    patch = {'movement': {'modeId': mode, 'state': state, 'position': list(position), 'orientation': yaw(heading)},
             'editor': editor, 'spatial': {'map': map}}
    ui('statePreview', json.dumps(patch), METHODS); time.sleep(.5)


def shot(name):
    time.sleep(.7)
    audit = json.loads(ui('layoutAudit'))
    assert audit['labels'] > 0 and not audit['failures'], (name, audit)
    call('grim', '-o', 'HYPRUNE-PREVIEW', str(SHOTS / (name + '.png')))
    taken.append(name)


taken = []
time.sleep(2)
assert status()['lease']
ctl('hl.dispatch(hl.dsp.cursor.move({x=40,y=40}))')  # park the nested software cursor
ctl('hl.monitor({output="HYPRUNE-PREVIEW",mode="1920x1080@60",position="1280x0",scale=1})')
time.sleep(1.2)
ui('open'); time.sleep(.8)
assert status()['director']

# Help: Walk / Fly bound to movement.modeId; Climbing shown active, not selectable.
ui('tab', 4)
for name, mode, state in [('help-walk', 'com.hyprune.walk', 'grounded'), ('help-fly', 'com.hyprune.fly', 'flying'),
                          ('help-climbing', 'com.hyprune.walk', 'climbing')]:
    preview(mode, state)
    assert status()['movement']['modeId'] == mode
    shot(name)
# Pressing a segment asks the (mock) core; its answer moves the control.
ui('statePreview', '', ''); time.sleep(.5)
assert ui('press', 'segment:walk') == 'true'; time.sleep(1)
# The SDK mock implements free flight only: the request reaches it and its refusal shows.
assert '"method": "movement.set"' in (ROOT / 'dev/.run/shell.log').read_text()
assert status()['movement']['modeId'] == 'com.hyprune.fly', status()['movement']
shot('help-walk-refused-by-mock')

# Surfaces: two pocketed windows (one only in the pocket list), two placed.
preview()
ui('tab', 2); ui('scrollPage', 0)
shot('surfaces-pocket')
ui('scrollPage', 1); shot('surfaces-placed'); ui('scrollPage', 0)
ui('pocketResult', 'surface-music', 'surface.unpocket', json.dumps({'revision': 9, 'placed': False}))
assert status()['surfaceFeedback']['text'].startswith('No free spot here')
shot('surfaces-unpocket-no-spot')
ui('pocketResult', 'surface-browser', 'surface.pocket', '-32005: window is locked')
shot('surfaces-pocket-refused')
ui('theme', 'true'); shot('surfaces-pocket-paper'); ui('theme', 'false')
preview(editor={**EDITOR, 'unplaced': {'count': 0, 'windows': [], 'selectedId': None, 'preview': False}})
shot('surfaces-none-pocketed')

# Map: auto level follows the feet; manual pick; zoom and pan; Paper theme; no levels.
ui('tab', 0)
preview(position=(0, 1.7, 4), heading=40)
view = json.loads(ui('mapView', 1, 0, 0, 'auto')); assert view['level'] == 'ground' and view['themed'], view
shot('map-ground-auto')
preview(position=(7, 7.7, 3), heading=200)
view = json.loads(ui('mapView', 1, 0, 0, 'auto')); assert view['level'] == 'upper', view
shot('map-upper-auto')
view = json.loads(ui('mapView', 1, 0, 0, 'ground')); assert view['level'] == 'ground' and view['picked'] == 'ground', view
shot('map-ground-picked')
view = json.loads(ui('mapView', 2.5, -260, 180, 'upper')); assert view['zoom'] == 2.5, view
shot('map-upper-zoomed-panned')
json.loads(ui('mapView', 1, 0, 0, 'auto')); assert ui('press', 'mapCentre') == 'true' and ui('press', 'mapZoomIn') == 'true'
shot('map-upper-centred-on-me')
preview(position=(0, 1.7, 4), heading=40)
view = json.loads(ui('mapView', 4, -420, 380, 'auto')); assert view['level'] == 'ground', view
shot('map-ground-zoomed-panned')
ui('theme', 'true'); json.loads(ui('mapView', 1, 0, 0, 'auto')); shot('map-ground-paper'); ui('theme', 'false')
preview(map={k: v for k, v in MAP.items() if k != 'levels'})
view = json.loads(ui('mapView', 1, 0, 0, 'auto')); assert not view['themed'] and view['level'] is None, view
shot('map-overview-no-levels')

# The segmented control sends movement.set (recorded as a preview action, never sent).
ui('statePreview', '', '')
ui('close'); time.sleep(.5)
logs = (ROOT / 'dev/.run/shell.log').read_text()
assert not any(x in logs for x in ['ReferenceError', 'TypeError', 'Binding loop', 'Unable to assign']), logs[-3000:]
if os.environ.get('HYPRUNE_DIRECTOR_PUBLISH') == '1':
    target = devenv.gallery_dir('screenshots/director-' + datetime.date.today().isoformat())
    for name in taken:
        temp = target / ('.mock-' + name + '.png.tmp')  # mock-: SDK mock + preview data, not real core
        shutil.copyfile(SHOTS / (name + '.png'), temp)
        os.replace(temp, target / ('mock-' + name + '.png'))
    print('published ->', target)
print('PASS director captures:', ', '.join(taken), '->', SHOTS)
