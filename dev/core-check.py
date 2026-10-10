#!/usr/bin/env python3
"""Exercise this shell against real core in our own locked nested compositor."""
import asyncio
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CORE = Path(os.environ.get('HYPRUNE_CORE_DIR', ROOT.parent / 'core'))
RUN = ROOT / 'dev/.run/core'
sys.path.insert(0, str(ROOT / 'bridge'))
from client import Client, GRANTS


class CoreProbe(Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.signals = []

    def present_location(self, hint=None):
        if hint is not None: self.signals.append(hint)
        super().present_location(hint)


async def until(predicate, seconds=12):
    async with asyncio.timeout(seconds):
        while not predicate():
            await asyncio.sleep(.05)


async def main():
    RUN.mkdir(parents=True, exist_ok=True)
    os.chmod(RUN, 0o700)
    installed = RUN / 'worlds'
    installed.mkdir(exist_ok=True)
    manifests = []
    for name in ['atrium', 'materials']:
        source = CORE / 'tests/fixtures' / name
        if not (source / 'world.json').exists():
            raise RuntimeError('Generate core fixtures per its README first')
        world_id = json.loads((source / 'world.json').read_text())['id']
        target = installed / world_id
        shutil.copytree(source, target, dirs_exist_ok=True)
        manifests.append(target / 'world.json')
    if not (CORE / 'build/hyprune-core.so').exists():
        raise RuntimeError('Build core per its README first')

    outer_signature = os.environ.get('HYPRLAND_INSTANCE_SIGNATURE', '')
    outer_display = os.environ['WAYLAND_DISPLAY']
    config = ROOT / 'dev/hyprland.lua'
    session_file = ROOT / 'dev/.run/session.json'
    session_file.unlink(missing_ok=True)
    tokens = {'org.hyprune.shell.smoke': secrets.token_hex(32), 'com.hyprune.shell': secrets.token_hex(32)}
    grant_read, grant_write = os.pipe()
    os.write(grant_write, json.dumps([{'token': token, 'client': client, 'capabilities': GRANTS}
                                    for client, token in tokens.items()]).encode())
    os.close(grant_write)
    env = {**os.environ, 'AQ_BACKEND': 'wayland', 'HYPRUNE_WORLD_DIR': str(installed),
           'HYPRUNE_LAUNCH_FD': str(grant_read), 'HYPRUNE_SHELL_ROOT': str(ROOT)}
    env.pop('HYPRLAND_INSTANCE_SIGNATURE', None)
    compositor_log = (RUN / 'hyprland.log').open('w')
    compositor = subprocess.Popen(['Hyprland', '-c', str(config)], env=env, pass_fds=(grant_read,),
                                  stdout=compositor_log, stderr=subprocess.STDOUT)
    os.close(grant_read)
    start_time = Path(f'/proc/{compositor.pid}/stat').read_text().split()[21]
    bridge = probe = probe_task = None
    logs = [compositor_log]
    try:
        await until(session_file.exists)
        session = json.loads(session_file.read_text())
        signature, display = session['HYPRLAND_INSTANCE_SIGNATURE'], session['WAYLAND_DISPLAY']
        nested_env = {**os.environ, 'HYPRLAND_INSTANCE_SIGNATURE': signature, 'WAYLAND_DISPLAY': display}
        runtime = Path(env['XDG_RUNTIME_DIR'])

        def verified():
            assert compositor.poll() is None, 'nested compositor exited'
            assert Path(f'/proc/{compositor.pid}/stat').read_text().split()[21] == start_time, 'PID reused'
            assert str(config).encode() in Path(f'/proc/{compositor.pid}/cmdline').read_bytes().split(b'\0')
            assert signature != outer_signature and display != outer_display, 'refusing outer session'
            lock = (runtime / 'hypr' / signature / 'hyprland.lock').read_text().splitlines()
            assert lock[:2] == [str(compositor.pid), display], 'nested lock identity mismatch'
            assert (runtime / display).is_socket()
            return nested_env

        def ctl(*args):
            return subprocess.check_output(['hyprctl', '-i', signature, *args], env=verified(), text=True).strip()

        def nested(*args):
            subprocess.run(args, env=verified(), check=True, stdout=subprocess.DEVNULL)

        ctl('output', 'create', 'headless', 'HYPRUNE-PREVIEW')
        ctl('eval', 'hl.dispatch(hl.dsp.focus({monitor="HYPRUNE-PREVIEW"}))')
        plugin = RUN / 'hyprune-core.so'
        shutil.copy2(CORE / 'build/hyprune-core.so', plugin)
        assert ctl('plugin', 'load', str(plugin)) == 'ok'
        ctl('reload')
        ctl('dismissnotify', '-1')
        core_socket = runtime / 'hyprune' / signature / 'control.sock'
        await until(core_socket.is_socket)
        info = core_socket.lstat()
        assert info.st_uid == os.getuid() and stat.S_ISSOCK(info.st_mode)
        socket_normalized = stat.S_IMODE(info.st_mode) == 0o700
        if socket_normalized:
            # Current core bind uses umask(0077), producing 0700 rather than
            # RFC-0003's 0600. Normalize only this verified test-owned socket.
            verified()
            core_socket.chmod(0o600)
            print('Core test adapter: normalize owned nested socket 0700 -> RFC 0600', flush=True)
        # Core currently binds before its plugin method advertisement arrives.
        # Avoid consuming a one-shot token on that incomplete startup profile.
        await asyncio.sleep(.3)
        events = []

        async def probe_token(): return tokens['org.hyprune.shell.smoke']
        probe = CoreProbe(str(core_socket), events.append, probe_token, protocol='0.2', client_id='org.hyprune.shell.smoke')
        probe_task = asyncio.create_task(probe.run())
        try:
            await until(lambda: probe.ready)
        except TimeoutError:
            for event in events:
                if event['type'] == 'connection': print(event, flush=True)
            raise
        assert probe.hello['protocol'] == '0.2'
        print('Core hello: 0.2,', len(probe.hello['methods']), 'advertised methods', flush=True)
        await probe.call('world.load', {'worldId': 'org.hyprune.materials'})
        ctl('eval', 'hl.plugin.hyprune.toggle("HYPRUNE-PREVIEW")')
        await until(lambda: probe.state and probe.state['runtime']['active'] and probe.state['runtime']['outputs'])
        output_id = probe.state['runtime']['outputs'][0]

        token_read, token_write = os.pipe()
        os.write(token_write, (tokens['com.hyprune.shell'] + '\n').encode())
        os.close(token_write)
        shell_log = (RUN / 'shell.log').open('w'); logs.append(shell_log)
        command = [sys.executable, str(ROOT / 'bridge/launch.py'), '--protocol', '0.2', '--client-id', 'com.hyprune.shell',
                   '--socket', str(core_socket), '--token-fd', str(token_read), '--output', output_id + '=HYPRUNE-PREVIEW']
        for manifest in manifests: command += ['--world-package', str(manifest)]
        bridge = subprocess.Popen(command, env=verified(), pass_fds=(token_read,), stdout=shell_log, stderr=subprocess.STDOUT)
        os.close(token_read)
        shell_pid = None
        for _ in range(100):
            children = Path(f'/proc/{bridge.pid}/task/{bridge.pid}/children').read_text().split()
            shell_pid = next((int(pid) for pid in children if Path(f'/proc/{pid}/comm').read_text().strip() in ['qs', 'quickshell']), None)
            if shell_pid: break
            await asyncio.sleep(.1)
        assert shell_pid, 'Quickshell child did not start'

        def ui():
            try:
                return json.loads(subprocess.check_output(['qs', 'ipc', '--pid', str(shell_pid), 'call', 'preview', 'status'],
                                                         env=verified(), text=True, stderr=subprocess.DEVNULL))
            except subprocess.CalledProcessError:
                if bridge.poll() is not None: raise RuntimeError('Shell exited; see core/shell.log')
                return {'status':'starting','lease':'','director':False,'warp':False}

        await until(lambda: ui()['status'] == 'live' and ui()['lease'])
        assert not ui()['warp'], 'A terminal initial snapshot replayed a warp'
        # Core, rather than QML, owns the actual seat hold timing. It cannot yet
        # grant this UI exclusive input; the shell must keep its Director unmapped.
        nested('wtype', '-P', 'Tab', '-s', '450', '-p', 'Tab')
        await until(lambda: any(lease['overlays'] for lease in probe.state['shell']['leases']))
        await asyncio.sleep(.3)
        assert not ui()['director'], 'Unsupported exclusive input must not map Director'
        nested('wtype', '-k', 'Escape')
        await asyncio.sleep(.2)
        print('Real core 0.2: hold timing and rejected exclusive mapping PASS', flush=True)

        await probe.call('travel.start', {'to': {'zoneId': 'gallery'}, 'durationMs': 5800})
        await until(lambda: ui()['warp'])
        await asyncio.sleep(2)
        shots = Path(os.environ.get('HYPRUNE_GALLERY_DIR', str(Path(__file__).resolve().parent / '.run/gallery'))) / 'screenshots/hyprune-shell-m0'
        shots.mkdir(parents=True, exist_ok=True)
        nested('grim', '-o', 'HYPRUNE-PREVIEW', str(shots / 'native-core-warp.png'))
        await until(lambda: probe.state['location']['transition']['phase'] == 'arrived')
        await until(lambda: not ui()['warp'])
        await asyncio.sleep(.6)
        nested('grim', '-o', 'HYPRUNE-PREVIEW', str(shots / 'native-core-hud.png'))
        print('Real core 0.2: travel, passive warp and confirmed arrival PASS', flush=True)

        before = len(probe.signals)
        await probe.call('world.load', {'worldId': 'org.hyprune.atrium'})
        transitions = probe.signals[before:]
        assert any(t['phase'] == 'loading' and t['progress'] is None for t in transitions), 'Missing pending-load state'
        await until(lambda: probe.state['world']['id'] == 'org.hyprune.atrium')
        await until(lambda: not ui()['warp'])
        print('Real core 0.2: indeterminate world loading and activation PASS', flush=True)

        await probe.call('travel.start', {'to': {'position': [0, 1.7, 4]}, 'durationMs': 5800})
        await until(lambda: ui()['warp'])
        nested('wtype', '-k', 'F12')
        await until(lambda: not probe.state['runtime']['active'])
        await until(lambda: not ui()['warp'] and not ui()['director'] and not ui()['lease'])
        print('Real core 0.2: F12 during warp restores desktop; shell unmaps PASS', flush=True)
        (RUN / 'result.json').write_text(json.dumps({'protocol': '0.2', 'socketPermissionsNormalized': socket_normalized, 'coreCommit': subprocess.check_output(['git', '-C', str(CORE), 'rev-parse', 'HEAD']).decode().strip(), 'hold': True, 'exclusiveRejected': True, 'travel': True, 'worldLoad': True, 'escapeDuringWarp': True}, indent=2) + '\n')
    finally:
        if bridge and bridge.poll() is None:
            bridge.terminate()
            await asyncio.to_thread(bridge.wait, 8)
        if probe:
            await probe.shutdown()
        if probe_task:
            probe_task.cancel(); await asyncio.gather(probe_task, return_exceptions=True)
        if compositor.poll() is None:
            compositor.terminate()
            try: await asyncio.to_thread(compositor.wait, 8)
            except subprocess.TimeoutExpired: compositor.kill(); await asyncio.to_thread(compositor.wait)
        for log in logs: log.close()
        session_file.unlink(missing_ok=True)


if __name__ == '__main__':
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
