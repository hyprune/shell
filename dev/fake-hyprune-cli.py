#!/usr/bin/env python3
"""A fake `hyprune` CLI for the Director Library page (RFC-0015 phase 1), development only.

Speaks the CLI JSON contract the page depends on: listing documents for `source list`,
`browse` and `content list` (alias `installed`), and JSON lines for jobs (`install`, `add`,
`update`, `rollback`, `pin`, `unpin`, `remove`, `source add|refresh|enable|disable|remove`)
with `--plan`, `--yes` and `--accept-source-change`. No network, no packages: the sources,
entries and installs below are fixtures kept in a state file so actions persist between runs.

    HYPRUNE_CLI="python3 dev/fake-hyprune-cli.py" ./dev/run library

Environment:
  HYPRUNE_FAKE_CLI_STATE  state directory (default $XDG_RUNTIME_DIR/hyprune-fake-cli, else /tmp)
  HYPRUNE_FAKE_CLI_DELAY  seconds per progress step (default 0.25; 0 for tests)
A file `hold` in the state directory naming a stage (or `progress`, half way through the
download) makes jobs wait there until the file is removed (at most 600 s): stills of a running job.
`reset` restores the fixtures. Fixture behaviours: Frank's lamps fails verification
(hash.mismatch); Tidepool from Frank's stuff is a source change (installed from the
community registry); Orbital garden needs a newer Hyprune; the starter library is
system-managed (its plan needs --override; remove refused, managed.system); a source URL
containing "broken" is refused. Shapes follow the SDK CLI (plan packages carry no name).
"""
import json
import os
import pathlib
import sys
import time

STATE_DIR = pathlib.Path(os.environ.get('HYPRUNE_FAKE_CLI_STATE') or
                         pathlib.Path(os.environ.get('XDG_RUNTIME_DIR') or '/tmp') / 'hyprune-fake-cli')
STATE = STATE_DIR / 'state.json'
DELAY = float(os.environ.get('HYPRUNE_FAKE_CLI_DELAY', '0.25'))
NOW = '2026-10-12T08:30:00Z'
MIB = 1024 * 1024


def version(tag, ver, fmt, licence, size, expanded, published, loadable=True, status='available'):
    return {'tag': tag, 'version': ver, 'formatVersion': fmt, 'license': licence, 'bytes': size, 'expandedBytes': expanded,
            'published': published, 'loadable': loadable, 'status': status,
            'sha256': (tag.encode().hex() * 8)[:64].ljust(64, '0')}


def entry(source, id, type, name, summary, creator, repo, tags, versions, thumb=None):
    return {'sourceId': source, 'id': id, 'type': type, 'name': name, 'summary': summary, 'creator': creator, 'repo': repo,
            'tags': tags, 'versions': versions, 'thumb': thumb}


