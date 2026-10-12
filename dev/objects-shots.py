#!/usr/bin/env python3
"""IPC 0.22 (RFC-0011 P1) captures: Director > Objects (Catalog with filters and search, Placed
with the configure panel), object toasts and pocketed objects in the tool 5 HUD.

Launched only by dev/run's validated nested lifetime: dev/run objects
The SDK mock speaks IPC 0.2, so 0.22 state (objects, editor.unplaced.objects), methods and
results come from the dev-only statePreview / objectPreview / objectResult hooks
(ShellState.dev); preview-only actions are recorded, never sent. Thumbnails are generated
under /tmp. Stills go to HYPRUNE_OBJECTS_SHOTS (default /tmp/hyprune-objects-shots).
"""
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import time
ROOT = pathlib.Path(__file__).resolve().parent.parent
session = json.loads((ROOT / 'dev/.run/session.json').read_text())
# dev/run already refused the parent session; confirm we still target its nested one.
assert session['WAYLAND_DISPLAY'] == os.environ['WAYLAND_DISPLAY']
assert session['HYPRLAND_INSTANCE_SIGNATURE'] == os.environ['HYPRLAND_INSTANCE_SIGNATURE']
pid = os.environ['HYPRUNE_SHELL_PID']
SHOTS = pathlib.Path(os.environ.get('HYPRUNE_OBJECTS_SHOTS', '/tmp/hyprune-objects-shots'))
shutil.rmtree(SHOTS, ignore_errors=True); SHOTS.mkdir(parents=True)
THUMBS = pathlib.Path(tempfile.mkdtemp(prefix='hyprune-object-thumbs-'))
OUTPUT = os.environ.get('HYPRUNE_PREVIEW_OUTPUT', 'HYPRUNE-PREVIEW')  # HYPRUNE_DEV_PREVIEW=nested: the nested window
METHODS = ','.join(['objects.catalog', 'objects.pocket', 'objects.place', 'objects.transform', 'objects.remove', 'objects.hide',
                    'objects.reset', 'objects.configure', 'libraries.list', 'libraries.install', 'libraries.remove'])


def call(*args): return subprocess.check_output(args, text=True).strip()
def ui(*args): return call('qs', 'ipc', '--pid', pid, 'call', 'preview', *map(str, args))
def ctl(code): return call('hyprctl', '-i', session['HYPRLAND_INSTANCE_SIGNATURE'], 'eval', code)
def status(): return json.loads(ui('status'))
def objects(): return status()['objects']
def actions(method): return [a['params'] for a in status()['previewActions'] if a['method'] == method]


def wait(predicate, timeout=5):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate(): return
        time.sleep(.1)
    raise AssertionError('timed out')


taken = []


def shot(name):
    time.sleep(.7)
    for _ in range(20):  # a freshly mapped or resized layer settles its geometry first
        audit = json.loads(ui('layoutAudit'))
        if audit['labels'] > 0 and not audit['failures']: break
        time.sleep(.2)
    else:
        call('grim', '-o', OUTPUT, str(SHOTS / ('FAILED-' + name + '.png')))
    assert audit['labels'] > 0 and not audit['failures'], (name, audit)
    call('grim', '-o', OUTPUT, str(SHOTS / (name + '.png')))
    taken.append(name)


def thumbnail(name, colour, shape):
    """A plain generated PNG (no third-party art): a shape on a transparent square."""
    from PIL import Image, ImageDraw
    image = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    if shape == 'box': draw.rectangle((64, 40, 192, 224), fill=colour, outline=(20, 30, 40, 255), width=6)
    elif shape == 'lamp': draw.rectangle((120, 70, 136, 230), fill=(60, 66, 70, 255)); draw.ellipse((88, 24, 168, 104), fill=colour)
    elif shape == 'plant': draw.polygon([(128, 20), (60, 150), (196, 150)], fill=colour); draw.rectangle((96, 150, 160, 230), fill=(150, 90, 60, 255))
    else: draw.rectangle((40, 120, 216, 150), fill=colour); draw.rectangle((50, 150, 66, 230), fill=colour); draw.rectangle((190, 150, 206, 230), fill=colour)
    path = THUMBS / (name + '.png')
    image.save(path)
    return str(path)


RACK = 'library/com.hyprune.starter@0.1.0/server-rack'


def entry(ref, source, name, category, traits, size, triangles, thumb=None, **over):
    return {'ref': ref, 'source': source, 'id': ref.split('/')[-1], 'version': '0.1.0' if source == 'library' else None,
            'formatVersion': '0.10', 'name': name, 'description': None, 'category': category, 'tags': over.pop('tags', []), 'traits': traits,
            'surfaces': ['floor'], 'scale': [0.5, 2], 'bounds': {'min': [-size[0] / 2, 0, -size[2] / 2], 'max': [size[0] / 2, size[1], size[2] / 2]},
            'triangles': triangles, 'gpuBytes': triangles * 120 if triangles else None, 'collisionTriangles': 12, 'thumbnail': thumb, 'license': 'CC0-1.0',
            'library': 'com.hyprune.starter@0.1.0' if source == 'library' else None, 'versions': [], 'state': 'ready', 'placeable': True,
            'reason': None, 'errors': [], **over}


