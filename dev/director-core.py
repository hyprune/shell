#!/usr/bin/env python3
"""Real IPC 0.20 Director check and captures (core's verified nested lifetime).
Run from anywhere: flock /tmp/worldshell-nested.lock python3 dev/director-core.py
HYPRUNE_CORE_DIR selects the core checkout (needs IPC 0.20). HYPRUNE_M2_PACKAGE may name a
package carrying com.hyprune.blueprint (its world id must differ from the bundled worlds,
which the harness installs after it). No owner-session control.

Help: Walk / Fly pressed in the Director change core's movement mode both ways.
Surfaces: Put in pocket / Take out / place through the shell (bridge allow-list, core,
result feedback), including placed:false while looking at the floor.
Map: the package's blueprint levels, auto-follow by feet height, manual pick, zoom and pan.
Stills go to the gallery's screenshots/director-<date>/ (dot-temp name, then rename).
"""
import argparse, datetime, json, os, pathlib, re, shutil, subprocess, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); import devenv  # noqa: E402
ROOT = pathlib.Path(__file__).resolve().parent.parent
CORE = pathlib.Path(os.environ.get('HYPRUNE_CORE_DIR', str(ROOT.parent / 'core')))
sys.path.insert(0, str(CORE / 'dev/nested'))
import session as s  # noqa: E402
import m3b  # noqa: E402
from ctl import verified  # noqa: E402
from m2 import wait, keys  # noqa: E402
SHOTS = devenv.gallery_dir('screenshots/director-' + datetime.date.today().isoformat())
STAGE = ROOT / 'dev/.run/director-core'
PACKAGE = os.environ.get('HYPRUNE_M2_PACKAGE')


