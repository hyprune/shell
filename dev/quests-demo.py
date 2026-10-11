#!/usr/bin/env python3
"""Record the IPC 0.21 quests demo (about 50 s) in Lumen Reach with this shell on real core.

Nested only, inside core's harness, like dev/quests-core.py:
  HYPRUNE_NESTED_STATE_ROOT=/tmp/x python3 $CORE/dev/nested/isolated.py dev/quests-demo.py OUT.mkv
In order: walking in Sun Court; a TAB tap reveals markers (fade in, hold, fade out); a TAB
hold opens the Director; the Quests tab; a personal quest typed into the form (its steps
at Array Hall) and tracked; the tracked edge arrow, then turning toward it to its diamond;
a focus session started with F, the HUD chip counting down into the break (focus clock
scaled by core's quests harness). wf-recorder captures HEADLESS-1 (NVENC constant QP);
encoding for publication is a separate step. OUT.json gets the timeline.
"""
import argparse, json, math, os, pathlib, secrets, signal, subprocess, sys, time, types
ROOT = pathlib.Path(__file__).resolve().parent.parent
CORE = pathlib.Path(os.environ.get('HYPRUNE_CORE_DIR', str(ROOT.parent / 'core')))
sys.path.insert(0, str(CORE / 'dev/nested'))
import session as s  # noqa: E402
import quests  # noqa: E402
from ctl import verified  # noqa: E402
from m2 import wait, keys  # noqa: E402
LUMEN = 'com.hyprune.lumen-reach'
SHELL_TOKEN = secrets.token_hex(32)
SHELL_GRANT = {'token': SHELL_TOKEN, 'client': 'com.hyprune.shell',
               'capabilities': ['state.read', 'world.control', 'surface.control', 'movement.control', 'shell.control',
                                'runtime.control', 'quest.control']}
OUT = None