def pose(x, z, yaw_q=(0, 0, 0, 1)): return {'position': [x, 0, z], 'rotation': list(yaw_q)}


def instance(id, source, ref, name, x, z, **over):
    return {'id': id, 'source': source, 'ref': ref, 'name': name, 'areaId': 'arrival', 'pose': pose(x, z, (0, 0.258819, 0, 0.965926)),
            'scale': 1, 'state': 'active', 'movable': True, 'locked': False, 'rule': None, 'path': None, 'activity': None, 'seat': None, **over}


CATALOG = [
    entry('package/reading-desk', 'package', 'Reading desk', 'furniture', ['decorative', 'collidable', 'movable'], (1.6, 0.76, 0.8), 2310,
          thumbnail('desk', (180, 130, 80, 255), 'desk'), tags=['desk', 'table']),
    entry('package/archive-shelf', 'package', 'Archive shelf', 'furniture', [], (2.0, 2.4, 0.5), 5400, None,
          placeable=False, reason='not movable: only objects with the movable trait can be placed'),
    entry(RACK, 'library', 'Server rack', 'machines', ['decorative', 'collidable', 'movable', 'machine'], (1.24, 2.16, 1.3), 4210,
          thumbnail('rack', (70, 90, 110, 255), 'box'), tags=['rack', 'network']),
    entry('library/com.hyprune.starter@0.1.0/floor-lamp', 'library', 'Floor lamp', 'lighting', ['decorative', 'movable'], (0.45, 1.7, 0.45), 960,
          thumbnail('lamp', (250, 220, 140, 255), 'lamp'), tags=['lamp', 'light']),
    entry('library/com.hyprune.starter@0.1.0/bench', 'library', 'Garden bench with an unusually long display name', 'furniture',
          ['decorative', 'collidable', 'movable', 'seat'], (1.8, 0.9, 0.6), 3100, None, tags=['seat', 'outdoor']),
    entry('user/potted-fern', 'user', 'Potted fern', 'plants', ['decorative', 'movable'], (0.5, 1.1, 0.5), 1800,
          thumbnail('fern', (80, 160, 90, 255), 'plant'), tags=['green', 'plant']),
    entry('user/guide', 'user', 'Guide', 'characters', ['character', 'movable'], (0.6, 1.8, 0.4), 12000, None,
          placeable=False, reason='character: user characters arrive with routes (RFC-0011 P2)'),
    entry('user/broken-chair', 'user', 'Broken chair', 'furniture', ['movable'], (0.5, 0.9, 0.5), None, None, state='invalid', placeable=False,
          reason='invalid: model.glb is missing', errors=['model.glb is missing', 'thumbnail.png is not a PNG file'], bounds=None),
]
INSTANCES = [
    instance('reading-desk', 'authored', 'package/reading-desk', 'Reading desk', 2, -3),
    instance('archive-shelf', 'authored', 'package/archive-shelf', 'Archive shelf', -4, -6, movable=False),
    instance('lantern', 'authored', 'package/reading-desk', 'Lantern', 6, 1, state='hidden'),
    instance('u-7c2e91', 'user', RACK, 'Server rack', 3.2, -4.5),
    instance('u-0a1b2c', 'user', 'user/potted-fern', 'Potted fern', 1, 2, locked=True, movable=False),
    instance('u-33aa10', 'user', 'library/com.hyprune.starter@0.1.0/floor-lamp', 'Floor lamp', -1, 4, state='blocked', rule='walls'),
    instance('u-55bb20', 'user', 'library/com.hyprune.starter@0.1.0/bench', 'Garden bench', 0, 7, state='missing'),
]
USAGE = {'placements': 4, 'assets': 4, 'triangles': 10870, 'gpuBytes': 6815744, 'collisionTriangles': 48}
LIMITS = {'placements': 128, 'assets': 32, 'triangles': 400000, 'gpuBytes': 201326592, 'collisionTriangles': 10000}
POCKET = [{'itemId': 'pocket-1', 'ref': RACK, 'name': 'Server rack'}, {'itemId': 'pocket-2', 'ref': 'user/potted-fern', 'name': 'Potted fern'},
          {'itemId': 'pocket-3', 'ref': 'library/com.hyprune.starter@0.1.0/floor-lamp', 'name': 'Floor lamp'}]


