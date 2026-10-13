#!/usr/bin/env python3
"""IPC 0.23 (RFC-0011 P2) captures: spawning a character from Director > Objects (route step,
settings, stops on a user route), the Characters view (motion, disable, rebind, remove), the
drawing bar and HUD hint, the aimed prompt (and its note when posed still), the say caption, the choice list, panel /
waypoint / guide interactions and character refusals.

Launched only by dev/run's validated nested lifetime: dev/run npcs
The SDK mock speaks IPC 0.2, so 0.23 state (objects.instances with characters, npcs, editor
paths), paths.list and results come from the dev-only statePreview / objectPreview /
pathPreview / objectResult / npcChoice hooks (ShellState.dev); preview-only actions are
recorded, never sent. Stills go to HYPRUNE_NPCS_SHOTS (default /tmp/hyprune-npcs-shots).
"""
import json
import os
import pathlib
import shutil
import subprocess
import time
ROOT = pathlib.Path(__file__).resolve().parent.parent
session = json.loads((ROOT / 'dev/.run/session.json').read_text())
# dev/run already refused the parent session; confirm we still target its nested one.
assert session['WAYLAND_DISPLAY'] == os.environ['WAYLAND_DISPLAY']
assert session['HYPRLAND_INSTANCE_SIGNATURE'] == os.environ['HYPRLAND_INSTANCE_SIGNATURE']
pid = os.environ['HYPRUNE_SHELL_PID']
SHOTS = pathlib.Path(os.environ.get('HYPRUNE_NPCS_SHOTS', '/tmp/hyprune-npcs-shots'))
shutil.rmtree(SHOTS, ignore_errors=True); SHOTS.mkdir(parents=True)
OUTPUT = os.environ.get('HYPRUNE_PREVIEW_OUTPUT', 'HYPRUNE-PREVIEW')
METHODS = ','.join(['objects.catalog', 'objects.pocket', 'objects.place', 'objects.transform', 'objects.remove', 'objects.hide',
                    'objects.reset', 'objects.configure', 'libraries.list', 'npcs.spawn', 'npcs.bind', 'npcs.disable', 'npcs.remove',
                    'paths.list', 'paths.set', 'paths.remove', 'paths.draw', 'paths.finish', 'interaction.choose', 'graphics.set'])


def call(*args): return subprocess.check_output(args, text=True).strip()
def ui(*args): return call('qs', 'ipc', '--pid', pid, 'call', 'preview', *map(str, args))
def ctl(code): return call('hyprctl', '-i', session['HYPRLAND_INSTANCE_SIGNATURE'], 'eval', code)
def status(): return json.loads(ui('status'))
def npcs(): return status()['npcs']
def actions(method): return [a['params'] for a in status()['previewActions'] if a['method'] == method]


def wait(predicate, timeout=5):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate(): return
        time.sleep(.1)
    s = status()
    raise AssertionError('timed out; npcs status: ' + json.dumps(s['npcs']) + ' actions: ' + json.dumps(s['previewActions'][-4:]))


taken = []


def shot(name):
    time.sleep(.7)
    for _ in range(20):
        audit = json.loads(ui('layoutAudit'))
        if audit['labels'] > 0 and not audit['failures']: break
        time.sleep(.2)
    else:
        call('grim', '-o', OUTPUT, str(SHOTS / ('FAILED-' + name + '.png')))
    assert audit['labels'] > 0 and not audit['failures'], (name, audit)
    call('grim', '-o', OUTPUT, str(SHOTS / (name + '.png')))
    taken.append(name)


GUIDE, RESIDENT = 'user/guide', 'library/com.hyprune.starter@0.1.0/resident-blue'