def acceptance(client, children, args, shell_token, socketpath):
    assert client.hello['protocol'] == '0.20' and {'surface.pocket', 'surface.unpocket'} <= set(client.hello['methods']), client.hello
    world = json.loads((pathlib.Path(PACKAGE) / 'world.json').read_text()) if PACKAGE else None
    client.call('world.load', {'worldId': world['id'] if world else 'com.hyprune.lumen-reach'})
    sub = client.call('state.subscribe', {'topics': ['state']})['subscriptionId']
    def state(): return client.call('state.snapshot', {'subscriptionId': sub})['snapshot']['state']
    s.ctl('eval', 'hl.plugin.hyprune.toggle("HEADLESS-1")'); wait(lambda: s.camera()['active'])
    r, w = os.pipe(); os.write(w, (shell_token + '\n').encode()); os.close(w)
    _, env = verified()
    env.update(HYPRUNE_TOKEN_FD=str(r), HYPRUNE_PROTOCOL='0.20', HYPRUNE_SOCKET=str(socketpath), HYPRUNE_OUTPUT_SCREEN='HEADLESS-1', HYPRUNE_DEV_AUTOMATION='1')
    log = open(s.STATE / 'shell.log', 'w')
    shell = subprocess.Popen(['python3', str(ROOT / 'bridge/launch.py'), '--protocol', '0.20'], env=env, pass_fds=(r,), stdout=log, stderr=subprocess.STDOUT)
    os.close(r); children.append(shell)

    def child():
        assert shell.poll() is None, 'shell exited; see shell.log'
        return next((int(p) for p in pathlib.Path(f'/proc/{shell.pid}/task/{shell.pid}/children').read_text().split()
                     if pathlib.Path(f'/proc/{p}/comm').read_text().strip() in ['qs', 'quickshell']), None)
    qpid = wait(child)

    def ui(*a):
        verified(); return subprocess.check_output([str(s.HERE / 'ctl.py'), 'env', 'qs', 'ipc', '--pid', str(qpid), 'call', 'preview', *map(str, a)], text=True).strip()

    def status():
        try: return json.loads(ui('status'))
        except (subprocess.CalledProcessError, json.JSONDecodeError): return {}
    taken = []

    def shot(name):
        time.sleep(.8)
        audit = json.loads(ui('layoutAudit'))
        assert audit['labels'] > 0 and not audit['failures'], (name, audit)
        subprocess.run([str(s.HERE / 'ctl.py'), 'shot', str(STAGE / (name + '.png'))], check=True); taken.append(name)
    wait(lambda: status().get('lease'))
    assert status()['protocol'] == '0.20', status().get('protocol')
    for title in ['Notes · field journal', 'Music · ambient']:
        children.append(s.envrun('kitty', '--title', title, 'bash', '--noprofile', '--norc', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    wait(lambda: len([c for c in s.camera()['captures'] if c['title'] in ['Notes · field journal', 'Music · ambient'] and c['visible']]) == 2, 20)
    ids = {c['title']: c['id'] for c in s.camera()['captures'] if c['title'] in ['Notes · field journal', 'Music · ambient']}
    pocketed = lambda: [w['surfaceId'] for w in state()['editor']['unplaced']['windows']]

    def park(): s.ctl('eval', 'hl.dispatch(hl.dsp.cursor.move({x=4,y=4}))')  # keep the software cursor out of stills

    def director():
        keys('-P', 'Tab', '-s', '1150', '-p', 'Tab'); wait(lambda: status().get('director'))
    director(); park()

    # Help: the segmented control drives core's movement mode; core's mode drives the control.
    ui('tab', 4)
    client.call('movement.set', {'modeId': 'com.hyprune.walk'}); wait(lambda: state()['movement']['modeId'] == 'com.hyprune.walk')
    shot('core-help-walk')
    assert ui('press', 'segment:fly') == 'true'; wait(lambda: state()['movement']['modeId'] == 'com.hyprune.fly')
    shot('core-help-fly')
    assert ui('press', 'segment:walk') == 'true'; wait(lambda: state()['movement']['modeId'] == 'com.hyprune.walk')
    assert ui('press', 'segment:fly') == 'true'; wait(lambda: state()['movement']['modeId'] == 'com.hyprune.fly')

    # Surfaces: pocket one window through the shell, then take it out where no spot fits.
    ui('tab', 2); ui('scrollPage', 0)
    notes, music = ids['Notes · field journal'], ids['Music · ambient']
    shot('core-surfaces-before')
    assert ui('press', 'pocketButton:' + music) == 'true'; wait(lambda: music in pocketed(), 5)
    wait(lambda: (status().get('surfaceFeedback') or {}).get('surfaceId') == music)
    ui('scrollPage', 0); shot('core-surfaces-pocketed')
    s.ctl('eval', 'hl.plugin.hyprune.camera(-8, 1.7, 12, 0, -1.55)'); time.sleep(.6)  # look at the floor: no free spot
    assert ui('press', 'unpocketButton:' + music) == 'true'
    wait(lambda: (status().get('surfaceFeedback') or {}).get('text', '').startswith('No free spot'), 5)
    assert music in pocketed() and state()['editor']['tool'] == 5
    ui('scrollPage', 0); shot('core-surfaces-unpocket-no-spot')
    s.ctl('eval', 'hl.plugin.hyprune.camera(-8, 1.7, 12, 0, 0)'); time.sleep(.6)
    assert ui('press', 'unpocketButton:' + music) == 'true'; wait(lambda: music not in pocketed(), 5)
    wait(lambda: (status().get('surfaceFeedback') or {}).get('text') == 'Placed in front of you.')
    shot('core-surfaces-placed-again')

    # Map: blueprint levels from the package; auto follows the feet, manual pick, zoom and pan.
    ui('tab', 0)
    levels = (state()['spatial']['map'] or {}).get('levels') or []
    if levels:
        t = state()['spatial']['map']['worldToMap']
        vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', levels[0]['svg']).group(1).split()]
        for i, level in enumerate(levels):
            # Fly over the first floor point of this level at a feet height inside its band.
            m = re.search(r'class="floor"[^>]*? d="M([-\d.]+)[ ,]([-\d.]+)', level['svg'])
            u, v = (float(m.group(1)) - vb[0]) / vb[2], (float(m.group(2)) - vb[1]) / vb[3]
            x, z = (u - t[4]) / t[0], (v - t[5]) / t[3]
            feet = (level['minY'] + min(level['maxY'], level['minY'] + 6)) / 2
            s.ctl('eval', f'hl.plugin.hyprune.camera({x + 4},{feet + 1.7},{z + 4},0.6,0)'); time.sleep(1)
            view = json.loads(ui('mapView', 1, 0, 0, 'auto'))
            assert view['level'] == level['id'] and view['themed'], (level['id'], view)
            shot(f'core-map-{i}-{level["id"]}-auto')
        view = json.loads(ui('mapView', 1, 0, 0, levels[0]['id'])); assert view['picked'] == levels[0]['id']
        shot(f'core-map-{levels[0]["id"]}-picked')
        # Centre on the player (on the top level) and zoom in with the map's own buttons.
        view = json.loads(ui('mapView', 1, 0, 0, levels[-1]['id']))
        assert ui('press', 'mapCentre') == 'true' and ui('press', 'mapZoomIn') == 'true'
        shot(f'core-map-{levels[-1]["id"]}-zoomed-centred')
        view = json.loads(ui('mapView', 4, -150, 120, levels[-1]['id'])); assert view['zoom'] == 4, view
        shot(f'core-map-{levels[-1]["id"]}-zoomed-panned')
        json.loads(ui('mapView', 1, 0, 0, 'auto'))
        ui('theme', 'true'); time.sleep(.4); shot('core-map-auto-paper'); ui('theme', 'false')
    else:
        shot('core-map-overview')
    keys('-k', 'Escape')
    errors = (s.STATE / 'shell.log').read_text()
    assert not any(x in errors for x in ['ReferenceError', 'TypeError', 'Binding loop', 'Unable to assign', 'Unknown shell action']), errors[-3000:]
    for name in taken:
        temp = SHOTS / ('.' + name + '.png.tmp')
        shutil.copyfile(STAGE / (name + '.png'), temp); os.replace(temp, SHOTS / (name + '.png'))
    client.call('runtime.exit', {})
    print('PASS shell 0.20 Director on real core:', ', '.join(taken), '->', SHOTS, flush=True)


if __name__ == '__main__':
    shutil.rmtree(STAGE, ignore_errors=True); STAGE.mkdir(parents=True)
    os.environ['HYPRUNE_NESTED_PROTOCOL'] = '0.20'
    fixture = s.STATE_ROOT / '.m3b-state'; fixture.mkdir(exist_ok=True)
    for name in ['input.json', 'layout.json', 'editor.json', 'graphics.json']: (fixture / name).unlink(missing_ok=True)
    m3b.acceptance = acceptance
    s.run(argparse.Namespace(m3b=True, m3a=False, m2=False, m1=False, integration=False, live=False, serve=False, record=False, visible=False))
