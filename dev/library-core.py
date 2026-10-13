#!/usr/bin/env python3
"""RFC-0015 phase 1, real run: the Library tab with the hyprune CLI against a nested core.

Nested only, inside core's harness. On a host without a parent session:
  HYPRUNE_NESTED_STATE_ROOT=$(mktemp -d) HYPRUNE_CORE_DIR=<core checkout, built> \\
  HYPRUNE_LIBRARY_WORLD=<a world package directory> HYPRUNE_LIBRARY_ARCHIVE=<library .tar.zst> \\
  HYPRUNE_CLI="node <sdk>/dist/src/cli.js" python3 $CORE/dev/nested/isolated.py dev/library-core.py
A loopback HTTP server stands in for the official index (HYPRUNE_REGISTRY_OFFICIAL_URL and
HYPRUNE_REGISTRY_COMMUNITY_URL with HYPRUNE_FETCH_ALLOW_LOOPBACK_HTTP=1, a test-only switch):
one library entry for the archive, with a generated thumbnail. Core and the CLI share a
private XDG_DATA_HOME; the CLI's state, config and cache homes are private too.

Checks (each reported PASS/FAIL; the run fails if any fails): the shell negotiates IPC 0.24
with objects.control; Refresh sources lists the entry with its verified cached thumbnail;
Install shows the plan; confirming installs it (stages to done); core's object catalog lists
the library's objects (Objects > Catalog, Library filter); Installed lists it; Remove removes
it and the catalog drops it; no QML runtime errors. Stills go to HYPRUNE_LIBRARY_CORE_SHOTS
(default dev/.run/library-core).
"""
import argparse, hashlib, http.server, io, json, os, pathlib, shutil, subprocess, sys, tarfile, threading, time
ROOT = pathlib.Path(__file__).resolve().parent.parent
CORE = pathlib.Path(os.environ.get('HYPRUNE_CORE_DIR', str(ROOT.parent / 'core')))
sys.path.insert(0, str(CORE / 'dev/nested'))
import session as s  # noqa: E402
import catalog  # noqa: E402
from ctl import verified  # noqa: E402
from m2 import wait, keys  # noqa: E402
SHOTS = pathlib.Path(os.environ.get('HYPRUNE_LIBRARY_CORE_SHOTS', str(ROOT / 'dev/.run/library-core')))
WORLD_DIR = pathlib.Path(os.environ.get('HYPRUNE_LIBRARY_WORLD', str(ROOT.parent / 'worlds/dist/com.hyprune.lumen-reach')))
ARCHIVE = pathlib.Path(os.environ['HYPRUNE_LIBRARY_ARCHIVE'])
CLI = os.environ.get('HYPRUNE_CLI', '')
WORLD_ID = json.loads((WORLD_DIR / 'world.json').read_text())['id']


def library_manifest(archive):
    """id, version, formatVersion, name, files and expanded bytes of a library archive."""
    raw = subprocess.check_output(['zstd', '-dc', str(archive)])
    files = expanded = 0
    manifest = None
    with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
        for m in tar.getmembers():
            if m.isfile():
                files += 1; expanded += m.size
                if m.name.count('/') == 1 and m.name.endswith('/library.json'): manifest = json.load(tar.extractfile(m))
    return manifest, files, expanded


class Index:
    """The loopback server: /index/official.json, /index/community.json, /dl/<files>."""

    def __init__(self, base):
        self.base = base; (base / 'index').mkdir(parents=True); (base / 'dl').mkdir()
        handler = lambda *a, **k: http.server.SimpleHTTPRequestHandler(*a, directory=str(base), **k)
        http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f'http://127.0.0.1:{self.server.server_address[1]}'

    def publish(self, archive):
        manifest, files, expanded = library_manifest(archive)
        name = f"{manifest['id']}-{manifest['version']}"
        shutil.copy(archive, self.base / 'dl' / (name + '.tar.zst'))
        from PIL import Image, ImageDraw  # a plain generated thumbnail (no third-party art)
        image = Image.new('RGB', (640, 360), (40, 46, 52)); draw = ImageDraw.Draw(image)
        for i in range(4): draw.rectangle((90 + i * 120, 140, 160 + i * 120, 280), fill=(200, 160, 110))
        thumb = self.base / 'dl' / (name + '.thumb-1.png'); image.save(thumb)
        digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        version = {'tag': 'v' + manifest['version'], 'version': manifest['version'], 'formatVersion': manifest.get('formatVersion', '0.10'),
                   'published': time.strftime('%Y-%m-%d', time.gmtime()), 'license': manifest.get('license') or 'CC0-1.0',
                   'url': f'{self.url}/dl/{name}.tar.zst', 'sha256': digest(archive), 'bytes': archive.stat().st_size,
                   'expandedBytes': expanded, 'files': files, 'status': 'available',
                   'thumbnails': [{'url': f'{self.url}/dl/{thumb.name}', 'sha256': digest(thumb), 'width': 640, 'height': 360}]}
        entry = {'id': manifest['id'], 'type': 'library', 'name': manifest.get('name') or manifest['id'],
                 'summary': 'Desks, shelves, plants and machines for any world.', 'creator': 'hyprune',
                 'repo': 'https://github.com/hyprune/worlds', 'tags': ['starter', 'objects'], 'versions': [version]}
        stamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        (self.base / 'index/official.json').write_text(json.dumps({'indexVersion': '0.1', 'name': 'Official (test)', 'serial': 1, 'generated': stamp, 'entries': [entry]}))
        (self.base / 'index/community.json').write_text(json.dumps({'indexVersion': '0.1', 'name': 'Community (test)', 'serial': 1, 'generated': stamp, 'entries': []}))
        return manifest, version