def entry(ref, source, name, category, traits, **over):
    return {'ref': ref, 'source': source, 'id': ref.split('/')[-1], 'version': '0.1.0' if source == 'library' else None,
            'formatVersion': '0.10', 'name': name, 'description': None, 'category': category, 'tags': [], 'traits': traits,
            'surfaces': ['floor'], 'scale': [1, 1], 'bounds': {'min': [-0.3, 0, -0.2], 'max': [0.3, 1.8, 0.2]}, 'triangles': 12000,
            'gpuBytes': 1440000, 'collisionTriangles': 0, 'thumbnail': None, 'license': 'CC0-1.0',
            'library': 'com.hyprune.starter@0.1.0' if source == 'library' else None, 'versions': [], 'state': 'ready',
            'placeable': False, 'reason': 'character: use npcs.spawn', 'errors': [], **over}


CATALOG = [
    entry(GUIDE, 'user', 'Guide', 'characters', ['character']),
    entry(RESIDENT, 'library', 'Resident (blue)', 'characters', ['character']),
    entry('user/broken-walker', 'user', 'Broken walker', 'characters', ['character'], state='invalid', errors=['no walk clip in scene.glb']),
    entry('package/reading-desk', 'package', 'Reading desk', 'furniture', ['decorative', 'collidable', 'movable'], placeable=True, reason=None,
          bounds={'min': [-0.8, 0, -0.4], 'max': [0.8, 0.76, 0.4]}, triangles=2310),
]


def pt(x, z, kind='line'): return {'position': [x, 0, z], 'type': kind}


def path(id, source='package', use='route', walkable=True, **over):
    return {'ref': source + '/' + id, 'source': source, 'id': id, 'name': None, 'use': use, 'closed': False,
            'points': [pt(0, 0), pt(4, 0, 'curve'), pt(6, 3, 'curve'), pt(4, 6)], 'speed': None, 'stops': [],
            'walkable': walkable if use == 'route' else None, 'problems': [], 'bound': [], **over}


PATHS = [
    path('plaza-loop', name='Plaza loop', closed=True, bound=['ada']),
    path('market-stroll', name='Market stroll', bound=['bo', 'cy']),
    path('bridge-walk', name='Over the bridge', walkable=False, problems=['no floor under (4.0, 0.0, 2.5)', 'capsule hits a wall at (4.0, 0.0, 3.0)']),
    path('path-1', source='user', name='Desk round', stops=[{'point': 1, 'seconds': 5, 'clip': 'wave'}, {'point': 3, 'seconds': 12, 'seat': 'bench-1'}],
         bound=['u-npc001']),
    path('path-2', source='user', points=[pt(0, 0), pt(1, 1)]),
    path('rail', use='track'),
]


def pose(x, z): return {'position': [x, 0, z], 'rotation': [0, 0.258819, 0, 0.965926]}


def instance(id, source, ref, name, x, z, **over):
    return {'id': id, 'source': source, 'ref': ref, 'name': name, 'areaId': 'plaza', 'pose': pose(x, z), 'scale': 1, 'state': 'active',
            'movable': False, 'locked': False, 'rule': None, 'path': None, 'activity': None, 'seat': None, 'character': False, 'accent': None, **over}


INSTANCES = [
    instance('reading-desk', 'authored', 'package/reading-desk', 'Reading desk', 2, -3, movable=True),
    instance('ada', 'authored', RESIDENT, 'Ada', 0, 0, character=True, path='package/plaza-loop', activity='walking'),
    instance('bo', 'authored', RESIDENT, 'Bo', 3, 1, character=True, path='package/market-stroll', activity='stopped', accent=[0.6939, 0.0953, 0.0437]),
    instance('cy', 'authored', RESIDENT, 'Cy', 5, 2, character=True, path='package/market-stroll', state='hidden'),
    instance('dee', 'authored', RESIDENT, 'Dee', 1, 5, character=True, seat='bench-1', activity='sitting'),
    instance('u-npc001', 'user', GUIDE, 'Guide', -2, 3, character=True, path='user/path-1', activity='walking', accent=[0.0452, 0.2664, 0.5029]),
    instance('u-npc002', 'user', GUIDE, 'Guide', -4, 1, character=True, path='package/bridge-walk', state='suspended', activity='suspended'),
]
USAGE = {'placements': 2, 'assets': 2, 'triangles': 26310, 'gpuBytes': 3145728, 'collisionTriangles': 12}
LIMITS = {'placements': 128, 'assets': 32, 'triangles': 400000, 'gpuBytes': 201326592, 'collisionTriangles': 10000}
NPCS = {'motion': 'auto', 'state': 'animating', 'reason': None, 'usage': {'authored': 4, 'user': 2}, 'limits': {'authored': 16, 'user': 8},
        'drawing': None, 'aimed': None, 'interaction': None}
