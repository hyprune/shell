#!/usr/bin/env python3
"""IPC 0.21 (RFC-0012) captures: the Director Quests page and personal quest form,
Settings > Guidance, the HUD quest tracker, focus timer chip, toasts and banner.

Launched only by dev/run's validated nested lifetime: dev/run quests
The SDK mock speaks IPC 0.2, so 0.21 state (markers, quests, focus), methods, results
and events come from the dev-only statePreview / questPreview / questEvent hooks
(ShellState.dev); preview-only actions are recorded, never sent.
Stills go to HYPRUNE_QUESTS_SHOTS (default dev/.run/quests).
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
SHOTS = pathlib.Path(os.environ.get('HYPRUNE_QUESTS_SHOTS', ROOT / 'dev/.run/quests'))
shutil.rmtree(SHOTS, ignore_errors=True); SHOTS.mkdir(parents=True)
METHODS = ','.join(['markers.reveal', 'guidance.get', 'guidance.set', 'quests.list', 'quests.get', 'quests.track', 'quests.accept',
                    'quests.abandon', 'quests.resume', 'quests.create', 'quests.update', 'quests.delete', 'quests.mark',
                    'focus.start', 'focus.pause', 'focus.resume', 'focus.skip', 'focus.stop', 'focus.history'])


def call(*args): return subprocess.check_output(args, text=True).strip()
def ui(*args): return call('qs', 'ipc', '--pid', pid, 'call', 'preview', *map(str, args))
def ctl(code): return call('hyprctl', '-i', session['HYPRLAND_INSTANCE_SIGNATURE'], 'eval', code)
def status(): return json.loads(ui('status'))


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
        call('grim', '-o', 'HYPRUNE-PREVIEW', str(SHOTS / ('FAILED-' + name + '.png')))
    assert audit['labels'] > 0 and not audit['failures'], (name, audit)
    call('grim', '-o', 'HYPRUNE-PREVIEW', str(SHOTS / (name + '.png')))
    taken.append(name)


def ref(id): return {'source': 'personal', 'id': id}


def summary(id, title, state, tracked=False, step=None, progress=(0, 1), updated='2026-10-12T10:00', off=False):
    return {'questRef': ref(id), 'title': title, 'category': 'personal', 'state': state, 'tracked': tracked, 'step': step,
            'progress': list(progress), 'offWorld': off, 'updatedAt': updated}


def objective(id, type, label, done=0, **extra):
    return {'id': id, 'type': type, 'label': label, 'count': 1, 'done': done, **extra}


def step(id, title, state, objectives, target=None):
    return {'id': id, 'title': title, 'optional': False, 'any': False, 'state': state, 'target': target, 'objectives': objectives}


def detail(id, title, state, steps, tracked=False, summary_text=''):
    return {'questRef': ref(id), 'title': title, 'summary': summary_text, 'category': 'personal', 'state': state, 'tracked': tracked,
            'sequential': True, 'expires': None, 'createdAt': '2026-10-10T09:00', 'updatedAt': '2026-10-12T10:00',
            'completedAt': None, 'personal': True, 'steps': steps}


NOTES = detail('release-notes', 'Write the release notes', 'active', [
    step('draft', 'Draft the changes list', 'done', [objective('done', 'manual', 'Done', 1)]),
    step('write', 'Write it up at the workshop', 'current',
         [objective('focus', 'focus', '2 focus sessions', 1, sessions=2, creditedMinutes=23.5), objective('done', 'manual', 'Done')],
         target={'zoneId': 'work'}),
    step('review', 'Ask for a review', 'pending', [objective('done', 'manual', 'Done')]),
    step('publish', 'Publish', 'pending', [objective('done', 'manual', 'Done')], target={'workspaceId': 3})],
    tracked=True, summary_text='Everything that changed since the last release, in plain words.')
TAXES = detail('tax-return', 'File the tax return', 'active', [
    step('gather', 'Gather the receipts', 'current', [objective('done', 'manual', 'Done')]),
    step('fill', 'Fill in the forms', 'pending', [objective('focus', 'focus', '3 focus sessions', 0, sessions=3)])])
LIST = [summary('release-notes', NOTES['title'], 'active', True, {'id': 'write', 'title': 'Write it up at the workshop', 'progress': [1, 2]}, (1, 4)),
        summary('tax-return', TAXES['title'], 'active', False, {'id': 'gather', 'title': 'Gather the receipts', 'progress': [0, 1]}, (0, 2), '2026-10-11T08:00'),
        summary('garden', 'Repot the garden plants', 'active', False, {'id': 'pots', 'title': 'Buy pots', 'progress': [0, 1]}, (0, 3), '2026-10-09T08:00', True),
        summary('reading', 'Read the networking book', 'available', False, None, (0, 5)),
        summary('backup', 'Set up backups', 'completed', False, None, (2, 2)),
        summary('bike', 'Fix the bike', 'abandoned', False, {'id': 'tube', 'title': 'New inner tube', 'progress': [0, 1]}, (0, 2))]
GUIDANCE = {
    'config': {'markers.reveal_ms': 4000, 'markers.reveal_mode': 'timer', 'markers.max_revealed': 12, 'markers.labels': 5,
               'markers.persistent': 'edge', 'markers.core_draw': True, 'quests.notifications': 'all', 'focus.work_min': 25,
               'focus.short_break_min': 5, 'focus.long_break_min': 15, 'focus.long_break_every': 4, 'focus.cycles': 4,
               'focus.auto_start_breaks': True, 'focus.auto_start_work': False, 'focus.count_mode': 'focus', 'focus.idle_s': 180,
               'focus.grace_s': 30, 'focus.calm': True, 'focus.calm_npc_distance': 6, 'focus.desktop_chip': False, 'focus.history_days': 90},
    'ranges': {'markers.reveal_ms': [1000, 15000], 'markers.max_revealed': [4, 16], 'markers.labels': [2, 8], 'focus.work_min': [5, 120],
               'focus.short_break_min': [1, 30], 'focus.long_break_min': [5, 60], 'focus.long_break_every': [2, 12], 'focus.cycles': [1, 12],
               'focus.idle_s': [60, 900], 'focus.grace_s': [0, 120], 'focus.calm_npc_distance': [2, 20], 'focus.history_days': [0, 365]},
    'options': {'markers.reveal_mode': ['timer', 'toggle'], 'markers.persistent': ['off', 'edge', 'always'],
                'quests.notifications': ['all', 'important', 'off'], 'focus.count_mode': ['focus', 'wall']},
    'path': '~/.config/hyprune/guidance.json', 'error': ''}
GUIDANCE['defaults'] = dict(GUIDANCE['config'])
GUIDANCE['overrides'] = {}
GUIDANCE['config'] = {**GUIDANCE['config'], 'focus.work_min': 50, 'focus.short_break_min': 10}
GUIDANCE['overrides'] = {'focus.work_min': 50, 'focus.short_break_min': 10}
QUESTS = {'enabled': True, 'tracked': ref('release-notes'), 'counts': {'available': 1, 'active': 3, 'completed': 1}, 'world': None,
          'active': [{'id': 'release-notes', 'source': 'personal', 'title': NOTES['title'],
                      'step': {'id': 'write', 'title': 'Write it up at the workshop', 'progress': [1, 2]}, 'progress': [1, 4]}]}
MARKERS = {'reveal': None, 'persistent': 'edge', 'calm': False, 'coreDraw': True, 'list': [
    {'id': 'quest:personal/release-notes/write/focus', 'kind': 'quest', 'tier': 1, 'label': 'Write it up', 'icon': 'quest',
     'target': {'zoneId': 'work'}, 'position': [0, 1.7, -2.5], 'areaId': None, 'range': [2, 400], 'labelRange': 120,
     'occlusion': 'through', 'tracked': True, 'source': {'questId': 'personal/release-notes', 'stepId': 'write', 'objectiveId': 'focus'}}]}


def focus_state(state='work', remaining=17 * 60_000 + 42_000, phase=25 * 60_000, credited=6 * 60_000, cycle=2, cycles=4,
                break_kind=None, calm=False):
    now = float(ui('monotonicNow'))
    running = state in ('work', 'break')
    return {'state': state, 'pausedState': 'work' if state == 'paused' else None, 'sessionId': 'focus-5eed',
            'phaseStartedAtMs': int(now - (phase - remaining)) if running else None, 'phaseEndsAtMs': int(now + remaining) if running else None,
            'phaseMs': phase, 'remainingMs': remaining, 'creditedMs': credited, 'crediting': state == 'work', 'cycle': cycle,
            'cycles': cycles, 'breakKind': break_kind, 'countMode': 'focus',
            'target': {'kind': 'any', 'label': 'Any window', 'questRef': ref('release-notes')}, 'calm': calm}


def preview(focus=None, quests=QUESTS, extra=None):
    patch = {'markers': MARKERS, 'quests': quests, 'focus': focus or focus_state('idle', 0, 0, 0, 0)}
    patch.update(extra or {})
    ui('statePreview', json.dumps(patch), METHODS); time.sleep(.4)


def event(method, params):
    ui('questEvent', method, json.dumps({**params, 'sessionId': 'mock', 'revision': 1}))


time.sleep(2)
assert status()['lease']
ctl('hl.dispatch(hl.dsp.cursor.move({x=40,y=40}))')  # park the nested software cursor
ui('questPreview', json.dumps({'list': LIST, 'details': {'personal/release-notes': NOTES, 'personal/tax-return': TAXES}, 'guidance': GUIDANCE}))
for w, h, scale, suffix in [(1920, 1080, 1, ''), (1280, 720, 1, '-720p'), (2560, 1440, 2, '-1440p-s2')]:
    ctl(f'hl.monitor({{output="HYPRUNE-PREVIEW",mode="{w}x{h}@60",position="1280x0",scale={scale}}})')
    time.sleep(1.2)
    ui('close'); time.sleep(.4)
    # HUD: tracker and a running work interval with credit.
    preview(focus_state())
    wait(lambda: status()['quests']['guidance'] is not None)  # guidance.get on connect
    shot('hud-tracker-focus-work' + suffix)
    if suffix:  # smaller logical viewports: the page and the form must still fit
        ui('open'); time.sleep(.8); ui('tabNamed', 'quests')
        wait(lambda: status()['quests']['list'] == len(LIST))
        ui('questSelect', 'personal/release-notes')
        wait(lambda: status()['quests']['detail'] == NOTES['title'])
        shot('quests-page' + suffix)
        ui('questForm', json.dumps({'edit': True})); shot('quests-form-edit' + suffix)
        assert ui('press', 'quest-form-cancel') == 'true'
        ui('tabNamed', 'settings'); ui('settingsSection', 5); shot('settings-guidance' + suffix)
        ui('close'); time.sleep(.5)
        continue
    event('quest.progress', {'questRef': ref('release-notes'), 'kind': 'step', 'title': NOTES['title'], 'stepId': 'draft',
                             'stepTitle': 'Draft the changes list', 'nextStepTitle': 'Write it up at the workshop'})
    shot('hud-toast-step-done')
    event('quest.progress', {'questRef': ref('backup'), 'kind': 'completed', 'title': 'Set up backups'})
    shot('hud-banner-quest-complete')
    time.sleep(5)
    # Break: chip in the break colour, suggestion toast; cycle dots show interval 2 done.
    preview(focus_state('break', 3 * 60_000 + 12_000, 5 * 60_000, 23 * 60_000, break_kind='short'))
    event('focus.phase', {'focusSessionId': 'focus-5eed', 'phase': 'break', 'cycle': 2, 'cycles': 4, 'creditedMs': 23 * 60_000,
                          'breakKind': 'short', 'suggestion': {'markerId': 'break:lookout', 'label': 'the north lookout'}})
    shot('hud-focus-break-suggestion')
    time.sleep(4.5)
    # Calm work interval: tracker on one line; a step toast waits for the break.
    preview(focus_state(calm=True, cycle=3))
    event('quest.progress', {'questRef': ref('tax-return'), 'kind': 'step', 'title': TAXES['title'], 'stepId': 'gather',
                             'stepTitle': 'Gather the receipts'})
    assert status()['quests']['deferred'] == 1 and not status()['quests']['toasts'], status()['quests']
    shot('hud-calm-tracker-one-line')
    preview(focus_state('break', 4 * 60_000, 5 * 60_000, 25 * 60_000, cycle=3, break_kind='short'))
    wait(lambda: status()['quests']['toasts'])
    shot('hud-calm-deferred-toast-at-break')
    time.sleep(3.5)
    preview(focus_state('paused', 9 * 60_000, 25 * 60_000, 11 * 60_000, cycle=3))
    ui('motion', 'true'); shot('hud-focus-paused-reduced-motion'); ui('motion', 'false')
    preview(focus_state(cycles=12, cycle=7, remaining=95 * 60_000, phase=120 * 60_000))
    shot('hud-focus-long-session')
    ui('theme', 'true'); shot('hud-focus-paper'); ui('theme', 'false')

    # Director > Quests.
    preview(focus_state())
    ui('open'); time.sleep(.8)
    assert status()['director']
    ui('tabNamed', 'quests')
    wait(lambda: status()['quests']['list'] == len(LIST))
    ui('questSelect', 'personal/release-notes')
    wait(lambda: status()['quests']['detail'] == NOTES['title'])
    shot('quests-page')
    # Keyboard: Down/Up move the selection through the list, T asks to track.
    call('wtype', '-k', 'Down'); wait(lambda: status()['quests']['selected'] == 'personal/tax-return')
    call('wtype', '-k', 'Up'); wait(lambda: status()['quests']['selected'] == 'personal/release-notes')
    wait(lambda: status()['quests']['detail'] == NOTES['title'])
    call('wtype', 't'); time.sleep(.3)
    track = [a for a in status()['previewActions'] if a['method'] == 'quests.track']
    assert track and track[-1]['params'] == {'questRef': None}, track  # tracked: T untracks
    ui('scrollPage', 1); shot('quests-page-steps-end'); ui('scrollPage', 0)
    ui('theme', 'true'); shot('quests-page-paper'); ui('theme', 'false')
    ui('questSelect', 'personal/tax-return')
    wait(lambda: status()['quests']['detail'] == TAXES['title'])
    shot('quests-page-second-quest')
    assert ui('press', 'quest-map-write') == 'false'  # not visible for this quest
    ui('questSelect', 'personal/release-notes')
    wait(lambda: status()['quests']['detail'] == NOTES['title'])
    assert ui('press', 'quest-waypoint-write') == 'true'
    assert ui('press', 'quest-start-focus-write') == 'false'  # a session is running: disabled
    assert ui('press', 'focus-pause') == 'true'
    actions = [a['method'] for a in status()['previewActions']]
    assert 'focus.pause' in actions, actions
    ui('questForm', json.dumps({'title': 'Plan the trip', 'summary': 'Three days by the sea',
                                'steps': 'Book the train\nFind a place to stay\nPack', 'targetKind': 'workspace', 'targetValue': '3',
                                'sessions': {'Find a place to stay': 2}}))
    shot('quests-form-new')
    ui('questForm', json.dumps({'edit': True}))
    shot('quests-form-edit')
    assert ui('press', 'quest-form-save') == 'true'
    actions = status()['previewActions']
    update = next(a for a in reversed(actions) if a['method'] == 'quests.update')
    assert [s['id'] for s in update['params']['quest']['steps']] == ['draft', 'write', 'review', 'publish'], update
    assert ui('press', 'quest-form-cancel') == 'true'
    preview(focus_state('idle', 0, 0, 0, 0))
    shot('quests-page-focus-idle')
    if ui('press', 'quest-map-write') == 'true':
        wait(lambda: status()['tabName'] == 'map')
        shot('map-quest-focus')
        ui('tabNamed', 'quests')
    # Settings > Guidance.
    ui('tabNamed', 'settings'); ui('settingsSection', 5); time.sleep(.5)
    shot('settings-guidance')
    ui('settingsScroll', 1); shot('settings-guidance-end'); ui('settingsScroll', 0)
    ui('close'); time.sleep(.5)
    # Desktop (world not active): the chip only with focus.desktop_chip.
    preview(focus_state(), extra={'runtime': {'active': False, 'outputs': ['output-main']}})
    ui('questPreview', json.dumps({'list': LIST, 'details': {'personal/release-notes': NOTES}, 'guidance': {**GUIDANCE, 'config': {**GUIDANCE['config'], 'focus.desktop_chip': True}}}))
    ui('statePreview', json.dumps({'markers': MARKERS, 'quests': QUESTS, 'focus': focus_state(), 'runtime': {'active': False, 'outputs': ['output-main']}}), METHODS)
    time.sleep(1)
    call('grim', '-o', 'HYPRUNE-PREVIEW', str(SHOTS / 'desktop-focus-chip.png')); taken.append('desktop-focus-chip')

ui('statePreview', '', ''); ui('questPreview', '')
logs = (ROOT / 'dev/.run/shell.log').read_text()
assert not any(x in logs for x in ['ReferenceError', 'TypeError', 'Binding loop', 'Unable to assign']), logs[-3000:]
print('PASS quests captures:', ', '.join(taken), '->', SHOTS)