def fixtures():
    sources = [
        {'id': 'official', 'kind': 'official', 'label': 'Official', 'url': 'https://hyprune.github.io/registry/v0.1/official.json',
         'enabled': True, 'builtin': True, 'system': False, 'lastRefresh': '2026-10-12T07:58:11Z', 'serial': 41, 'error': None},
        {'id': 'community', 'kind': 'community', 'label': 'Community registry', 'url': 'https://hyprune.github.io/registry/v0.1/community.json',
         'enabled': True, 'builtin': True, 'system': False, 'lastRefresh': '2026-10-12T07:58:12Z', 'serial': 230, 'error': None},
        {'id': 'franks-stuff', 'kind': 'index', 'label': "Frank's stuff", 'url': 'https://example.org/hyprune/v0.1/index.json',
         'enabled': True, 'builtin': False, 'system': False, 'lastRefresh': '2026-10-11T21:04:40Z', 'serial': 7, 'error': None},
        {'id': 'studio-mirror', 'kind': 'index', 'label': 'Studio mirror', 'url': 'https://mirror.example.net/hyprune/index.json',
         'enabled': False, 'builtin': False, 'system': True, 'lastRefresh': None, 'serial': None, 'error': None},
        {'id': 'ada-worlds', 'kind': 'github', 'label': "Ada's worlds", 'repo': 'ada/tidepool-world',
         'enabled': True, 'builtin': False, 'system': False, 'lastRefresh': '2026-10-12T07:58:13Z', 'serial': None,
         'error': 'fetch.failed: GitHub answered 404 for ada/tidepool-world/releases'},
    ]
    entries = [
        entry('official', 'com.hyprune.lumen-reach', 'world', 'Lumen Reach', 'A coastal observatory town with a lit pier and rooftop paths.',
              'hyprune', 'https://github.com/hyprune/worlds', ['coast', 'town', 'night'],
              [version('lumen-reach-v0.10.0', '0.10.0', '0.7', 'CC-BY-4.0', 61 * MIB, 140 * MIB, '2026-10-11T18:00:00Z'),
               version('lumen-reach-v0.9.1', '0.9.1', '0.7', 'CC-BY-4.0', 58 * MIB, 133 * MIB, '2026-10-08T12:00:00Z')], 'reach'),
        entry('official', 'com.hyprune.street', 'library', 'Street furniture', 'Benches, lamps, bins and signs for paths and plazas.',
              'hyprune', 'https://github.com/hyprune/library-street', ['street', 'lamps', 'benches'],
              [version('v1.2.0', '1.2.0', '0.10', 'CC0-1.0', 3 * MIB + 40000, 7 * MIB, '2026-10-10T09:00:00Z')], 'street'),
        entry('official', 'com.hyprune.starter', 'library', 'Starter objects', 'Desks, shelves, plants and machines for any world.',
              'hyprune', 'https://github.com/hyprune/library-starter', ['starter'],
              [version('v0.1.1', '0.1.1', '0.10', 'CC0-1.0', 9 * MIB, 22 * MIB, '2026-10-12T06:00:00Z')], 'starter'),
        entry('community', 'io.github.ada.tidepool', 'world', 'Tidepool', 'Rock pools and a boardwalk at low tide; four screens in the boathouse.',
              'ada', 'https://github.com/ada/tidepool-world', ['coast', 'water', 'calm'],
              [version('v1.2.0', '1.2.0', '0.7', 'CC-BY-SA-4.0', 46 * MIB, 92 * MIB, '2026-10-09T15:20:00Z'),
               version('v1.1.0', '1.1.0', '0.6', 'CC-BY-SA-4.0', 44 * MIB, 90 * MIB, '2026-09-30T15:20:00Z')], 'tide'),
        entry('community', 'io.github.ben.workshop', 'library', 'Workshop props', 'Workbenches, tool walls and a band saw (decorative).',
              'ben', 'https://github.com/ben/hyprune-objects-workshop', ['workshop', 'tools'],
              [version('v0.4.0', '0.4.0', '0.10', 'CC0-1.0', 5 * MIB, 12 * MIB, '2026-10-05T10:00:00Z')], None),
        entry('community', 'io.github.cy.orbital', 'world', 'Orbital garden', 'A ring station greenhouse with a slow day cycle.',
              'cy', 'https://github.com/cy/hyprune-world-orbital', ['space', 'garden'],
              [version('v2.0.0', '2.0.0', '0.12', 'CC-BY-4.0', 80 * MIB, 190 * MIB, '2026-10-12T05:00:00Z', loadable=False)], 'orbit'),
        entry('franks-stuff', 'io.github.ada.tidepool', 'world', 'Tidepool (Frank\'s remix)', 'Tidepool with a lighthouse added.',
              'frank', 'https://github.com/frank/hyprune-stuff', ['coast'],
              [version('tidepool-v1.2.1', '1.2.1', '0.7', 'CC-BY-SA-4.0', 47 * MIB, 94 * MIB, '2026-10-11T20:00:00Z')], 'tide'),
        entry('franks-stuff', 'org.example.frank.lamps', 'library', "Frank's lamps", 'Twelve hanging lamps.',
              'frank', 'https://github.com/frank/hyprune-stuff', ['lamps'],
              [version('lamps-v0.2.0', '0.2.0', '0.10', 'MIT', 2 * MIB, 4 * MIB, '2026-10-11T20:00:00Z')], None),
    ]
    installs = [
        {'id': 'com.hyprune.lumen-reach', 'type': 'world', 'sourceId': 'official', 'tag': 'lumen-reach-v0.9.1', 'version': '0.9.1',
         'previous': {'tag': 'lumen-reach-v0.9.0', 'version': '0.9.0'}, 'pinned': False, 'managed': 'user', 'license': 'CC-BY-4.0'},
        {'id': 'io.github.ada.tidepool', 'type': 'world', 'sourceId': 'community', 'tag': 'v1.1.0', 'version': '1.1.0',
         'previous': None, 'pinned': True, 'managed': 'user', 'license': 'CC-BY-SA-4.0'},
        {'id': 'com.hyprune.starter', 'type': 'library', 'sourceId': 'system', 'tag': None, 'version': '0.1.0',
         'previous': None, 'pinned': False, 'managed': 'system', 'license': 'CC0-1.0'},
        {'id': 'io.github.dee.lanterns', 'type': 'library', 'sourceId': 'community', 'tag': 'v0.3.0', 'version': '0.3.0',
         'previous': None, 'pinned': False, 'managed': 'user', 'license': 'CC-BY-4.0', 'removedFromSource': True},
    ]
    return {'sources': sources, 'entries': entries, 'installs': installs}