def prepare(installed):
    shutil.rmtree(installed / WORLD_ID, ignore_errors=True)
    shutil.copytree(WORLD_DIR, installed / WORLD_ID)
    for name in ['editor.json', 'editor.json.v1', 'layout.json', 'input.json']:
        (s.STATE / name).unlink(missing_ok=True)
    # Core and the CLI share the data home (user libraries); core watches its library root.
    shutil.rmtree(s.STATE / 'datahome', ignore_errors=True)
    (s.STATE / 'datahome').mkdir()
    os.environ['XDG_DATA_HOME'] = str(s.STATE / 'datahome')


def acceptance(client, children, args, shell_token, socketpath):
    results = []

    def check(name, ok, data=None):
        results.append({'name': name, 'pass': bool(ok), 'evidence': data})
        print(('PASS' if ok else 'FAIL') + ' library-core: ' + name, json.dumps(data)[:600] if data is not None else '', flush=True)
        return ok

    index = Index(s.STATE / 'registry-server')
    manifest, version = index.publish(ARCHIVE)
    homes = {k: s.STATE / ('cli-' + k) for k in ['state', 'config', 'cache']}
    for d in homes.values(): shutil.rmtree(d, ignore_errors=True); d.mkdir()
    cli_env = {'HYPRUNE_REGISTRY_OFFICIAL_URL': index.url + '/index/official.json', 'HYPRUNE_REGISTRY_COMMUNITY_URL': index.url + '/index/community.json',
               'HYPRUNE_FETCH_ALLOW_LOOPBACK_HTTP': '1', 'XDG_DATA_HOME': os.environ['XDG_DATA_HOME'], 'XDG_STATE_HOME': str(homes['state']),
               'XDG_CONFIG_HOME': str(homes['config']), 'XDG_CACHE_HOME': str(homes['cache']), 'HYPRUNE_WORLD_DIR': str(s.STATE / 'worlds'), 'HYPRUNE_CLI': CLI}

    def cli(*a):
        return json.loads(subprocess.check_output(CLI.split() + list(a), env={**os.environ, **cli_env}, text=True))

    s.ctl('eval', 'hl.dispatch(hl.dsp.focus({ monitor = "HEADLESS-1" }))')
    client.call('world.load', {'worldId': WORLD_ID})
    s.ctl('eval', 'hl.plugin.hyprune.toggle("HEADLESS-1")'); wait(lambda: s.camera()['active'])
    # The harness's catalog lifetime grants the shell token objects.control.
    r, w = os.pipe(); os.write(w, (shell_token + '\n').encode()); os.close(w)
    _, env = verified()
    env.update(cli_env)
    env.update(HYPRUNE_TOKEN_FD=str(r), HYPRUNE_PROTOCOL='0.24', HYPRUNE_SOCKET=str(socketpath), HYPRUNE_OUTPUT_SCREEN='HEADLESS-1',
               HYPRUNE_DEV_AUTOMATION='1', HYPRUNE_SHELL_PREFERENCES=str(s.STATE / 'shell-preferences.json'))
    log = open(s.STATE / 'shell.log', 'w')
    shell = subprocess.Popen(['python3', str(ROOT / 'bridge/launch.py'), '--protocol', '0.24'], env=env, pass_fds=(r,), stdout=log, stderr=subprocess.STDOUT)
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

    def library(): return status().get('library') or {}
    def job(): return library().get('job') or {}

    def shot(name):
        time.sleep(.8)
        subprocess.run([str(s.HERE / 'ctl.py'), 'shot', str(SHOTS / (name + '.png'))], check=True)

    def press(name): return ui('press', name) == 'true'
    def park(): s.ctl('eval', 'hl.dispatch(hl.dsp.cursor.move({x=4,y=4}))')
    def director():
        keys('-P', 'Tab', '-s', '1150', '-p', 'Tab'); wait(lambda: status().get('director'), 5); park()
    def attempt(name, fn):
        try: return fn()
        except Exception as error:  # report and keep going
            import traceback
            where = [f'{f.lineno}: {f.line}' for f in traceback.extract_tb(error.__traceback__) if f.filename == __file__][-1:]
            check(name, False, {'error': repr(error)[:300], 'at': where, 'library': library()})
            subprocess.run([str(s.HERE / 'ctl.py'), 'shot', str(SHOTS / ('FAILED-' + name.replace(' ', '-') + '.png'))])

    wait(lambda: status().get('lease'), 20)
    st = status()
    check('hello negotiates IPC 0.24 with objects.control', st.get('protocol') == '0.24' and 'objects.control' in st.get('capabilities', []),
          {'protocol': st.get('protocol'), 'capabilities': st.get('capabilities'), 'cli': (st.get('library') or {}).get('cli')})
    ref = f"official/{manifest['id']}"

    def browse():
        director()
        ui('tabNamed', 'library'); wait(lambda: status().get('tabName') == 'library')
        wait(lambda: library().get('loaded') and not library().get('busy'), 20)
        assert press('library-refresh-all')
        wait(lambda: not library().get('busy') and library().get('entries') == 1, 60)
        doc = cli('browse', '--json')['entries'][0]
        thumb = pathlib.Path(doc['thumbnail'] or '/nonexistent')
        ok = thumb.is_file() and hashlib.sha256(thumb.read_bytes()).hexdigest() == version['thumbnails'][0]['sha256'] and str(thumb).startswith(str(homes['cache']))
        sources = cli('source', 'list', '--json')['sources']
        shot('core-browse')
        check('Refresh sources lists the entry with its verified cached thumbnail', ok and doc['display'] == 'Official' and not any(x['error'] for x in sources),
              {'thumbnail': str(thumb), 'display': doc['display'], 'sources': [(x['id'], x['entries'], x['error']) for x in sources]})
    attempt('browse', browse)

    def install():
        catalog_before = status()['objects']['catalog']
        assert press('libraryAct:' + ref)
        wait(lambda: job().get('phase') in ('confirm', 'failed'), 60)
        shot('core-install-confirm')
        check('Install shows the plan for confirmation', job().get('phase') == 'confirm' and '--plan' in job().get('args', []), job())
        assert press('library-job-primary')
        wait(lambda: job().get('phase') in ('done', 'failed'), 120)
        shot('core-install-' + job().get('phase', 'unknown'))
        check('confirming installs it: stages to done', job().get('phase') == 'done' and '--yes' in job().get('args', []), job())
        assert press('library-job-primary')  # Open in Objects
        wait(lambda: status().get('tabName') == 'objects')
        wait(lambda: status()['objects']['catalog'] > catalog_before, 30)
        ui('objectFilter', 'library', '', ''); time.sleep(.5)
        shown = status()['objects']['shown']
        shot('core-objects-library')
        check("core's catalog lists the library's objects (Objects > Catalog, Library)", shown > 0,
              {'before': catalog_before, 'after': status()['objects']['catalog'], 'libraryShown': shown})
        ui('objectFilter', 'all', '', '')
    attempt('install', install)

    def installed_and_remove():
        ui('tabNamed', 'library'); ui('libraryView', 'installed'); wait(lambda: status().get('tabName') == 'library')
        wait(lambda: any(i.startswith(manifest['id'] + '@') for i in library().get('installs', [])), 20)
        ui('librarySelect', manifest['id']); time.sleep(.5)
        shot('core-installed')
        check('Installed lists it', True, library().get('installs'))
        catalog = status()['objects']['catalog']
        assert press('library-install-remove') and press('library-install-remove')
        wait(lambda: not library().get('busy') and not any(i.startswith(manifest['id'] + '@') for i in library().get('installs', [])), 60)
        ui('tabNamed', 'objects')
        wait(lambda: status()['objects']['catalog'] < catalog, 30)
        check('Remove removes it and the catalog drops it', True, {'before': catalog, 'after': status()['objects']['catalog'], 'feedback': library().get('feedback')})
    attempt('installed and remove', installed_and_remove)

    errors = (s.STATE / 'shell.log').read_text()
    bad = [x for x in ['ReferenceError', 'TypeError', 'Binding loop', 'Unable to assign', 'does not match the negotiated protocol'] if x in errors]
    check('no QML runtime errors in the shell log', not bad, bad)
    (SHOTS / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    failed = [r_['name'] for r_ in results if not r_['pass']]
    print(('PASS' if not failed else 'FAIL') + f' library-core: {len(results) - len(failed)}/{len(results)} checks', failed, flush=True)
    index.server.shutdown()
    client.call('runtime.exit', {})
    if failed: raise SystemExit(1)


if __name__ == '__main__':
    assert CLI, 'set HYPRUNE_CLI to the hyprune CLI (for example "node <sdk>/dist/src/cli.js")'
    shutil.rmtree(SHOTS, ignore_errors=True); SHOTS.mkdir(parents=True)
    # Ride the harness's catalog lifetime (IPC 0.22+ grants, private state) with these checks.
    catalog.prepare = prepare
    catalog.acceptance = acceptance
    s.run(argparse.Namespace(m3b=False, m3a=False, m2=False, m1=False, integration=False, live=False, serve=False, record=False,
                             visible=False, catalog=True, authoring=False, climbing=False))
