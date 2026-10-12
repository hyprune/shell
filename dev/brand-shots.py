#!/usr/bin/env python3
"""Brand mark captures: Director header, Settings About and Performance.

Launched only by dev/run's validated nested lifetime: dev/run brand
HYPRUNE_BRAND_SHOTS overrides the output folder.
"""
import json, os, pathlib, subprocess, time
ROOT = pathlib.Path(__file__).resolve().parent.parent
session = json.loads((ROOT / 'dev/.run/session.json').read_text())
# dev/run already refused the parent session; confirm we still target its nested one.
assert session['WAYLAND_DISPLAY'] == os.environ['WAYLAND_DISPLAY']
assert session['HYPRLAND_INSTANCE_SIGNATURE'] == os.environ['HYPRLAND_INSTANCE_SIGNATURE']
pid = os.environ['HYPRUNE_SHELL_PID']
SHOTS = pathlib.Path(os.environ.get('HYPRUNE_BRAND_SHOTS', ROOT / 'dev/.run/brand'))
SHOTS.mkdir(parents=True, exist_ok=True)
RULE = lambda px: 'h16' if px <= 16 else 'h32' if px < 48 else 'optical' if px < 96 else 'primary'


def call(*args): return subprocess.check_output(args, text=True).strip()
def ui(*args): return call('qs', 'ipc', '--pid', pid, 'call', 'preview', *map(str, args))
def ctl(code): return call('hyprctl', '-i', session['HYPRLAND_INSTANCE_SIGNATURE'], 'eval', code)


report = []
time.sleep(2)
assert json.loads(ui('status'))['lease']
# Park the nested software cursor outside the preview output.
ctl('hl.dispatch(hl.dsp.cursor.move({x=40,y=40}))')
for w, h, scale, suffix in [(1920, 1080, 1, ''), (1920, 1080, 2, '-s2'), (1920, 1080, 1.25, '-s1.25'), (3840, 2160, 1, '-4k')]:
    ctl(f'hl.monitor({{output="HYPRUNE-PREVIEW",mode="{w}x{h}@60",position="1280x0",scale={scale}}})')
    time.sleep(1.2)
    ui('open'); time.sleep(.8)
    assert json.loads(ui('status'))['director']
    for theme in ['night', 'paper']:
        ui('theme', 'true' if theme == 'paper' else 'false')
        for tab, surface in [('map', 'director'), ('settings', 'settings'), ('performance', 'performance')]:
            ui('tabNamed', tab)
            if surface == 'settings':
                ui('settingsSection', 0); time.sleep(.3); ui('settingsScroll', 1)
            time.sleep(.6)
            audit = json.loads(ui('layoutAudit'))
            assert audit['labels'] > 0 and not audit['failures'], (surface, theme, suffix, audit)
            marks = json.loads(ui('brandMarks'))
            header = next(m for m in marks if m['name'] == 'brandMark:director')
            assert header['sceneBox'][3] < 0.2 * h / scale, header
            assert {m['name'] for m in marks} >= {'brandMark:director'} | ({'brandMark:about'} if surface == 'settings' else set()), marks
            for m in marks:
                assert isinstance(m['size'], (int, float)) and m['physicalSize'] >= 16, m
                assert m['variant'] == RULE(m['physicalSize']), m
            name = f'shell-{surface}-{theme}{suffix}'
            call('grim', '-o', 'HYPRUNE-PREVIEW', str(SHOTS / f'{name}.png'))
            entry = {'shot': name, 'output': f'{w}x{h}', 'scale': scale, 'marks': marks}
            report.append(entry); print(json.dumps(entry), flush=True)
    ui('theme', 'false'); ui('close'); time.sleep(.5)
ctl('hl.monitor({output="HYPRUNE-PREVIEW",mode="1920x1080@60",position="1280x0",scale=1})')
(SHOTS / 'brand-report.json').write_text(json.dumps(report, indent=1) + '\n')
logs = (ROOT / 'dev/.run/shell.log').read_text()
assert not any(x in logs for x in ['ERROR', 'ReferenceError', 'TypeError', 'Binding loop', 'Unable to assign']), logs[-4000:]
print('DONE', SHOTS, flush=True)