def load():
    if not STATE.exists(): save(fixtures())
    return json.loads(STATE.read_text())


def save(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(state, indent=1))
    tmp.replace(STATE)


def out(value):
    print(json.dumps(value), flush=True)


def display(source):
    if source['kind'] == 'official': return 'Official'
    if source['kind'] == 'community': return 'Community registry'
    return 'Custom: ' + source['label']


def tier(source): return source['kind'] if source['kind'] in ('official', 'community') else 'custom'


def note(source): return {'official': 'reviewed', 'community': 'declared'}.get(source['kind'], 'unchecked')


def source_of(state, sid): return next((s for s in state['sources'] if s['id'] == sid), None)


def newer(a, b):
    def key(v): return tuple(int(x) for x in v.split('-')[0].split('.'))
    return key(a) > key(b)


def thumbnail(name):
    """A plain generated PNG standing in for a verified cached thumbnail (no third-party art)."""
    if not name: return None
    path = STATE_DIR / 'thumbnails' / (name + '.png')
    if path.exists(): return str(path)
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    colours = {'reach': ((22, 44, 70), (240, 200, 110)), 'street': ((40, 46, 52), (150, 200, 220)), 'starter': ((60, 50, 40), (200, 160, 110)),
               'tide': ((20, 70, 80), (120, 220, 200)), 'orbit': ((16, 18, 40), (170, 150, 240))}
    back, fore = colours.get(name, ((40, 40, 40), (200, 200, 200)))
    image = Image.new('RGB', (480, 270), back)
    draw = ImageDraw.Draw(image)
    if name == 'reach': draw.rectangle((0, 190, 480, 270), fill=(14, 30, 48)); [draw.ellipse((40 + i * 70, 150, 60 + i * 70, 170), fill=fore) for i in range(6)]
    elif name == 'tide': [draw.ellipse((60 + i * 90, 160 - i * 12, 150 + i * 90, 210 - i * 12), outline=fore, width=5) for i in range(4)]
    elif name == 'orbit': draw.ellipse((140, 35, 340, 235), outline=fore, width=12); draw.ellipse((215, 110, 265, 160), fill=fore)
    elif name == 'street': draw.rectangle((230, 60, 244, 230), fill=fore); draw.ellipse((205, 30, 270, 90), fill=(250, 220, 140))
    else: [draw.rectangle((60 + i * 100, 110, 130 + i * 100, 220), fill=fore) for i in range(4)]
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return str(path)


def installed_record(state, id): return next((i for i in state['installs'] if i['id'] == id), None)


def browse_doc(state, text, type_, source_id):
    words = text.lower().split()
    entries = []
    for e in state['entries']:
        source = source_of(state, e['sourceId'])
        if not source or not source['enabled']: continue
        if type_ and e['type'] != type_: continue
        if source_id and e['sourceId'] != source_id: continue
        hay = ' '.join([e['name'], e['summary']] + e['tags']).lower()
        if any(w not in hay for w in words): continue
        latest = dict(e['versions'][0]); latest.pop('sha256', None); latest.update(prerelease=False, requires=[])
        record = installed_record(state, e['id'])
        if record and record['managed'] == 'system': record = None  # system content has no install record
        installed = {'tag': record['tag'], 'sourceId': record['sourceId']} if record else None
        update = None
        if record and record['sourceId'] == e['sourceId']:
            best = next((v for v in e['versions'] if v['loadable'] and v['status'] == 'available'), None)
            if best and newer(best['version'], record['version']): update = best['tag']
        entries.append({'sourceId': e['sourceId'], 'display': display(source), 'tier': tier(source), 'id': e['id'], 'type': e['type'],
                        'name': e['name'], 'summary': e['summary'], 'creator': e['creator'], 'repo': e['repo'], 'tags': e['tags'],
                        'latest': latest, 'licenceNote': note(source), 'thumbnail': thumbnail(e['thumb']), 'installed': installed,
                        'update': update, 'versions': [{k: v[k] for k in ('tag', 'version', 'formatVersion', 'status', 'loadable')} for v in e['versions']]})
    order = {'official': 0, 'community': 1, 'custom': 2}
    entries.sort(key=lambda x: (order[x['tier']], x['name'].lower()))
    return {'entries': entries}


