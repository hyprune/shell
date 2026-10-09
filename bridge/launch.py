#!/usr/bin/env python3
"""Trusted launcher: inherited token FD stays here, never in QML/argv/files."""
import argparse
import asyncio
import contextlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import socket
import signal
import stat
import tempfile
from client import Client
from preferences import Preferences
from world_style import load as load_world_style
from protocol import SUPPORTED_PROTOCOLS, at_least
from outline import OutlineController
from jsonschema.exceptions import ValidationError
from protocol import decode, WORLD_VALIDATORS

ROOT = Path(__file__).resolve().parents[1]


def presentation_child(pid):
    """Only a descendant of this trusted launcher may use its private bridge."""
    for _ in range(32):
        if pid == os.getpid(): return True
        if pid <= 1: return False
        try: pid = int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[1])
        except (OSError, ValueError, IndexError): return False
    return False


def socket_path(explicit=None):
    runtime = os.environ.get('XDG_RUNTIME_DIR')
    if not runtime or not Path(runtime).is_absolute():
        raise ValueError('XDG_RUNTIME_DIR must be an absolute path')
    base = Path(runtime)
    if base.stat().st_uid != os.getuid(): raise ValueError('runtime directory owner mismatch')
    if explicit:
        path = Path(explicit)
        if not path.is_relative_to(base) or '..' in path.parts:
            raise ValueError('explicit socket must be beneath XDG_RUNTIME_DIR')
    else:
        sig = os.environ.get('HYPRLAND_INSTANCE_SIGNATURE', '')
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', sig): raise ValueError('missing/unsafe instance signature')
        path = base / 'hyprune' / sig / 'control.sock'
    return str(path)


def catalog(paths):
    result = []
    for path in paths:
        manifest = Path(path)
        obj = decode(manifest.read_bytes())
        version = obj.get('formatVersion')
        if version not in WORLD_VALIDATORS: raise ValueError('Unsupported world format')
        WORLD_VALIDATORS[version].validate(obj)
        result.append(obj)
    return result