AIMED = {'objectId': 'ada', 'name': 'Ada', 'prompt': 'Talk', 'interactions': [{'id': 'hello', 'label': 'Talk', 'type': 'say'}]}
SEVERAL = {**AIMED, 'interactions': AIMED['interactions'] + [{'id': 'map', 'label': 'Show me the map', 'type': 'panel'},
                                                             {'id': 'follow', 'label': 'Walk with me', 'type': 'guide'}]}
SAY = {'objectId': 'ada', 'interactionId': 'hello', 'type': 'say', 'label': 'Talk', 'choices': [],
       'line': 'The tram leaves from the east platform. Mind the rails when you cross the plaza.', 'lineIndex': 0, 'lineCount': 3, 'panel': None}
CHOOSE = {'objectId': 'ada', 'interactionId': None, 'type': 'choose', 'label': 'Ada', 'line': None, 'lineIndex': 0, 'lineCount': 0, 'panel': None,
          'choices': [{'id': 'hello', 'label': 'Talk'}, {'id': 'map', 'label': 'Show me the map'}, {'id': 'follow', 'label': 'Walk with me'}]}


def editor():
    return {'mode': 'world', 'tool': 3, 'submode': 'open curve', 'selectedId': None, 'selectedKind': '', 'objects': [], 'locked': [],
            'debug': False, 'carryFacing': None, 'contentScale': None,
            'paths': [{'id': p['id'], 'worldId': 'w', 'areaId': 'plaza', 'closed': p['closed'], 'points': p['points'], 'use': p['use'],
                       'name': p['name'], 'speed': p['speed'], 'stops': p['stops']} for p in PATHS if p['source'] == 'user'],
            'unplaced': {'count': 0, 'windows': [], 'selectedId': None, 'preview': False, 'objects': []},
            'gizmo': {'space': 'world', 'pivot': 'base', 'snap': True}}


def preview(npcs_patch=None, extra=None):
    patch = {'objects': {'catalogRevision': 3, 'instances': INSTANCES, 'pocket': [], 'usage': USAGE, 'limits': LIMITS},
             'npcs': {**NPCS, **(npcs_patch or {})}}
    patch.update(extra or {})
    ui('statePreview', json.dumps(patch), METHODS); time.sleep(.4)


def open_objects(view='catalog'):
    ui('close'); time.sleep(.4)
    ui('open'); time.sleep(.8)
    assert status()['director']
    ui('tabNamed', 'objects'); ui('objectsView', view)
    wait(lambda: status()['tabName'] == 'objects')


