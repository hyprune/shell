#!/usr/bin/env python3
"""RFC-0015 phase 1 captures: Director > Library (Browse, Installed, Sources), the install
confirmation with provenance, a source change's second confirmation, progress, a finished
library install refreshing the object catalog, an error with its rule, and the HUD toast.

Launched only by dev/run's validated nested lifetime: dev/run library
The page runs the fake CLI (dev/fake-hyprune-cli.py, state under dev/.run/fake-cli) that
dev/run selects when HYPRUNE_CLI is unset; the SDK mock provides the session, and the
objects methods come from the dev-only statePreview hook so the catalog refresh after a
library install is visible as a recorded preview action. Stills go to HYPRUNE_LIBRARY_SHOTS
(default /tmp/hyprune-library-shots).
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
ROOT = pathlib.Path(__file__).resolve().parent.parent
session = json.loads((ROOT / 'dev/.run/session.json').read_text())
# dev/run already refused the parent session; confirm we still target its nested one.
assert session['WAYLAND_DISPLAY'] == os.environ['WAYLAND_DISPLAY']
assert session['HYPRLAND_INSTANCE_SIGNATURE'] == os.environ['HYPRLAND_INSTANCE_SIGNATURE']
assert 'fake-hyprune-cli.py' in os.environ.get('HYPRUNE_CLI', ''), 'library-shots drives the fake CLI (leave HYPRUNE_CLI unset)'
pid = os.environ['HYPRUNE_SHELL_PID']
SHOTS = pathlib.Path(os.environ.get('HYPRUNE_LIBRARY_SHOTS', '/tmp/hyprune-library-shots'))
shutil.rmtree(SHOTS, ignore_errors=True); SHOTS.mkdir(parents=True)
OUTPUT = os.environ.get('HYPRUNE_PREVIEW_OUTPUT', 'HYPRUNE-PREVIEW')
FAKE_STATE = pathlib.Path(os.environ['HYPRUNE_FAKE_CLI_STATE'])
HOLD = FAKE_STATE / 'hold'
METHODS = ','.join(['objects.catalog', 'objects.pocket', 'libraries.list', 'libraries.install', 'libraries.remove'])


def call(*args): return subprocess.check_output(args, text=True).strip()
def ui(*args): return call('qs', 'ipc', '--pid', pid, 'call', 'preview', *map(str, args))
def ctl(code): return call('hyprctl', '-i', session['HYPRLAND_INSTANCE_SIGNATURE'], 'eval', code)
def status(): return json.loads(ui('status'))
def library(): return status()['library']
def job(): return library()['job']
def actions(method): return [a['params'] for a in status()['previewActions'] if a['method'] == method]
def hold(stage): HOLD.parent.mkdir(parents=True, exist_ok=True); HOLD.write_text(stage)
def release(): HOLD.unlink(missing_ok=True)


def wait(predicate, timeout=8):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate(): return
        time.sleep(.1)
    raise AssertionError('timed out: ' + json.dumps(library())[:1500])


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


def loaded(entries=8):
    ui('libraryRefresh')
    wait(lambda: library()['loaded'] and library()['entries'] == entries and not library()['busy'])


def idle(): wait(lambda: not library()['busy'])


def press(name):
    assert ui('press', name) == 'true', name


release()
subprocess.check_call([sys.executable, str(ROOT / 'dev/fake-hyprune-cli.py'), 'reset'])
time.sleep(2)
assert status()['lease']
ctl('hl.dispatch(hl.dsp.cursor.move({x=40,y=40}))')  # park the nested software cursor
USAGE = {'placements': 0, 'assets': 0, 'triangles': 0, 'gpuBytes': 0, 'collisionTriangles': 0}
LIMITS = {'placements': 128, 'assets': 32, 'triangles': 400000, 'gpuBytes': 201326592, 'collisionTriangles': 10000}
ui('statePreview', json.dumps({'objects': {'catalogRevision': 3, 'instances': [], 'pocket': [], 'usage': USAGE, 'limits': LIMITS}}), METHODS)
ui('objectPreview', json.dumps({'catalog': {'revision': 3, 'entries': []}, 'libraries': []}))
sizes = [(1920, 1080, 1, ''), (1280, 720, 1, '-720p'), (2560, 1440, 2, '-1440p-s2'), (3840, 2160, 1, '-4k')]
for w, h, scale, suffix in sizes:
    ctl(f'hl.monitor({{output="{OUTPUT}",mode="{w}x{h}@60",position="{"1280x0" if OUTPUT == "HYPRUNE-PREVIEW" else "0x0"}",scale={scale}}})')
    time.sleep(1.2)
    ui('close'); time.sleep(.4)
    ui('open'); time.sleep(.8)
    assert status()['director']
    ui('tabNamed', 'library'); ui('libraryView', 'browse')
    wait(lambda: status()['tabName'] == 'library')
    loaded()
    ui('libraryFilter', 'all', 'all', '')
    shot('browse' + suffix)
    ui('libraryView', 'installed'); ui('librarySelect', 'com.hyprune.lumen-reach')
    shot('installed' + suffix)
    ui('libraryView', 'sources')
    shot('sources' + suffix)
    ui('libraryView', 'browse')
    if suffix:
        ui('close'); time.sleep(.4)
        continue

    # Browse: filters, search and the keyboard cursor.
    assert ui('libraryFilter', 'all', 'library', '') == 'true'; wait(lambda: library()['shown'] == 4)
    shot('browse-libraries')
    ui('libraryFilter', 'all', 'all', 'coast'); wait(lambda: library()['shown'] == 3)
    shot('browse-search-coast')
    ui('libraryFilter', 'franks-stuff', 'all', ''); wait(lambda: library()['shown'] == 2)
    shot('browse-custom-source')
    ui('libraryFilter', 'all', 'all', '')
    assert ui('press', 'libraryAct:community/io.github.cy.orbital') == 'false'  # needs a newer Hyprune
    assert ui('press', 'libraryAct:official/com.hyprune.starter') == 'false'    # system-managed
    assert ui('focusNamed', 'libraryBrowse') == 'true'
    call('wtype', '-k', 'Down'); wait(lambda: library()['cursor'] == 1)
    call('wtype', '-k', 'Right'); wait(lambda: status()['tabName'] == 'places')  # Left/Right still change views
    call('wtype', '-k', 'Left'); wait(lambda: status()['tabName'] == 'library')
    ui('theme', 'true'); shot('browse-paper'); ui('theme', 'false')

    # Install a library: plan -> confirmation -> progress -> done -> the object catalog refreshes.
    press('libraryAct:official/com.hyprune.street')
    wait(lambda: job() and job()['phase'] == 'confirm')
    assert job()['args'] == ['install', 'com.hyprune.street', '--from', 'official', '--plan', '--json'], job()
    shot('install-confirm')
    ui('theme', 'true'); shot('install-confirm-paper'); ui('theme', 'false')
    hold('progress')
    catalogs = len(actions('objects.catalog'))
    press('library-job-primary')
    wait(lambda: job()['phase'] == 'running' and job()['progress'] and job()['progress']['bytes'] > 0)
    assert job()['args'] == ['install', 'com.hyprune.street', '--from', 'official', '--yes', '--json'], job()
    shot('install-progress')
    release()
    wait(lambda: job()['phase'] == 'done')
    assert job()['result']['type'] == 'library' and job()['stages'][-1] == 'committing', job()
    wait(lambda: len(actions('objects.catalog')) > catalogs and actions('libraries.list'))
    shot('install-done')
    press('library-job-primary')  # Open in Objects
    wait(lambda: status()['tabName'] == 'objects' and status()['objects']['view'] == 'catalog')
    ui('tabNamed', 'library'); wait(lambda: status()['tabName'] == 'library' and library()['job'] is None)
    idle()
    assert any(i.startswith('com.hyprune.street@v1.2.0') for i in library()['installs']), library()['installs']

    # Update with a required library listed in the plan; Cancel leaves everything as it was.
    press('libraryAct:official/com.hyprune.lumen-reach')
    wait(lambda: job() and job()['phase'] == 'confirm')
    assert job()['args'][:2] == ['update', 'com.hyprune.lumen-reach'], job()
    shot('update-confirm-requirements')
    press('library-job-secondary')
    wait(lambda: library()['job'] is None)

    # A source change needs a second, explicit confirmation before --accept-source-change.
    press('libraryAct:franks-stuff/io.github.ada.tidepool')
    wait(lambda: job() and job()['phase'] == 'confirm' and job()['sourceChange'])
    shot('source-change')
    press('library-job-primary')
    time.sleep(.5)
    assert job()['phase'] == 'confirm' and '--yes' not in job()['args'], job()  # nothing ran yet
    shot('source-change-confirm')
    press('library-job-primary')
    wait(lambda: job()['phase'] == 'done')
    assert '--accept-source-change' in job()['args'] and '--yes' in job()['args'], job()
    press('library-job-back'); wait(lambda: library()['job'] is None); idle()

    # A failure shows core's words and the rule; nothing is installed.
    press('libraryAct:franks-stuff/org.example.frank.lamps')
    wait(lambda: job() and job()['phase'] == 'confirm')
    shot('install-confirm-custom')
    press('library-job-primary')
    wait(lambda: job()['phase'] == 'failed')
    assert job()['error']['rule'] == 'hash.mismatch', job()
    shot('install-error')
    press('library-job-back'); wait(lambda: library()['job'] is None); idle()

    # Installed: roll back (pins), unpin, remove behind a second press; system rows are read only.
    ui('libraryView', 'installed'); ui('librarySelect', 'com.hyprune.lumen-reach'); time.sleep(.3)
    press('library-install-rollback'); idle()
    wait(lambda: 'com.hyprune.lumen-reach@lumen-reach-v0.9.0:pinned' in library()['installs'])
    assert 'Rolled back' in library()['feedback']['text'], library()['feedback']
    shot('installed-rolled-back')
    press('library-install-unpin'); idle()
    wait(lambda: 'com.hyprune.lumen-reach@lumen-reach-v0.9.0' in library()['installs'])
    ui('librarySelect', 'com.hyprune.starter'); time.sleep(.3)
    assert ui('press', 'library-install-remove') == 'false'  # no actions for system-managed installs
    shot('installed-system')
    ui('librarySelect', 'io.github.dee.lanterns'); time.sleep(.3)
    press('library-install-remove')
    assert library()['confirm'] == 'remove:io.github.dee.lanterns' and not library()['busy']
    shot('installed-confirm-remove')
    press('library-install-remove'); idle()
    wait(lambda: not any(i.startswith('io.github.dee.lanterns') for i in library()['installs']))
    ui('theme', 'true'); ui('librarySelect', 'io.github.ada.tidepool'); shot('installed-paper'); ui('theme', 'false')

    # Sources: add (github: with a label), a package URL without its hash, disable / enable, refresh.
    ui('libraryView', 'sources'); time.sleep(.3)
    assert ui('libraryForm', 'github:ada/more-worlds', 'Ada two', '') == 'true'
    wait(lambda: library()['form']['ok'])
    shot('sources-add-form')
    press('source-add'); idle()
    wait(lambda: library()['sources'] == 6)
    assert ui('libraryForm', 'https://example.org/packs/lamp-pack-1.0.0.tar.zst', '', '') == 'true'
    wait(lambda: library()['form']['needsHash'] and not library()['form']['ok'])
    shot('sources-add-needs-hash')
    ui('libraryForm', 'https://example.org/broken/index.json', 'Broken', '')
    press('source-add'); idle()
    assert 'source.invalid' in library()['feedback']['text'], library()['feedback']
    shot('sources-add-refused')
    ui('libraryForm', '', '', '')
    press('source-toggle:community'); idle()
    wait(lambda: library()['entries'] == 5)
    shot('sources-community-disabled')
    press('source-toggle:community'); idle(); wait(lambda: library()['entries'] == 8)
    press('source-refresh:official'); idle()
    press('source-remove:ada-two'); assert library()['confirm'] == 'source:ada-two'
    press('source-remove:ada-two'); idle(); wait(lambda: library()['sources'] == 5)

    # A job finishing while the Director is closed shows a HUD toast.
    ui('libraryView', 'installed'); ui('librarySelect', 'io.github.ada.tidepool'); time.sleep(.3)
    hold('committing')
    press('library-install-pin')
    wait(lambda: library()['busy'])
    ui('close'); time.sleep(.5)
    release()
    wait(lambda: any(t.get('title') == 'Library' for t in status()['quests']['toasts']))
    shot('hud-toast')
    time.sleep(4.5)

ui('statePreview', '', ''); ui('objectPreview', '')
release()
logs = (ROOT / 'dev/.run/shell.log').read_text()
assert not any(x in logs for x in ['ReferenceError', 'TypeError', 'Binding loop', 'Unable to assign']), logs[-3000:]
print('PASS library captures:', ', '.join(taken), '->', SHOTS)