async def main(args):
    directory = Path(tempfile.mkdtemp(prefix='hyprune-shell-', dir=os.environ['XDG_RUNTIME_DIR']))
    os.chmod(directory, 0o700)
    local = directory / 'presentation.sock'
    peers = set()
    cache = {}
    preferences = Preferences()
    style_catalog = {}
    style_world = None
    tokens = None
    renewal_fd = None
    if args.token_fd is not None:
        # A supervisor writes a NEW one-shot token line per connection attempt.
        tokens = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(tokens)
        await asyncio.get_running_loop().connect_read_pipe(lambda: protocol, os.fdopen(os.dup(args.token_fd), 'rb', buffering=0))
        if os.environ.get('HYPRUNE_TOKEN_REFRESH') == '1': renewal_fd = os.dup(args.token_fd)
        os.close(args.token_fd)

    async def token_source():
        if renewal_fd is not None: os.write(renewal_fd, b'renew\n')
        line = await tokens.readline()
        if not line: raise RuntimeError('Supervisor token FD exhausted; relaunch required')
        token = line.decode('ascii').strip()
        if not re.fullmatch('[a-f0-9]{64}', token): raise ValueError('invalid supervisor token')
        return token

    def emit(event):
        nonlocal style_world
        if event['type'] == 'state':
            state = event.get('state')
            world_id = state['world']['id'] if state and state.get('world') and state['runtime']['active'] else None
            if world_id != style_world:
                style_world = world_id
                style = style_catalog.get(world_id,{})
                emit({'type':'world.style','value':style})
                if style.get('warning'): emit({'type':'notice','level':'warning','message':style['warning'],'code':'style.asset'})
        if event["type"] in ["connection", "notice"]: print(json.dumps(event), flush=True)
        if event['type'] in ['connection', 'hello', 'state', 'director', 'catalog', 'presentation', 'metadata', 'preferences', 'world.style', 'outline']:
            cache[event['type']] = event
        line = (json.dumps(event, ensure_ascii=False, allow_nan=False) + '\n').encode()
        for writer in tuple(peers):
            if writer.transport.get_write_buffer_size() > 4 * 1024 * 1024:
                writer.close()
                peers.discard(writer)
            elif not writer.is_closing(): writer.write(line)

    emit({'type':'preferences', 'value':preferences.value})
    bindings = dict(pair.split('=', 1) for pair in args.output)
    client = Client(socket_path(args.socket), emit, token_source if tokens else None, bindings, args.protocol, args.client_id)
    outline = OutlineController(client)
    worlds = catalog(args.world_package)
    for manifest in args.world_package:
        try:
            style = load_world_style(manifest,directory/'assets')
            if style: style_catalog[style['worldId']] = style
        except (ValueError, OSError, ValidationError) as error:
            emit({'type':'notice','level':'warning','message':'World HUD style unavailable; using your concept style.','code':'style.invalid'})
    emit({'type':'world.style','value':{}})
    client.worlds = worlds
    emit({'type': 'catalog', 'worlds': worlds})
    fixture = json.loads(Path(args.presentation).read_text()) if args.presentation else None
    if fixture: emit({'type': 'presentation', **fixture})

    async def open_preview():
        if at_least(args.protocol, 2):
            await client.call('ui.open', {'leaseId':client.lease,'outputId':client.output,'panel':'overview'})
        else:
            await client.overlay(True)

    async def perform(cmd):
        try:
            if cmd['type'] == 'screens':
                client.screens = cmd['names']
                await client.reconcile()
            elif cmd['type'] == 'preferences':
                emit({'type':'preferences', 'value':preferences.update(cmd['patch'])})
            elif cmd['type'] == 'close':
                await client.overlay(False)
            elif cmd['type'] == 'drive' and at_least(args.protocol, 3):
                await client.call('route.set', {'points':[{'position':cmd['position']}]})
                await client.call('autodrive.start', {})
            elif cmd['type'] in ['outline.get','outline.patch'] and at_least(args.protocol,13):
                result = await outline.update(cmd.get('worldId'),cmd.get('patch'))
                emit({'type':'outline','value':result})
            elif cmd['type'] == 'action':
                # QML can request only the published intent methods.
                if cmd['method'] not in (['world.load', 'surface.focus', 'movement.set', 'runtime.exit'] +
                        (['graphics.get','graphics.set'] if at_least(args.protocol, 7) else []) +
                        (['camera.get'] if at_least(args.protocol,13) else []) +
                        (['overlay.style','input.get','input.preview','input.set','input.capture','input.capture.cancel'] if at_least(args.protocol, 6) else []) +
                        (['surfaces.recall', 'surface.pull', 'surface.place', 'surface.return', 'workspace.focus', 'workspace.unfocus'] if at_least(args.protocol, 4) else []) +
                        (['waypoint.set', 'travel.start', 'travel.cancel', 'route.set', 'autodrive.start', 'autodrive.stop', 'workspace.activate'] if at_least(args.protocol, 2) else [])):
                    raise ValueError('Unknown shell action')
                params=cmd['params']
                if cmd['method']=='overlay.style':params={**params,'leaseId':client.lease}
                result = await client.call(cmd['method'], params)
                emit({'type': 'action', 'method': cmd['method'], 'result': result})
            elif cmd['type'] == 'dev.warp' and fixture and at_least(args.protocol, 2):
                await client.call('world.load', {'worldId': cmd['worldId']})
            elif cmd['type'] == 'dev.open' and fixture:
                await open_preview()
            else:
                raise ValueError('Unknown presentation command')
        except Exception as error:
            message = 'Core response does not match the negotiated protocol.' if isinstance(error, ValidationError) else str(error)[:512]
            emit({'type': 'notice', 'level': 'warning', 'code': 'shell.action', 'message': message})

    current_peer = None
    async def peer(reader, writer):
        nonlocal current_peer
        creds = writer.get_extra_info('socket').getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
        import struct
        pid, uid, _ = struct.unpack('3i', creds)
        if uid != os.getuid() or not presentation_child(pid):
            writer.close()
            return
        # Quickshell's crash supervisor may retain the old socket FD. A verified
        # replacement child supersedes it; the core connection/grant stays here.
        for old in tuple(peers): old.close()
        with contextlib.suppress(Exception): await client.overlay(False)
        current_peer = writer
        client.wayland_pid = pid
        peers.add(writer)
        print(json.dumps({'type':'presentation.peer','pid':pid}), flush=True)
        commands = set()
        for event in cache.values(): writer.write((json.dumps(event) + '\n').encode())
        # Timing is recomputed after a QML restart, never replayed from cache.
        client.publish_hold(force=True)
        try:
            while line := await reader.readline():
                cmd = decode(line)
                if len(commands) >= 64:
                    raise ConnectionError('Presentation command queue overflow')
                task = asyncio.create_task(perform(cmd))
                commands.add(task)
                task.add_done_callback(commands.discard)
                await writer.drain()
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            for task in tuple(commands): task.cancel()
            await asyncio.gather(*commands, return_exceptions=True)
            peers.discard(writer)
            writer.close()
            if current_peer is writer:
                current_peer = None
                with contextlib.suppress(Exception): await client.overlay(False)

    server = await asyncio.start_unix_server(peer, str(local), limit=1_048_576)
    os.chmod(local, 0o600)
    env = {**os.environ, 'HYPRUNE_BRIDGE_SOCKET': str(local), 'HYPRUNE_OUTPUT_SCREEN': next(iter(bindings.values()), os.environ.get('HYPRUNE_OUTPUT_SCREEN', ''))}
    env.pop('HYPRUNE_TOKEN_FD', None)
    child = await asyncio.create_subprocess_exec('qs', '-p', str(ROOT / 'qml'), '--no-color', env=env)
    client.wayland_pid = child.pid
    task = asyncio.create_task(client.run())

    async def tour():
        if not fixture or not args.tour: return
        while not client.lease: await asyncio.sleep(.1)
        await asyncio.sleep(3)
        emit({'type': 'notice', 'level': 'info', 'code': 'mock.arrival', 'message': 'Observatory link established. Your desktop is within reach.'})
        emit({'type': 'zone', 'name': 'The arrival garden', 'subtitle': 'OBSERVATORY / SECTOR 01'})
        await asyncio.sleep(3)
        await open_preview()
        for index in range(6):
            emit({'type': 'dev.tab', 'index': index})
            await asyncio.sleep(4)
        await client.overlay(False)
        if at_least(args.protocol, 2): await client.call('world.load', {'worldId': 'com.hyprune.garden'})

    async def projection_preview():
        # Synthetic projection samples supplied by a dev camera fixture, never
        # inferred as a real core camera from the player's movement quaternion.
        while True:
            if fixture and client.ready:
                elapsed = asyncio.get_running_loop().time()
                emit({'type': 'projection', 'markers': [
                    {**m, 'x': m['x'] + .016 * math.sin(elapsed / 2.8),
                     'y': m['y'] + .007 * math.cos(elapsed / 3)}
                    for m in (fixture.get('markers', []) if not fixture.get('worldId') or client.state['world']['id']==fixture['worldId'] else [])]})
            await asyncio.sleep(.1)

    projecting = asyncio.create_task(projection_preview())
    touring = asyncio.create_task(tour())
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in [signal.SIGTERM, signal.SIGINT]: loop.add_signal_handler(sig, stop.set)
    child_wait = asyncio.create_task(child.wait())
    stop_wait = asyncio.create_task(stop.wait())
    try:
        while True:
            done, _ = await asyncio.wait([child_wait, stop_wait], return_when=asyncio.FIRST_COMPLETED)
            if stop_wait in done or child.returncode == 0: break
            emit({'type':'notice','level':'warning','code':'shell.qml-restart','message':'Presentation exited; restarting through the existing authenticated bridge'})
            with contextlib.suppress(Exception): await client.overlay(False)
            await asyncio.sleep(.3)
            child = await asyncio.create_subprocess_exec('qs', '-p', str(ROOT / 'qml'), '--no-color', env=env)
            client.wayland_pid = child.pid
            child_wait = asyncio.create_task(child.wait())
    finally:
        stop_wait.cancel()
        touring.cancel()
        projecting.cancel()
        await client.shutdown()
        task.cancel()
        await asyncio.gather(task, touring, projecting, return_exceptions=True)
        if renewal_fd is not None: os.close(renewal_fd)
        server.close()
        for writer in tuple(peers): writer.close()
        await server.wait_closed()
        if child.returncode is None:
            child.terminate()
            await child_wait
        shutil.rmtree(directory)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--socket', default=os.environ.get('HYPRUNE_SOCKET'))
    parser.add_argument('--protocol', choices=SUPPORTED_PROTOCOLS, default=os.environ.get('HYPRUNE_PROTOCOL', '0.15'), help='Exact production protocol; never auto-upgrade')
    parser.add_argument('--token-fd', type=int, default=int(os.environ['HYPRUNE_TOKEN_FD']) if 'HYPRUNE_TOKEN_FD' in os.environ else None)
    parser.add_argument('--output', action='append', default=[], metavar='OPAQUE_ID=WAYLAND_NAME')
    parser.add_argument('--world-package', action='append', default=[], metavar='WORLD_JSON')
    parser.add_argument('--presentation', help='DEV ONLY: local camera/map fixture, never IPC fields')
    parser.add_argument('--client-id', default=os.environ.get('HYPRUNE_CLIENT_ID', 'com.hyprune.shell'))
    parser.add_argument('--tour', action='store_true')
    args = parser.parse_args()
    try: asyncio.run(main(args))
    except KeyboardInterrupt: pass
