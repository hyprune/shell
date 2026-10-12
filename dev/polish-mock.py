#!/usr/bin/env python3
"""SDK mock visual matrix; invoked only by dev/run polish under its flock."""
import json, os, pathlib, subprocess, time
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent)); import devenv  # noqa: E402
ROOT=pathlib.Path(__file__).resolve().parent.parent
GALLERY=devenv.gallery_dir()/'screenshots/hyprune-shell-polish'
GALLERY.mkdir(parents=True,exist_ok=True)
session=json.loads((ROOT/'dev/.run/session.json').read_text())
assert session['WAYLAND_DISPLAY']==os.environ['WAYLAND_DISPLAY']
assert session['HYPRLAND_INSTANCE_SIGNATURE']==os.environ['HYPRLAND_INSTANCE_SIGNATURE']
pid=os.environ['HYPRUNE_SHELL_PID']
def call(*args):return subprocess.check_output(args,text=True).strip()
def ui(*args):return call('qs','ipc','--pid',pid,'call','preview',*map(str,args))
def ctl(code):return call('hyprctl','-i',session['HYPRLAND_INSTANCE_SIGNATURE'],'eval',code)
def shot(name):
 time.sleep(.45)
 audit=json.loads(ui('layoutAudit'))
 assert audit['labels'] > 0 and not audit['failures'], (name,audit)
 call('grim','-o','HYPRUNE-PREVIEW',str(GALLERY/(name+'.png')))
time.sleep(2)
assert json.loads(ui('status'))['lease']
for w,h in [(1920,1080),(2560,1440),(3840,2160)]:
 for scale in [1,2]:
  prefix=f'mock-{h}p-s{scale}'
  ctl(f'hl.monitor({{output="HYPRUNE-PREVIEW",mode="{w}x{h}@60",position="1280x0",scale={scale}}})')
  time.sleep(1)
  ui('close');ui('curvature',0);shot(prefix+'-hud-flat')
  ui('curvature',.6);shot(prefix+'-hud-curved')
  ui('open');time.sleep(.7)
  assert json.loads(ui('status'))['director']
  for name in ['map','quests','objects','places','surfaces','workspaces','help','whats-new','settings']:
   ui('tabNamed',name.replace('-',''));shot(prefix+'-'+name)
  ui('theme','true');shot(prefix+'-settings-paper');ui('theme','false')
  ui('warp');time.sleep(.5);shot(prefix+'-warp')
  for _ in range(100):
   if not json.loads(ui('status'))['warp']: break
   time.sleep(.1)
  assert not json.loads(ui('status'))['warp']
logs=(ROOT/'dev/.run/shell.log').read_text()
assert not any(x in logs for x in ['ERROR','ReferenceError','TypeError','Binding loop','Unable to assign']),logs
print('PASS SDK matrix: six physical-resolution/output-scale combinations, all seven pages, HUD flat/curved, warp')