def content_doc(state):
    installs = []
    for r in state['installs']:
        source = source_of(state, r['sourceId'])
        newer_tag = None
        if source and source['enabled']:
            e = next((x for x in state['entries'] if x['id'] == r['id'] and x['sourceId'] == r['sourceId']), None)
            best = next((v for v in e['versions'] if v['loadable'] and v['status'] == 'available'), None) if e else None
            if best and newer(best['version'], r['version']): newer_tag = best['tag']
        installs.append({'id': r['id'], 'type': r['type'], 'sourceId': r['sourceId'], 'display': display(source) if source else r['sourceId'].capitalize(),
                         'tag': r['tag'], 'version': r['version'], 'previous': r['previous'], 'pinned': r['pinned'], 'managed': r['managed'],
                         'removedFromSource': bool(r.get('removedFromSource')), 'newerTag': newer_tag, 'license': r['license'],
                         'path': str(STATE_DIR / ('worlds' if r['type'] == 'world' else 'libraries') / (r['id'] if r['type'] == 'world' else r['id'] + '@' + r['version']))})
    return {'installs': installs}


def sources_doc(state):
    result = []
    for s in state['sources']:
        row = dict(s)
        row['display'] = display(s)
        row['entries'] = sum(1 for e in state['entries'] if e['sourceId'] == s['id'])
        result.append(row)
    return {'sources': result}


def fail(rule, message, code=3):
    out({'event': 'error', 'error': {'rule': rule, 'message': message}})
    sys.exit(code)


def pause(stage):
    hold, end = STATE_DIR / 'hold', time.monotonic() + 600
    while hold.exists() and hold.read_text().strip() == stage and time.monotonic() < end: time.sleep(.1)


def stage(name):
    out({'event': 'stage', 'stage': name})
    pause(name)
    time.sleep(DELAY)


def resolve(state, target, source_id):
    tag = None
    if '@' in target: target, tag = target.split('@', 1)
    candidates = [e for e in state['entries'] if e['id'] == target and (not source_id or e['sourceId'] == source_id)
                  and source_of(state, e['sourceId'])['enabled']]
    if not candidates: fail('not.found', f'No enabled source lists {target}.')
    e = candidates[0]
    versions = [v for v in e['versions'] if (tag is None or v['tag'] == tag)]
    best = next((v for v in versions if v['loadable'] and v['status'] == 'available'), None)
    if not best:
        fail('format.unsupported', f"{e['name']} {versions[0]['tag'] if versions else tag or ''} needs a newer Hyprune (world format {e['versions'][0]['formatVersion']}).".replace('  ', ' '))
    return e, best


