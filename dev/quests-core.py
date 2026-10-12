#!/usr/bin/env python3
"""Real IPC 0.21 check: this shell against core's quests, markers and focus sessions.

Nested only, inside core's harness. On a host without a parent session:
  HYPRUNE_NESTED_STATE_ROOT=/tmp/x python3 $CORE/dev/nested/isolated.py dev/quests-core.py
With a parent session: flock /tmp/worldshell-nested.lock python3 dev/quests-core.py
HYPRUNE_CORE_DIR selects the core checkout (IPC 0.21, built). Lumen Reach comes from
../worlds/dist. Quest, focus and guidance files stay in the harness state dir; the focus
clock runs scaled (HYPRUNE_FOCUS_TIME_SCALE from core's quests prepare).

Checks (each reported PASS/FAIL; the run fails if any fails):
 hello 0.21 with quest.control; Quests tab create (form), track/untrack, mark a step done
 (toast), edit (progress kept), delete; Settings > Guidance round trip; a focus session
 started from a quest's focus objective, the HUD chip counting down and switching to the
 break; the hold ring: a TAB tap never shows it, a hold shows it after the delay and
 opens the Director. Stills go to HYPRUNE_QUESTS_CORE_SHOTS (default dev/.run/quests-core).
"""
import argparse, json, os, pathlib, secrets, shutil, subprocess, sys, time, types
ROOT = pathlib.Path(__file__).resolve().parent.parent
CORE = pathlib.Path(os.environ.get('HYPRUNE_CORE_DIR', str(ROOT.parent / 'core')))
sys.path.insert(0, str(CORE / 'dev/nested'))
import session as s  # noqa: E402
import quests  # noqa: E402
from ctl import verified  # noqa: E402
from m2 import wait, keys  # noqa: E402
SHOTS = pathlib.Path(os.environ.get('HYPRUNE_QUESTS_CORE_SHOTS', str(ROOT / 'dev/.run/quests-core')))
LUMEN = 'com.hyprune.lumen-reach'
SHELL_TOKEN = secrets.token_hex(32)
# The harness grants the shell no quest.control; this launch grant does (input.control is
# added to every grant by the harness).
SHELL_GRANT = {'token': SHELL_TOKEN, 'client': 'com.hyprune.shell',
               'capabilities': ['state.read', 'world.control', 'surface.control', 'movement.control', 'shell.control',
                                'runtime.control', 'quest.control']}


