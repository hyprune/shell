#!/usr/bin/env python3
"""Movement and Reticle settings captures (IPC 0.19 player settings, dev preview data).

Launched only by dev/run's validated nested lifetime: dev/run player
The SDK mock speaks IPC 0.2, so the sections are fed through the dev-only
`playerPreview` hook (ShellState.dev); no player.* call reaches any core.
HYPRUNE_PLAYER_SHOTS overrides the output folder.
"""
import json, os, pathlib, subprocess, time
ROOT = pathlib.Path(__file__).resolve().parent.parent
session = json.loads((ROOT / 'dev/.run/session.json').read_text())
# dev/run already refused the parent session; confirm we still target its nested one.
assert session['WAYLAND_DISPLAY'] == os.environ['WAYLAND_DISPLAY']
assert session['HYPRLAND_INSTANCE_SIGNATURE'] == os.environ['HYPRLAND_INSTANCE_SIGNATURE']
pid = os.environ['HYPRUNE_SHELL_PID']
SHOTS = pathlib.Path(os.environ.get('HYPRUNE_PLAYER_SHOTS', ROOT / 'docs/evidence/ipc18'))
SHOTS.mkdir(parents=True, exist_ok=True)
DEFAULTS = {'walk_speed': 4.0, 'run_speed': 10.0, 'view_bob': 'subtle', 'reticle_style': 'cross_dot', 'reticle_size': 18,
            'reticle_thickness': 2, 'reticle_gap': 4, 'reticle_opacity': 0.9, 'reticle_outline': True,
            'reticle_colour': 'theme', 'reticle_dynamic': True, 'reach_grab': 15, 'reach_mount': 8, 'reach_placement': 12}
RANGES = {'walk_speed': [0.5, 20], 'run_speed': [0.5, 30], 'reticle_size': [6, 64], 'reticle_thickness': [1, 6],
          'reticle_gap': [0, 20], 'reticle_opacity': [0.2, 1], 'reach_grab': [1, 100], 'reach_mount': [1, 100], 'reach_placement': [1, 100]}
CONFIG = {**DEFAULTS, 'walk_speed': 4.5, 'run_speed': 11.5, 'reach_grab': 20, 'reticle_size': 28, 'reticle_thickness': 2.5}
SETTINGS = {'config': CONFIG, 'defaults': DEFAULTS, 'overrides': {k: v for k, v in CONFIG.items() if DEFAULTS[k] != v},
            'options': {'view_bob': ['off', 'subtle', 'normal'], 'reticle_style': ['cross_dot', 't_dot', 'circle_dot', 'dot', 'cross', 'chevron']},
            'ranges': RANGES, 'path': '/dev/null', 'error': ''}


def call(*args): return subprocess.check_output(args, text=True).strip()
def ui(*args): return call('qs', 'ipc', '--pid', pid, 'call', 'preview', *map(str, args))
def ctl(code): return call('hyprctl', '-i', session['HYPRLAND_INSTANCE_SIGNATURE'], 'eval', code)
def status(): return json.loads(ui('status'))


def shot(name):
    time.sleep(.6)
    audit = json.loads(ui('layoutAudit'))
    assert audit['labels'] > 0 and not audit['failures'], (name, audit)
    call('grim', '-o', 'HYPRUNE-PREVIEW', str(SHOTS / (name + '.png')))
    return name


taken = []
time.sleep(2)
assert status()['lease']
ctl('hl.dispatch(hl.dsp.cursor.move({x=40,y=40}))')  # park the nested software cursor
assert not status()['playerSupported']  # IPC 0.2 mock: no Movement/Reticle sections
for w, h, scale, suffix in [(1920, 1080, 1, ''), (1920, 1080, 2, '-s2')]:
    ctl(f'hl.monitor({{output="HYPRUNE-PREVIEW",mode="{w}x{h}@60",position="1280x0",scale={scale}}})')
    time.sleep(1.2)
    ui('open'); time.sleep(.8)
    assert status()['director']
    ui('tabNamed', 'settings')
    ui('playerPreview', '')
    ui('settingsSection', 3); time.sleep(.3)
    if not suffix: taken.append(shot('settings-unsupported-night'))  # < 0.19: note only, no section buttons
    ui('playerPreview', json.dumps(SETTINGS))
    assert status()['playerSupported']
    for theme in ['night', 'paper']:
        ui('theme', 'true' if theme == 'paper' else 'false')
        ui('settingsSection', 3); time.sleep(.3); ui('settingsScroll', 0)
        taken.append(shot(f'movement-{theme}{suffix}'))
        ui('settingsScroll', 1); taken.append(shot(f'movement-{theme}-end{suffix}'))
        for style in (['cross_dot', 'circle_dot', 'chevron'] if not suffix and theme == 'night' else ['cross_dot']):
            ui('playerPreview', json.dumps({**SETTINGS, 'config': {**CONFIG, 'reticle_style': style,
                                            'reticle_colour': [0.3, 0.88, 1] if style == 'chevron' else 'theme'}}))
            ui('settingsSection', 4); time.sleep(.3); ui('settingsScroll', 0)
            taken.append(shot(f'reticle-{theme}{"" if style == "cross_dot" else "-" + style}{suffix}'))
        ui('settingsScroll', 1); taken.append(shot(f'reticle-{theme}-end{suffix}'))
        ui('playerPreview', json.dumps(SETTINGS))
    ui('theme', 'false')
    ui('close'); time.sleep(.5)
logs = (ROOT / 'dev/.run/shell.log').read_text()
assert not any(x in logs for x in ['ReferenceError', 'TypeError', 'Binding loop', 'Unable to assign']), logs[-3000:]
print('PASS player settings captures:', ', '.join(taken), '->', SHOTS)