def acceptance(client, children, args, shell_token, socketpath):
    sub = client.call('state.subscribe', {'topics': ['state']})['subscriptionId']
    def state(): return client.call('state.snapshot', {'subscriptionId': sub})['snapshot']['state']
    manifest = json.loads((s.STATE / 'worlds' / LUMEN / 'world.json').read_text())
    nodes = {n['id']: n['position'] for n in manifest['extensions']['com.hyprune.lumen-reach.routes']['nodes']}
    s.ctl('eval', 'hl.dispatch(hl.dsp.focus({ monitor = "HEADLESS-1" }))')
    client.call('world.load', {'worldId': LUMEN})
    client.call('graphics.set', {'patch': {'quality': 'high'}})
    s.ctl('eval', 'hl.plugin.hyprune.toggle("HEADLESS-1")'); wait(lambda: s.camera()['active'])
    client.call('movement.set', {'modeId': 'com.hyprune.walk'})
    # 5-minute work and 1-minute break run 15 s and 3 s at the harness's focus clock scale.
    client.call('guidance.set', {'patch': {'focus.work_min': 5, 'focus.short_break_min': 1, 'focus.cycles': 2}})
    r, w = os.pipe(); os.write(w, (SHELL_TOKEN + '\n').encode()); os.close(w)
    _, env = verified()
    env.update(HYPRUNE_TOKEN_FD=str(r), HYPRUNE_PROTOCOL='0.21', HYPRUNE_SOCKET=str(socketpath), HYPRUNE_OUTPUT_SCREEN='HEADLESS-1',
               HYPRUNE_DEV_AUTOMATION='1', HYPRUNE_SHELL_PREFERENCES=str(s.STATE / 'shell-preferences.json'))
    shell = subprocess.Popen(['python3', str(ROOT / 'bridge/launch.py'), '--protocol', '0.21'], env=env, pass_fds=(r,),
                             stdout=open(s.STATE / 'shell.log', 'w'), stderr=subprocess.STDOUT)
    os.close(r); children.append(shell)
    qpid = wait(lambda: next((int(p) for p in pathlib.Path(f'/proc/{shell.pid}/task/{shell.pid}/children').read_text().split()
                              if pathlib.Path(f'/proc/{p}/comm').read_text().strip() in ['qs', 'quickshell']), None))
    def ui(*a):
        verified(); return subprocess.check_output([str(s.HERE / 'ctl.py'), 'env', 'qs', 'ipc', '--pid', str(qpid), 'call', 'preview', *map(str, a)], text=True).strip()
    def status():
        try: return json.loads(ui('status'))
        except (subprocess.CalledProcessError, json.JSONDecodeError): return {}
    def park(): s.ctl('eval', 'hl.dispatch(hl.dsp.cursor.move({x=1919,y=1079}))')
    def look(x, y, z, yaw, pitch=0): s.ctl('eval', f'hl.plugin.hyprune.camera({x},{y},{z},{yaw},{pitch})')
    def open_director():
        for attempt in range(2):  # a hold that lands while core is busy is retried once
            keys('-P', 'Tab', '-s', '1200', '-p', 'Tab')
            try: wait(lambda: status().get('director'), 4); break
            except AssertionError:
                if attempt: raise
                print('DEMO retry: Director hold', status().get('mode'), flush=True)
        park()
    wait(lambda: status().get('lease'), 20)
    # Start just inside Sun Court, facing the court wall; warm up before the first frame.
    a, b = nodes['arrival'], nodes['court-junction']
    yaw = math.atan2(b[0] - a[0], -(b[2] - a[2]))
    look(a[0], a[1] + 1.7, a[2], yaw, -.03); park()
    time.sleep(5)
    log = open(s.STATE / 'recorder.log', 'w')
    recorder = s.envrun('wf-recorder', '-o', 'HEADLESS-1', '-r', '30', '-D', '--no-dmabuf', '-c', 'h264_nvenc', '-x', 'bgr0',
                        '-p', 'preset=p4', '-p', 'rc=constqp', '-p', 'qp=16', '-f', str(OUT), stdout=log, stderr=subprocess.STDOUT)
    children.append(recorder)
    started = time.monotonic(); timeline = []
    def mark(event): timeline.append({'t': round(time.monotonic() - started, 1), 'event': event}); print('DEMO', timeline[-1], flush=True)
    try:
        time.sleep(1.5)
        mark('walking in Sun Court')
        client.call('route.set', {'points': [{'position': [b[0], b[1] + 1.7, b[2]]}]})
        client.call('autodrive.start', {'speed': 1.6})
        time.sleep(4.5)
        client.call('autodrive.stop', {})
        # Face the court wall (homes and workspaces ahead), then tap TAB.
        here = state()['movement']['position']
        for i in range(1, 31):
            look(here[0], here[1], here[2], yaw * (1 - i / 30), .05 * i / 30); time.sleep(1 / 30)
        time.sleep(.5)
        mark('TAB tap: markers fade in, hold, fade out')
        keys('-k', 'Tab')
        wait(lambda: state()['markers']['reveal'], 3)
        time.sleep(5.6)
        mark('TAB hold: the Director opens')
        open_director()
        time.sleep(1.2)
        keys('-k', 'Right'); wait(lambda: status().get('tab') == 1, 3)  # Quests is the next tab
        mark('Quests tab: new personal quest')
        time.sleep(1)
        keys('n'); time.sleep(.6)
        keys('-d', '35', 'Ship the release notes'); time.sleep(.3)
        keys('-k', 'Tab', '-k', 'Tab'); time.sleep(.2)
        keys('-d', '35', 'Draft the notes'); keys('-k', 'Return'); keys('-d', '35', 'Publish'); time.sleep(.4)
        # Where: Array Hall (an area home); one focus session for the first step.
        ui('questForm', json.dumps({'title': 'Ship the release notes', 'steps': 'Draft the notes\nPublish', 'targetKind': 'area',
                                    'targetValue': 'array-hall', 'sessions': {'Draft the notes': 1}}))
        time.sleep(2.2)
        assert ui('press', 'quest-form-save') == 'true'
        ref = {'source': 'personal', 'id': 'ship-the-release-notes'}
        wait(lambda: state()['quests']['tracked'] == ref, 5)
        mark('created and tracked')
        time.sleep(3)
        keys('-k', 'Escape'); wait(lambda: not status().get('director'), 5)
        # Array Hall lies ahead (north): look a quarter turn away so its arrow sits on the
        # screen edge, then turn toward it (diamond).
        here = state()['movement']['position']
        away = -math.pi / 2
        look(here[0], here[1], here[2], away, 0)
        mark('tracked step: edge arrow')
        time.sleep(3.5)
        for i in range(1, 31):
            look(here[0], here[1], here[2], away * (1 - (1 - math.cos(math.pi * i / 30)) / 2), 0); time.sleep(1 / 30)
        mark('turned toward it: diamond')
        time.sleep(3)
        mark('focus session from the quest (F)')
        open_director()
        if status().get('tab') != 1: keys('-k', 'Right'); wait(lambda: status().get('tab') == 1, 3)
        time.sleep(.8)
        keys('f')
        try: wait(lambda: state()['focus']['state'] == 'work', 2)
        except AssertionError:  # keyboard focus elsewhere on the page: the same action by its button
            assert ui('press', 'quest-focus') == 'true'; wait(lambda: state()['focus']['state'] == 'work', 3)
            mark('(F fell back to the Focus session button)')
        time.sleep(1.2)
        keys('-k', 'Escape'); wait(lambda: not status().get('director'), 5)
        mark('HUD timer chip counting down')
        wait(lambda: state()['focus']['state'] == 'break', 25)
        mark('break: chip and suggestion toast')
        time.sleep(4)
    finally:
        recorder.send_signal(signal.SIGINT); recorder.wait(timeout=30); log.close()
    report = {'output': str(OUT), 'seconds': round(time.monotonic() - started, 1), 'timeline': timeline,
              'focusTimeScale': quests.SCALE}
    pathlib.Path(str(OUT) + '.json').write_text(json.dumps(report, indent=2) + '\n')
    errors = (s.STATE / 'shell.log').read_text()
    assert not any(x in errors for x in ['ReferenceError', 'TypeError', 'Unable to assign']), errors[-2000:]
    print('DEMO DONE', json.dumps({'seconds': report['seconds']}), flush=True)
    client.call('runtime.exit', {})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('output'); OUT = pathlib.Path(parser.parse_args().output).resolve()
    sys.modules['long_titles'] = types.SimpleNamespace(grants=lambda: [SHELL_GRANT], prepare=lambda installed: None, finish=lambda: None)
    quests.acceptance = acceptance
    s.run(argparse.Namespace(m3b=False, m3a=False, m2=False, m1=False, integration=False, live=False, serve=False, record=False,
                             visible=False, quests=True, long_titles=True))