def plan_for(state, e, v, kind):
    source = source_of(state, e['sourceId'])
    record = installed_record(state, e['id'])
    change, override = None, bool(record and record['managed'] == 'system')
    if override: record = None
    if record and record['sourceId'] != e['sourceId']:
        old = source_of(state, record['sourceId']) if record['sourceId'] else None
        change = {'id': e['id'], 'from': {'sourceId': record['sourceId'], 'display': display(old) if old else 'system'},
                  'to': {'sourceId': e['sourceId'], 'display': display(source)}}
    action = 'install' if not record else 'update' if newer(v['version'], record['version'] or '0.0.0') else 'downgrade' if record['version'] and newer(record['version'], v['version']) else 'install'
    # The SDK's plan package (no name: the shell shows the entry's).
    package = {'id': e['id'], 'type': e['type'], 'tag': v['tag'], 'version': v['version'], 'formatVersion': v['formatVersion'],
               'replaces': record['tag'] if record and record['tag'] else None, 'sourceId': e['sourceId'], 'sourceLabel': display(source),
               'creator': e['creator'], 'repo': e['repo'], 'license': v['license'], 'licenceNote': note(source), 'bytes': v['bytes'],
               'expandedBytes': v['expandedBytes'], 'sha256': v['sha256'], 'url': asset(e, v), 'action': action, 'requires': []}
    packages = [package]
    if e['type'] == 'world' and e['id'] == 'com.hyprune.lumen-reach':
        street = next(x for x in state['entries'] if x['id'] == 'com.hyprune.street')
        sv = street['versions'][0]
        package['requires'] = [street['id'] + '@' + sv['version']]
        packages.append({'id': street['id'], 'type': 'library', 'tag': sv['tag'], 'version': sv['version'], 'formatVersion': sv['formatVersion'],
                         'replaces': None, 'sourceId': 'official', 'sourceLabel': 'Official', 'creator': 'hyprune', 'repo': street['repo'],
                         'license': sv['license'], 'licenceNote': 'reviewed', 'bytes': sv['bytes'], 'expandedBytes': sv['expandedBytes'],
                         'sha256': sv['sha256'], 'url': asset(street, sv), 'requires': [],
                         'action': 'already-installed' if installed_record(state, street['id']) else 'install'})
    return {'packages': packages, 'sourceChange': change, 'override': override, 'diskFreeAfter': 182536110080}


def asset(e, v):
    return e['repo'] + '/releases/download/' + v['tag'] + '/' + e['id'] + '-' + v['version'] + '.tar.zst'