time.sleep(2)
assert status()['lease']
ctl('hl.dispatch(hl.dsp.cursor.move({x=40,y=40}))')  # park the nested software cursor
preview()
ui('objectPreview', json.dumps({'catalog': {'revision': 3, 'entries': CATALOG}, 'libraries': []}))
ui('pathPreview', json.dumps({'paths': PATHS}))  # an object: qs ipc would split a top-level [list]
wait(lambda: npcs()['paths'] == len(PATHS))
sizes = [(1920, 1080, 1, ''), (1280, 720, 1, '-720p'), (2560, 1440, 2, '-1440p-s2'), (3840, 2160, 1, '-4k')]
for w, h, scale, suffix in sizes:
    ctl(f'hl.monitor({{output="{OUTPUT}",mode="{w}x{h}@60",position="{"1280x0" if OUTPUT == "HYPRUNE-PREVIEW" else "0x0"}",scale={scale}}})')
    time.sleep(1.2)
    open_objects('catalog')
    wait(lambda: status()['objects']['catalog'] == len(CATALOG))
    shot('catalog-characters' + suffix)
    assert ui('press', 'objectSpawn:' + GUIDE) == 'true'
    wait(lambda: npcs()['spawnRef'] == GUIDE)
    shot('spawn-routes' + suffix)
    ui('objectsView', 'characters'); ui('npcSelect', 'u-npc001'); ui('npcSpawn', '')
    wait(lambda: npcs()['spawnRef'] == '')
    shot('characters' + suffix)
    if suffix:
        ui('close'); time.sleep(.4)
        preview({'interaction': SAY}); wait(lambda: npcs()['line'] == SAY['line'])
        shot('hud-say' + suffix)
        preview({'aimed': SEVERAL}); wait(lambda: npcs()['prompt'] == 'Talk to Ada')
        shot('hud-aimed' + suffix)
        preview()
        continue

    # ---- Spawn: the route column, settings, Stand here and Draw a new route ----
    ui('objectsView', 'catalog'); time.sleep(.3)
    assert ui('press', 'objectSpawn:user/broken-walker') == 'false'  # invalid: can't spawn
    assert ui('press', 'objectSpawn:' + GUIDE) == 'true'
    wait(lambda: npcs()['rows'] == ['stand', 'package/plaza-loop', 'package/market-stroll', 'package/bridge-walk', 'user/path-1', 'user/path-2', 'draw'])
    assert npcs()['cursor'] == 1 and npcs()['ready']
    assert ui('npcRoute', 3) == 'true'; wait(lambda: npcs()['ready'] is False)  # not walkable: disabled with core's problem
    shot('spawn-unwalkable')
    assert ui('press', 'npc-spawn-confirm') == 'false'
    assert ui('npcRoute', 1) == 'true'
    assert ui('npcSettings', json.dumps({'speed': 1.5, 'phase': 0.25, 'reverse': True, 'accent': '#3c8dbc'})) == 'true'
    shot('spawn-settings')
    assert ui('press', 'npc-spawn-confirm') == 'true'
    wait(lambda: actions('npcs.spawn'))
    assert actions('npcs.spawn')[-1] == {'ref': GUIDE, 'path': 'package/plaza-loop', 'speed': 1.5, 'accent': [0.0452, 0.2664, 0.5029],
                                         'phase': 0.25, 'reverse': True}, actions('npcs.spawn')
    wait(lambda: npcs()['spawnRef'] == '' and status()['objects']['view'] == 'characters' and npcs()['selected'] == 'u-npc001')
    # Stand here, by keyboard: Up to the first row, Enter.
    ui('objectsView', 'catalog'); time.sleep(.3)
    ui('npcSpawn', GUIDE); wait(lambda: npcs()['cursor'] == 1)
    call('wtype', '-k', 'Up'); wait(lambda: npcs()['cursor'] == 0)
    call('wtype', '-k', 'Return'); wait(lambda: len(actions('npcs.spawn')) == 2)
    assert actions('npcs.spawn')[-1] == {'ref': GUIDE}, actions('npcs.spawn')
    # Stops on a user route, saved with paths.set.
    ui('npcSpawn', RESIDENT); wait(lambda: npcs()['spawnRef'] == RESIDENT)
    assert ui('npcRoute', 4) == 'true'; wait(lambda: len(npcs()['stops']) == 2)
    assert ui('press', 'npc-stop-add') == 'true'; wait(lambda: len(npcs()['stops']) == 3)
    shot('spawn-stops')
    assert ui('press', 'npc-stops-save') == 'true'; wait(lambda: actions('paths.set'))
    saved = actions('paths.set')[-1]['path']
    assert saved['id'] == 'path-1' and [s['point'] for s in saved['stops']] == [0, 1, 3], saved
    assert saved['stops'][1] == {'point': 1, 'seconds': 5, 'clip': 'wave'} and saved['stops'][2] == {'point': 3, 'seconds': 12, 'seat': 'bench-1'}, saved
    # Draw a new route: paths.draw with the spawn, then the Director closes for tool 3.
    assert ui('npcRoute', 6) == 'true'; time.sleep(.2)
    assert ui('press', 'npc-spawn-confirm') == 'true'
    wait(lambda: actions('paths.draw'))
    assert actions('paths.draw')[-1] == {'use': 'route', 'spawn': {'ref': RESIDENT}}, actions('paths.draw')
    wait(lambda: not status()['director'])
    preview({'drawing': {'pathId': 'path-9', 'use': 'route', 'spawn': {'ref': RESIDENT}, 'bind': None}}, {'editor': editor()})
    wait(lambda: npcs()['drawingText'])
    shot('hud-drawing')
    open_objects('catalog')
    shot('drawing-bar')
    assert ui('press', 'npc-draw-done') == 'true'; wait(lambda: actions('paths.finish') == [{}])
    assert ui('press', 'npc-draw-cancel') == 'true'; wait(lambda: actions('paths.remove') == [{'id': 'path-9'}])
    preview()

    # ---- Characters: disable / enable, rebind, remove, motion ----
    ui('objectsView', 'characters'); ui('npcSelect', 'ada'); time.sleep(.3)
    assert ui('press', 'npc-disable') == 'true'
    assert actions('npcs.disable')[-1] == {'id': 'ada', 'disabled': True}
    assert ui('press', 'npc-remove') == 'false'  # authored: no Remove
    shot('characters-authored')
    ui('npcSelect', 'cy'); time.sleep(.3)
    assert ui('press', 'npc-disable') == 'true'
    assert actions('npcs.disable')[-1] == {'id': 'cy', 'disabled': False}
    ui('npcSelect', 'u-npc002'); time.sleep(.3)
    shot('characters-suspended')
    assert ui('press', 'npc-rebind') == 'true'
    wait(lambda: npcs()['rebindId'] == 'u-npc002' and npcs()['rows'][0] == 'package/plaza-loop')
    shot('rebind-routes')
    assert ui('npcRoute', 3) == 'true'; time.sleep(.2)
    assert ui('press', 'npc-spawn-confirm') == 'true'
    wait(lambda: actions('npcs.bind'))
    assert actions('npcs.bind')[-1] == {'id': 'u-npc002', 'path': 'user/path-1'}, actions('npcs.bind')
    wait(lambda: npcs()['rebindId'] == '')
    ui('npcSelect', 'u-npc001'); time.sleep(.3)
    assert ui('focusNamed', 'npcList') == 'true'
    call('wtype', '-k', 'Delete'); wait(lambda: actions('npcs.remove'))
    assert actions('npcs.remove')[-1] == {'id': 'u-npc001'}
    assert ui('press', 'npcs-remove-all') == 'true' and ui('press', 'npcs-remove-all') == 'true'
    assert actions('npcs.remove')[-1] == {'all': True}
    assert ui('press', 'segment:still') == 'true'
    assert actions('graphics.set')[-1] == {'patch': {'npc_motion': 'still'}}, actions('graphics.set')
    preview({'state': 'paused', 'reason': 'usb-c power'})
    shot('characters-paused')
    ui('theme', 'true'); shot('characters-paper'); ui('theme', 'false')
    # A refusal: core's words (walkability) on the page and as a toast.
    ui('objectResult', 'npcs.bind', json.dumps({'id': 'u-npc002', 'path': 'package/bridge-walk'}),
       json.dumps({'code': -32007, 'message': 'route bridge-walk: no floor under (4.0, 0.0, 2.5)', 'rule': 'walkable'}))
    wait(lambda: 'no floor' in (status()['objects']['feedback'] or {}).get('text', ''))
    shot('characters-refusal')
    preview()

    # ---- HUD: aimed prompt, caption, choice list, panel / waypoint / guide ----
    ui('close'); time.sleep(.5)
    preview({'aimed': AIMED})
    wait(lambda: npcs()['prompt'] == 'Talk')
    shot('hud-aimed')
    preview({'aimed': SEVERAL})
    wait(lambda: npcs()['prompt'] == 'Talk to Ada')
    shot('hud-aimed-several')
    # Posed still / reduced motion: the prompt says why and where it is set.
    preview({'aimed': AIMED, 'motion': 'still', 'state': 'still'})
    wait(lambda: npcs()['prompt'] == 'Talk' and npcs()['promptNote'] == 'Posed still · Objects › Characters')
    shot('hud-aimed-still')
    preview({'aimed': SEVERAL, 'state': 'paused', 'reason': 'reduced motion'})
    wait(lambda: npcs()['promptNote'] == 'Reduced motion · Settings')
    shot('hud-aimed-reduced')
    preview({'aimed': AIMED})
    wait(lambda: not npcs()['promptNote'])  # hidden: null
    preview({'interaction': SAY, 'aimed': AIMED})
    wait(lambda: npcs()['line'] == SAY['line'] and npcs()['prompt'] is None)
    shot('hud-say')
    for concept in ['Instrument', 'Minimal']:
        ui('concept', concept); time.sleep(.3); shot('hud-say-' + concept.lower())
    ui('concept', 'Adventure')
    preview({'interaction': {**SAY, 'line': 'See you at the platform.', 'lineIndex': 2}})
    shot('hud-say-last')
    preview({'interaction': CHOOSE})
    ui('npcChoice', json.dumps(CHOOSE))
    wait(lambda: npcs()['choice'] is not None)
    shot('hud-choice')
    call('wtype', '-k', 'Down'); call('wtype', '-k', 'Return')
    wait(lambda: actions('interaction.choose'))
    assert actions('interaction.choose')[-1] == {'objectId': 'ada', 'interactionId': 'map'}, actions('interaction.choose')
    call('wtype', '3'); wait(lambda: actions('interaction.choose')[-1] == {'objectId': 'ada', 'interactionId': 'follow'})
    call('wtype', '-k', 'Escape'); wait(lambda: actions('interaction.choose')[-1] == {'objectId': 'ada', 'interactionId': None})
    ui('npcChoice', ''); wait(lambda: npcs()['choice'] is None)
    preview({'interaction': {**SAY, 'interactionId': 'follow', 'type': 'guide', 'label': 'Walk with me', 'line': None, 'lineCount': 0}})
    wait(lambda: any(t.get('line') == 'Follow Ada' for t in status()['quests']['toasts']))
    wait(lambda: npcs()['toast'] == 'Follow Ada')  # drawn in the HUD toast column
    shot('hud-guide-toast')
    preview({'interaction': {**SAY, 'interactionId': 'desk', 'type': 'waypoint', 'label': 'Where is the desk?', 'line': None, 'lineCount': 0}})
    wait(lambda: any(t.get('line') == 'Waypoint set' for t in status()['quests']['toasts']))
    ui('npcNotice', 'path.unwalkable', 'route path-9: no floor under (1.0, 0.0, 2.0)')
    shot('hud-waypoint-and-notice')
    count = len(actions('interaction.choose'))
    preview({'interaction': {**SAY, 'interactionId': 'map', 'type': 'panel', 'label': 'Show me the map', 'line': None, 'lineCount': 0, 'panel': 'map'}})
    wait(lambda: status()['director'] and status()['tabName'] == 'map')
    wait(lambda: len(actions('interaction.choose')) == count + 1)
    assert actions('interaction.choose')[-1] == {'objectId': 'ada', 'interactionId': None}
    ui('close'); time.sleep(.4)
    preview({'interaction': {**SAY, 'interactionId': 'odd', 'type': 'panel', 'label': 'Odd', 'line': None, 'lineCount': 0, 'panel': 'casino'}})
    wait(lambda: len(actions('interaction.choose')) == count + 2)
    assert not status()['director']  # unknown panel ids just end the interaction
    ui('motion', 'true'); preview({'aimed': AIMED}); shot('hud-aimed-reduced-motion'); ui('motion', 'false')
    preview()

ui('statePreview', '', ''); ui('objectPreview', ''); ui('pathPreview', '')
logs = (ROOT / 'dev/.run/shell.log').read_text()
assert not any(x in logs for x in ['ReferenceError', 'TypeError', 'Binding loop', 'Unable to assign']), logs[-3000:]
print('PASS npcs captures:', ', '.join(taken), '->', SHOTS)