def editor(selected='pocket-2', windows=()):
    return {'mode': 'world', 'tool': 5, 'submode': 'placement', 'selectedId': None, 'selectedKind': '', 'paths': [], 'objects': [], 'locked': [],
            'debug': False, 'carryFacing': None, 'contentScale': None,
            'unplaced': {'count': len(windows) + len(POCKET), 'windows': list(windows), 'selectedId': selected, 'preview': True, 'objects': POCKET},
            'gizmo': {'space': 'world', 'pivot': 'base', 'snap': True}}


def preview(extra=None, instances=INSTANCES):
    patch = {'objects': {'catalogRevision': 3, 'instances': instances, 'pocket': POCKET, 'usage': USAGE, 'limits': LIMITS}}
    patch.update(extra or {})
    ui('statePreview', json.dumps(patch), METHODS); time.sleep(.4)


time.sleep(2)
assert status()['lease']
ctl('hl.dispatch(hl.dsp.cursor.move({x=40,y=40}))')  # park the nested software cursor
preview()
ui('objectPreview', json.dumps({'catalog': {'revision': 3, 'entries': CATALOG}, 'libraries': []}))
sizes = [(1920, 1080, 1, ''), (1280, 720, 1, '-720p'), (2560, 1440, 2, '-1440p-s2'), (3840, 2160, 1, '-4k'), (3840, 2160, 2, '-4k-s2')]
for w, h, scale, suffix in sizes:
    ctl(f'hl.monitor({{output="{OUTPUT}",mode="{w}x{h}@60",position="{"1280x0" if OUTPUT == "HYPRUNE-PREVIEW" else "0x0"}",scale={scale}}})')
    time.sleep(1.2)
    ui('close'); time.sleep(.4)
    ui('open'); time.sleep(.8)
    assert status()['director']
    ui('tabNamed', 'objects'); ui('objectsView', 'catalog')
    wait(lambda: status()['tabName'] == 'objects' and objects()['catalog'] == len(CATALOG))
    ui('objectFilter', 'all', '', '')
    shot('catalog' + suffix)
    ui('objectsView', 'placed'); ui('objectSelect', 'u-7c2e91')
    wait(lambda: objects()['sections'] == ['transform', 'lock', 'remove', 'data'])
    shot('placed' + suffix)
    if suffix:
        ui('close'); time.sleep(.4)
        continue

    # Catalog: filters, search, keyboard and Add.
    ui('objectsView', 'catalog'); time.sleep(.3)
    assert ui('objectFilter', 'user', '', '') == 'true'; wait(lambda: objects()['shown'] == 3)
    shot('catalog-mine')
    ui('objectFilter', 'all', 'furniture', ''); wait(lambda: objects()['shown'] == 4)
    ui('objectFilter', 'all', '', 'lamp'); wait(lambda: objects()['shown'] == 1)
    shot('catalog-search-lamp')
    ui('objectFilter', 'all', '', '')
    assert ui('focusNamed', 'objectsCatalog') == 'true'
    call('wtype', '-k', 'Down'); call('wtype', '-k', 'Down'); wait(lambda: objects()['cursor'] == 2)
    call('wtype', '-k', 'Return'); wait(lambda: actions('objects.pocket'))
    assert actions('objects.pocket')[-1] == {'ref': RACK}, actions('objects.pocket')
    wait(lambda: any(t.get('category') == 'objects' for t in status()['quests']['toasts']))
    assert 'pocket' in (objects()['feedback'] or {}).get('text', ''), objects()['feedback']
    shot('catalog-added-feedback')
    assert ui('press', 'objectAdd:user/potted-fern') == 'true'
    assert actions('objects.pocket')[-1] == {'ref': 'user/potted-fern'}
    assert ui('press', 'objectAdd:user/guide') == 'false'  # not placeable: disabled
    call('wtype', '-k', 'Right'); wait(lambda: status()['tabName'] == 'places')  # Left/Right still change views
    call('wtype', '-k', 'Left'); wait(lambda: status()['tabName'] == 'objects')
    ui('theme', 'true'); shot('catalog-paper'); ui('theme', 'false')

    # Placed: configure panel per source, lock, remove/reset, footer confirms.
    ui('objectsView', 'placed'); ui('objectSelect', 'u-7c2e91'); time.sleep(.3)
    assert ui('press', 'object-lock') == 'true'
    assert actions('objects.configure')[-1] == {'id': 'u-7c2e91', 'patch': {'locked': True}}
    assert ui('press', 'object-reset') == 'true'
    assert actions('objects.reset')[-1] == {'id': 'u-7c2e91'}
    assert ui('press', 'object-remove') == 'true'
    assert actions('objects.remove')[-1] == {'id': 'u-7c2e91'}
    wait(lambda: objects()['selected'] == 'reading-desk')  # the removed one's selection moves to the first
    ui('objectSelect', 'u-7c2e91'); time.sleep(.3)
    assert ui('press', 'object-reset') == 'true'
    assert actions('objects.reset')[-1] == {'id': 'u-7c2e91'}
    ui('objectSelect', 'reading-desk'); wait(lambda: objects()['selected'] == 'reading-desk')
    shot('placed-authored')
    assert ui('press', 'object-hide') == 'true'
    assert actions('objects.hide')[-1] == {'id': 'reading-desk', 'hidden': True}
    ui('objectSelect', 'lantern'); time.sleep(.3)
    assert ui('press', 'object-hide') == 'true'
    assert actions('objects.hide')[-1] == {'id': 'lantern', 'hidden': False}
    ui('objectSelect', 'archive-shelf'); time.sleep(.3)
    assert ui('press', 'object-hide') == 'false'  # a fixed authored instance can't be hidden
    shot('placed-authored-fixed')
    ui('objectSelect', 'u-0a1b2c'); time.sleep(.3)
    assert ui('press', 'object-remove') == 'false'  # locked
    shot('placed-locked')
    ui('objectSelect', 'u-33aa10'); time.sleep(.3)
    shot('placed-blocked')
    # Transform: edit X and commit with Enter.
    ui('objectSelect', 'u-7c2e91'); time.sleep(.3)
    assert ui('focusNamed', 'object-x') == 'true'
    call('wtype', '-M', 'ctrl', 'a', '-m', 'ctrl'); call('wtype', '5.5'); call('wtype', '-k', 'Return')
    wait(lambda: actions('objects.transform'))
    moved = actions('objects.transform')[-1]
    assert moved['id'] == 'u-7c2e91' and moved['pose']['position'] == [5.5, 0, -4.5], moved
    # Keyboard: Up/Down select, L locks the selected instance.
    assert ui('focusNamed', 'objectsPlaced') == 'true'
    call('wtype', '-k', 'Down'); wait(lambda: objects()['selected'] == 'u-0a1b2c')
    call('wtype', 'l'); wait(lambda: actions('objects.configure')[-1] == {'id': 'u-0a1b2c', 'patch': {'locked': False}})
    # Footer actions need a second press.
    count = len(actions('objects.remove'))
    assert ui('press', 'objects-remove-all') == 'true'
    assert len(actions('objects.remove')) == count and objects()['confirm'] == 'remove-all'
    shot('placed-confirm-remove-all')
    assert ui('press', 'objects-remove-all') == 'true'
    assert actions('objects.remove')[-1] == {'all': True}
    assert ui('press', 'objects-reset-all') == 'true' and ui('press', 'objects-reset-all') == 'true'
    assert actions('objects.reset')[-1] == {'all': True}
    ui('theme', 'true'); shot('placed-paper'); ui('theme', 'false')
    # A refusal: core's words and the placement rule, on the page and as a toast.
    ui('objectResult', 'objects.transform', json.dumps(moved), json.dumps({'code': -32007, 'message': 'the shape is inside a wall', 'rule': 'walls'}))
    wait(lambda: 'inside a wall' in (objects()['feedback'] or {}).get('text', ''))
    shot('placed-refusal')
    ui('objectsView', 'catalog')
    ui('close'); time.sleep(.5)
    ui('objectResult', 'objects.pocket', json.dumps({'ref': RACK}), json.dumps({'code': -32008, 'message': 'user placements: 128 per world', 'rule': 'budget'}))
    shot('hud-toast-budget')
    time.sleep(4.5)

    # Tool 5 HUD: pocketed objects listed, the selected one highlighted.
    preview({'editor': editor('pocket-2')})
    wait(lambda: status()['objects']['pocket'] and any(p['selected'] for p in status()['objects']['pocket']))
    hud = json.loads(ui('interactionHud'))
    assert hud['hudPocketObjects']['visible'] and hud['hudPlacementTitle']['text'] == 'Potted fern', hud
    shot('hud-tool5-objects')
    preview({'editor': editor('w1', [{'surfaceId': 'w1', 'title': 'Terminal · build log', 'appClass': 'foot', 'logicalSize': [1200, 800]}])})
    shot('hud-tool5-window-and-objects')
    for concept in ['Instrument', 'Minimal']:
        ui('concept', concept); preview({'editor': editor('pocket-3')}); shot('hud-tool5-objects-' + concept.lower())
    ui('concept', 'Adventure')
    preview()

ui('statePreview', '', ''); ui('objectPreview', '')
shutil.rmtree(THUMBS, ignore_errors=True)
logs = (ROOT / 'dev/.run/shell.log').read_text()
assert not any(x in logs for x in ['ReferenceError', 'TypeError', 'Binding loop', 'Unable to assign']), logs[-3000:]
print('PASS objects captures:', ', '.join(taken), '->', SHOTS)