def install_job(state, kind, target, flags):
    stage('resolving')
    if kind == 'update':
        record = installed_record(state, target)
        if not record: fail('not.found', f'{target} is not installed.')
        if record['managed'] == 'system': fail('managed.system', f'{target} is managed by the system configuration; change it there.')
        e, v = resolve(state, target, record['sourceId'])
    else:
        e, v = resolve(state, target, flags.get('--from'))
    plan = plan_for(state, e, v, kind)
    out({'event': 'plan', 'plan': plan})
    if '--plan' in flags: return 0
    if plan['sourceChange'] and '--accept-source-change' not in flags:
        fail('source.change', f"{e['id']} is installed from {plan['sourceChange']['from']['display']}; installing it from "
                              f"{plan['sourceChange']['to']['display']} needs --accept-source-change.")
    if plan['override'] and '--override' not in flags:
        fail('managed.system', f"{e['id']} is managed by the system configuration; installing your own copy needs --override.")
    if '--yes' not in flags: fail('confirm.required', 'Confirm the plan with --yes.')
    total = v['bytes']
    stage('downloading')
    for i in range(1, 9):
        out({'event': 'progress', 'bytes': total * i // 8, 'total': total})
        if i == 4: pause('progress')
        time.sleep(DELAY)
    stage('verifying')
    if e['id'] == 'org.example.frank.lamps':
        fail('hash.mismatch', f"The download of {e['id']} {v['tag']} doesn't match its pinned sha256; the cached file was deleted.", 1)
    stage('extracting')
    stage('validating')
    stage('committing')
    record = installed_record(state, e['id'])
    previous = {'tag': record['tag'], 'version': record['version']} if record and record['tag'] else None
    state['installs'] = [r for r in state['installs'] if r['id'] != e['id']]
    state['installs'].append({'id': e['id'], 'type': e['type'], 'sourceId': e['sourceId'], 'tag': v['tag'], 'version': v['version'],
                              'previous': previous, 'pinned': '--pin' in flags, 'managed': 'user', 'license': v['license']})
    save(state)
    out({'event': 'done', 'result': {'id': e['id'], 'type': e['type'], 'tag': v['tag'], 'version': v['version'],
                                     'action': plan['packages'][0]['action']}})
    return 0


def simple_job(state, kind, target, flags):
    record = installed_record(state, target)
    if not record: fail('not.found', f'{target} is not installed.')
    if record['managed'] == 'system': fail('managed.system', f'{target} is managed by the system configuration; change it there.')
    stage('committing')
    if kind == 'rollback':
        if not record['previous']: fail('not.found', f'{target} has no previous install to roll back to.')
        current = {'tag': record['tag'], 'version': record['version']}
        record['tag'], record['version'] = record['previous']['tag'], record['previous']['version']
        record['previous'] = current
        record['pinned'] = True
    elif kind in ('pin', 'unpin'):
        record['pinned'] = kind == 'pin'
    elif kind == 'remove':
        if '--yes' not in flags: fail('confirm.required', 'Confirm the removal with --yes.')
        state['installs'] = [r for r in state['installs'] if r['id'] != target]
    save(state)
    out({'event': 'done', 'result': {'id': record['id'], 'type': record['type'], 'tag': record['tag'], 'version': record['version'], 'action': kind}})
    return 0


def source_job(state, verb, args, flags):
    if verb == 'list':
        out(sources_doc(state)); return 0
    if verb == 'add':
        if not args: fail('source.invalid', 'Give a URL or github:owner/repo.', 2)
        url = args[0]
        stage('resolving')
        if 'broken' in url: fail('source.invalid', f'{url} is not an index in the v0.1 format: entries[0].id is missing.')
        if url.endswith('.tar.zst') and not flags.get('--sha256'): fail('source.invalid', 'A package URL needs --sha256.', 2)
        github = url.startswith('github:')
        label = flags.get('--label') or (url[7:] if github else url.split('/')[2])
        sid = flags.get('--id') or ''.join(c if c.isalnum() else '-' for c in label.lower()).strip('-')[:32]
        if source_of(state, sid): fail('source.invalid', f'A source with the id {sid} already exists.')
        source = {'id': sid, 'kind': 'github' if github else 'url' if url.endswith('.tar.zst') else 'index', 'label': label,
                  'enabled': True, 'builtin': False, 'system': False, 'lastRefresh': NOW, 'serial': None, 'error': None}
        source['repo' if github else 'url'] = url[7:] if github else url
        state['sources'].append(source)
        save(state)
        out({'event': 'done', 'result': {**source, 'display': display(source), 'entries': 0, 'skipped': []}}); return 0
    if verb == 'refresh':
        ids = args or [s['id'] for s in state['sources'] if s['enabled']]
        stage('resolving')
        for s in state['sources']:
            if s['id'] in ids and s['id'] != 'ada-worlds': s['lastRefresh'] = NOW; s['error'] = None
        save(state)
        out({'event': 'done', 'result': {'action': 'source.refresh', 'ids': ids}}); return 0
    if verb in ('enable', 'disable', 'remove'):
        s = source_of(state, args[0] if args else '')
        if not s: fail('not.found', f'No source {args[0] if args else ""}.')
        if verb == 'remove' and (s['builtin'] or s['system']):
            fail('source.invalid', 'Built-in and system sources can\'t be removed; disable them instead.')
        if verb == 'remove': state['sources'] = [x for x in state['sources'] if x['id'] != s['id']]
        else: s['enabled'] = verb == 'enable'
        save(state)
        out({'event': 'done', 'result': {'id': s['id'], 'action': 'source.' + verb}}); return 0
    print(f'hyprune: unknown source command {verb}', file=sys.stderr); return 2


def main(argv):
    if argv[:1] == ['reset']:
        save(fixtures()); return 0
    words, flags, i = [], {}, 0
    while i < len(argv):
        a = argv[i]
        if a in ('--from', '--type', '--source', '--label', '--id', '--sha256'):
            flags[a] = argv[i + 1] if i + 1 < len(argv) else ''; i += 2; continue
        if a.startswith('--'): flags[a] = True
        else: words.append(a)
        i += 1
    if '--json' not in flags:
        print('hyprune (fake): only --json is implemented', file=sys.stderr); return 2
    state = load()
    if words and words[0] in ('world', 'library'): words = words[1:]  # hyprune world|library <verb> ...
    verb, args = (words[0], words[1:]) if words else ('', [])
    if verb in ('source', 'sources'):
        return source_job(state, args[0] if args else 'list', args[1:], flags)
    if verb == 'browse':
        if '--refresh' in flags: source_job(state, 'refresh', [], {})
        out(browse_doc(state, ' '.join(args), flags.get('--type'), flags.get('--source'))); return 0
    if verb in ('installed', 'list') or (verb == 'content' and args[:1] == ['list']):
        out(content_doc(state)); return 0
    if verb in ('install', 'add', 'update'):
        if not args: fail('not.found', 'Give an id.', 2)
        return install_job(state, 'update' if verb == 'update' else 'install', args[0], flags)
    if verb in ('rollback', 'pin', 'unpin', 'remove'):
        if not args: fail('not.found', 'Give an id.', 2)
        return simple_job(state, verb, args[0], flags)
    print(f'hyprune (fake): unknown command {verb}', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