def acceptance(client, children, args, shell_token, socketpath):
    results = []

    def check(name, ok, data=None):
        results.append({'name': name, 'pass': bool(ok), 'evidence': data})
        print(('PASS' if ok else 'FAIL') + ' quests-core: ' + name, json.dumps(data)[:400] if data is not None else '', flush=True)
        return ok

    sub = client.call('state.subscribe', {'topics': ['state']})['subscriptionId']
    def state(): return client.call('state.snapshot', {'subscriptionId': sub})['snapshot']['state']
    s.ctl('eval', 'hl.dispatch(hl.dsp.focus({ monitor = "HEADLESS-1" }))')
    client.call('world.load', {'worldId': LUMEN})
    s.ctl('eval', 'hl.plugin.hyprune.toggle("HEADLESS-1")'); wait(lambda: s.camera()['active'])
    client.call('movement.set', {'modeId': 'com.hyprune.walk'})
    s.ctl('eval', 'hl.plugin.hyprune.camera(-8, 1.7, 12, 0, 0)')
    # Short intervals: 5 min work and 1 min breaks run 15 s and 3 s at the harness scale.
    client.call('guidance.set', {'patch': {'focus.work_min': 5, 'focus.short_break_min': 1, 'focus.cycles': 2}})
    r, w = os.pipe(); os.write(w, (SHELL_TOKEN + '\n').encode()); os.close(w)
    _, env = verified()
    env.update(HYPRUNE_TOKEN_FD=str(r), HYPRUNE_PROTOCOL='0.21', HYPRUNE_SOCKET=str(socketpath), HYPRUNE_OUTPUT_SCREEN='HEADLESS-1',
               HYPRUNE_DEV_AUTOMATION='1', HYPRUNE_SHELL_PREFERENCES=str(s.STATE / 'shell-preferences.json'))
    log = open(s.STATE / 'shell.log', 'w')
    shell = subprocess.Popen(['python3', str(ROOT / 'bridge/launch.py'), '--protocol', '0.21'], env=env, pass_fds=(r,), stdout=log, stderr=subprocess.STDOUT)
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

    def shot(name):
        time.sleep(.8)
        subprocess.run([str(s.HERE / 'ctl.py'), 'shot', str(SHOTS / (name + '.png'))], check=True)

    def press(name): return ui('press', name) == 'true'
    def park(): s.ctl('eval', 'hl.dispatch(hl.dsp.cursor.move({x=4,y=4}))')
    def director():
        keys('-P', 'Tab', '-s', '1150', '-p', 'Tab'); wait(lambda: status().get('director'), 5); park()
    def closed():
        keys('-k', 'Escape'); wait(lambda: not status().get('director'), 5)
    def listed(): return {q['questRef']['id']: q for q in client.call('quests.list', {})['quests']}
    def detail(id): return client.call('quests.get', {'questRef': {'source': 'personal', 'id': id}})['quest']
    def attempt(name, fn):
        try: return fn()
        except Exception as error:  # report and keep going
            import traceback
            where = [f'{f.lineno}: {f.line}' for f in traceback.extract_tb(error.__traceback__) if f.filename == __file__][-1:]
            check(name, False, {'error': repr(error)[:200], 'at': where})
            subprocess.run([str(s.HERE / 'ctl.py'), 'shot', str(SHOTS / ('FAILED-' + name.replace(' ', '-') + '.png'))])

    wait(lambda: status().get('lease'), 20)
    st = status()
    check('hello negotiates IPC 0.21 with quest.control', st.get('protocol') == '0.21' and 'quest.control' in st.get('capabilities', []),
          {'protocol': st.get('protocol'), 'capabilities': st.get('capabilities')})

    # Hold ring: a tap never shows the ring (core still reports the pending hold); a hold
    # shows it only after the delay, then opens the Director.
    def hold_ring():
        time.sleep(1)
        before = status()['holdStats']
        keys('-k', 'Tab')
        reveal = wait(lambda: state()['markers']['reveal'], 3)
        samples = []
        for _ in range(6): samples.append(status().get('holdFilling')); time.sleep(.1)
        after = status()['holdStats']
        check('TAB tap: markers reveal, the hold ring never shows', reveal['reason'] == 'tap' and after['shown'] == before['shown']
              and not any(samples) and not status().get('director'), {'before': before, 'after': after, 'reveal': reveal})
        time.sleep(5)  # let the reveal end
        keys('-P', 'Tab', '-s', '1400', '-p', 'Tab')
        opened = wait(lambda: status().get('director'), 5)
        stats = status()['holdStats']
        check('TAB hold: the ring shows after ~180 ms and the Director opens',
              opened and stats['shown'] == after['shown'] + 1 and 150 <= stats['lastDelayMs'] <= 320, stats)
        park(); closed()
    attempt('hold ring', hold_ring)

    # Quests tab: create through the form, track/untrack, mark done, edit, delete.
    def quest_page():
        director()
        ui('tabNamed', 'quests'); wait(lambda: status().get('tabName') == 'quests')
        ui('questForm', json.dumps({'title': 'Ship the release notes', 'summary': 'For the next release.',
                                    'steps': 'Draft at the workshop\nReview\nPublish', 'targetKind': 'area', 'targetValue': 'array-hall',
                                    'sessions': {'Review': 1}}))
        shot('core-quests-form')
        assert press('quest-form-save')
        quest = wait(lambda: listed().get('ship-the-release-notes'), 5)
        d = detail('ship-the-release-notes')
        check('create through the form (steps, area target, a focus step)',
              [s_['id'] for s_ in d['steps']] == ['draft-at-the-workshop', 'review', 'publish'] and
              d['steps'][0]['target'] == {'areaId': 'array-hall'} and d['steps'][1]['objectives'][0]['type'] == 'focus',
              {'steps': [(s_['id'], s_['objectives'][0]['type']) for s_ in d['steps']]})
        wait(lambda: (status().get('quests') or {}).get('detail') == 'Ship the release notes', 5)
        shot('core-quests-created')
        ref = {'source': 'personal', 'id': 'ship-the-release-notes'}
        tracked0 = state()['quests']['tracked']
        if tracked0 != ref:
            assert press('quest-track'); wait(lambda: state()['quests']['tracked'] == ref, 5)
        assert press('quest-track'); untracked = wait(lambda: state()['quests']['tracked'] is None, 5)
        assert press('quest-track'); retracked = wait(lambda: state()['quests']['tracked'] == ref, 5)
        check('Track / Untrack through the page', untracked and retracked, {'trackedAfterCreate': tracked0})
        assert press('quest-mark-draft-at-the-workshop-done')
        toast = wait(lambda: (status().get('quests') or {}).get('toasts'), 5)
        progress = detail('ship-the-release-notes')['steps'][0]['state']
        check('Mark done: the step completes and a step toast shows', progress == 'done' and toast[0]['line'] == '✓ Draft at the workshop'
              and toast[0]['detail'] == 'Next: Review', toast[0])
        wait(lambda: 'Review' in json.dumps(state()['quests']['active']), 5)
        ui('questForm', json.dumps({'edit': True, 'title': 'Ship the release notes 0.21', 'steps': 'Draft at the workshop\nReview\nTag\nPublish'}))
        shot('core-quests-edit')
        assert press('quest-form-save')
        e = wait(lambda: (lambda q: q if q['title'] == 'Ship the release notes 0.21' else None)(detail('ship-the-release-notes')), 5)
        check('Edit: title and steps change, the done step keeps its progress',
              [x['id'] for x in e['steps']] == ['draft-at-the-workshop', 'review', 'tag', 'publish'] and e['steps'][0]['state'] == 'done',
              [(x['id'], x['state']) for x in e['steps']])
        # A throwaway quest for Delete.
        ui('questForm', json.dumps({'title': 'Water the plants', 'steps': 'Kitchen\nBalcony'}))
        assert press('quest-form-save'); wait(lambda: 'water-the-plants' in listed(), 5)
        wait(lambda: (status().get('quests') or {}).get('detail') == 'Water the plants', 5)
        assert press('quest-delete') and press('quest-delete')
        check('Delete (confirmed) removes the quest', wait(lambda: 'water-the-plants' not in listed(), 5))
        ui('questSelect', 'personal/ship-the-release-notes')
        wait(lambda: (status().get('quests') or {}).get('detail') == 'Ship the release notes 0.21', 5)
        shot('core-quests-page')
    attempt('quests page', quest_page)

    # Map: core's markers.list on the shown level, the tracked step among them.
    def map_markers():
        ui('tabNamed', 'map'); time.sleep(1)
        listed_ids = {m['id'] for m in state()['markers']['list'] if m['position'] and m['kind'] != 'place'}
        drawn = set(json.loads(ui('mapMarkers')))
        tracked = [m['id'] for m in state()['markers']['list'] if m['tracked']]
        json.loads(ui('mapView', 1, 0, 0, 'auto'))
        shot('core-map-markers')
        check('Map draws markers.list (resolved, shown level), tracked step included', drawn and drawn <= listed_ids and
              any(t in drawn for t in tracked), {'drawn': sorted(drawn), 'tracked': tracked, 'listed': len(listed_ids)})
    attempt('map markers', map_markers)

    # Settings > Guidance: a toggle and a reset go through guidance.set and the file.
    def guidance():
        ui('tabNamed', 'settings'); ui('settingsSection', 5)
        wait(lambda: (status().get('quests') or {}).get('guidance'), 5)
        assert press('guidance-focus.desktop_chip')
        on = wait(lambda: client.call('guidance.get', {})['config']['focus.desktop_chip'] is True, 5)
        path = s.STATE / 'confighome/hyprune/guidance.json'
        saved = wait(lambda: path.exists() and json.loads(path.read_text()).get('focus.desktop_chip') is True, 8)
        shown = wait(lambda: status()['quests']['guidance']['focus.desktop_chip'] is True, 5)
        shot('core-settings-guidance')
        assert press('guidance-reset')
        reset = wait(lambda: client.call('guidance.get', {})['overrides'] == {}, 5)
        check('Settings > Guidance: toggle saved by core, shown, reset clears overrides', on and saved and shown and reset,
              {'file': str(path.name)})
        client.call('guidance.set', {'patch': {'focus.work_min': 5, 'focus.short_break_min': 1, 'focus.cycles': 2}})
    attempt('guidance', guidance)

    # Focus session from the quest's focus objective; the HUD chip counts down and turns to the break.
    def focus_session():
        ui('tabNamed', 'quests'); ui('questSelect', 'personal/ship-the-release-notes')
        wait(lambda: (status().get('quests') or {}).get('detail') == 'Ship the release notes 0.21', 5)
        time.sleep(.5)
        current = state()['workspaces']['currentId']
        assert press('segment:workspace'), 'focus target picker'
        assert press('quest-start-focus-review'), 'Start focus session button'
        f = wait(lambda: (lambda x: x if x['state'] == 'work' else None)(state()['focus']), 5)
        linked = (f['target'] or {}).get('questRef') == {'source': 'personal', 'id': 'ship-the-release-notes'}
        check('focus target picker: Workspace defaults to the current workspace', current and f['target']['kind'] == 'workspace'
              and f['target'].get('workspaceId') == current, {'current': current, 'target': f['target']})
        shot('core-quests-focus-started')
        closed()
        s.ctl('eval', 'hl.plugin.hyprune.camera(-8, 1.7, 12, 0, 0)')
        first = wait(lambda: status().get('focusChip') and status()['focusChip']['time'], 5)
        time.sleep(2.2)
        second = status()['focusChip']['time']
        shot('core-hud-focus-work')
        def secs(t): m, s_ = t.split(':')[-2:]; return int(m) * 60 + int(s_)
        check('focus.start from the quest focus objective; the HUD chip counts down',
              linked and f['phaseMs'] == 15000 and secs(second) < secs(first) <= 15, {'first': first, 'second': second, 'target': f['target']})
        brk = wait(lambda: status().get('focusChip') if (status().get('focusChip') or {}).get('phase') == 'SHORT BREAK' else None, 25)
        toast = (status().get('quests') or {}).get('toasts') or []
        shot('core-hud-focus-break')
        check('the chip switches to the break; a focus toast shows', state()['focus']['state'] == 'break' and brk['phase'] == 'SHORT BREAK',
              {'chip': brk, 'toast': toast[:1]})
        client.call('focus.stop', {})
    attempt('focus session', focus_session)

    errors = (s.STATE / 'shell.log').read_text()
    bad = [x for x in ['ReferenceError', 'TypeError', 'Binding loop', 'Unable to assign', 'Unknown shell action', 'does not match the negotiated protocol'] if x in errors]
    check('no QML runtime errors or protocol mismatches in the shell log', not bad, bad)
    (SHOTS / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    failed = [r_['name'] for r_ in results if not r_['pass']]
    print(('PASS' if not failed else 'FAIL') + f' quests-core: {len(results) - len(failed)}/{len(results)} checks', failed, flush=True)
    client.call('runtime.exit', {})
    if failed: raise SystemExit(1)


def harness_grants():
    return [SHELL_GRANT]


if __name__ == '__main__':
    shutil.rmtree(SHOTS, ignore_errors=True); SHOTS.mkdir(parents=True)
    # Ride the harness's extra-grant hook (it also selects its m3b lifetime) without its checks.
    sys.modules['long_titles'] = types.SimpleNamespace(grants=harness_grants, prepare=lambda installed: None, finish=lambda: None)
    quests.acceptance = acceptance
    s.run(argparse.Namespace(m3b=False, m3a=False, m2=False, m1=False, integration=False, live=False, serve=False, record=False,
                             visible=False, quests=True, long_titles=True))
