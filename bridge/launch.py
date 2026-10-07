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
from protocol import decode, WORLD_VALIDATOR

ROOT = Path(__file__).resolve().parents[1]


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
        WORLD_VALIDATOR.validate(obj)
        result.append(obj)
    return result


async def main(args):
    directory = Path(tempfile.mkdtemp(prefix='hyprune-shell-', dir=os.environ['XDG_RUNTIME_DIR']))
    os.chmod(directory, 0o700)
    local = directory / 'presentation.sock'
    peers = set()
    cache = {}
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
        if event['type'] in ['connection', 'hello', 'state', 'director', 'catalog', 'presentation', 'metadata']:
            cache[event['type']] = event
        line = (json.dumps(event, ensure_ascii=False, allow_nan=False) + '\n').encode()
        for writer in tuple(peers):
            if writer.transport.get_write_buffer_size() > 4 * 1024 * 1024:
                writer.close()
                peers.discard(writer)
            else: writer.write(line)

    bindings = dict(pair.split('=', 1) for pair in args.output)
    client = Client(socket_path(args.socket), emit, token_source if tokens else None, bindings, args.mock_preview)
    worlds = catalog(args.world_package)
    emit({'type': 'catalog', 'worlds': worlds})
    fixture = json.loads(Path(args.presentation).read_text()) if args.presentation else None
    if fixture: emit({'type': 'presentation', **fixture})

    async def open_preview():
        if args.mock_preview:
            await client.call('ui.open', {'leaseId':client.lease,'outputId':client.output,'panel':'director'})
        else:
            await client.overlay(True)

    async def peer(reader, writer):
        creds = writer.get_extra_info('socket').getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
        import struct
        if struct.unpack('3i', creds)[1] != os.getuid() or peers:
            writer.close()
            return
        peers.add(writer)
        for event in cache.values(): writer.write((json.dumps(event) + '\n').encode())
        try:
            while line := await reader.readline():
                cmd = decode(line)
                try:
                    if cmd['type'] == 'screens':
                        client.screens = cmd['names']
                        await client.reconcile()
                    elif cmd['type'] == 'close':
                        await client.overlay(False)
                    elif cmd['type'] == 'action':
                        # QML can request only the published intent methods.
                        if cmd['method'] not in (['world.load', 'surface.focus', 'movement.set', 'runtime.exit'] + (['waypoint.set', 'camera.set'] if args.mock_preview else [])):
                            raise ValueError('Unknown shell action')
                        result = await client.call(cmd['method'], cmd['params'])
                        emit({'type': 'action', 'method': cmd['method'], 'result': result})
                    elif cmd['type'] == 'dev.warp' and args.mock_preview:
                        await client.call('world.load', {'worldId': cmd['worldId']})
                    elif cmd['type'] == 'dev.open' and fixture:
                        await open_preview()
                    else:
                        raise ValueError('Unknown presentation command')
                except Exception as error:
                    emit({'type': 'notice', 'level': 'warning', 'code': 'shell.action', 'message': str(error)})
                await writer.drain()
        finally:
            peers.discard(writer)
            writer.close()
            with contextlib.suppress(Exception): await client.overlay(False)

    server = await asyncio.start_unix_server(peer, str(local), limit=1_048_576)
    os.chmod(local, 0o600)
    env = {**os.environ, 'HYPRUNE_BRIDGE_SOCKET': str(local), 'HYPRUNE_OUTPUT_SCREEN': next(iter(bindings.values()), '')}
    env.pop('HYPRUNE_TOKEN_FD', None)
    child = await asyncio.create_subprocess_exec('qs', '-p', str(ROOT / 'qml'), '--no-color', env=env)
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

    async def projection_preview():
        # Synthetic projection samples supplied by a dev camera fixture, never
        # inferred as a real core camera from the player's movement quaternion.
        while True:
            if fixture and client.ready:
                elapsed = asyncio.get_running_loop().time()
                emit({'type': 'projection', 'markers': [
                    {**m, 'x': m['x'] + .016 * math.sin(elapsed / 2.8),
                     'y': m['y'] + .007 * math.cos(elapsed / 3)}
                    for m in fixture.get('markers', [])]})
            await asyncio.sleep(.1)

    projecting = asyncio.create_task(projection_preview())
    touring = asyncio.create_task(tour())
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in [signal.SIGTERM, signal.SIGINT]: loop.add_signal_handler(sig, stop.set)
    child_wait = asyncio.create_task(child.wait())
    stop_wait = asyncio.create_task(stop.wait())
    try:
        await asyncio.wait([child_wait, stop_wait], return_when=asyncio.FIRST_COMPLETED)
    finally:
        stop_wait.cancel()
        touring.cancel()
        projecting.cancel()
        await client.shutdown()
        task.cancel()
        await asyncio.gather(task, touring, projecting, return_exceptions=True)
        if renewal_fd is not None: os.close(renewal_fd)
        server.close()
        await server.wait_closed()
        if child.returncode is None:
            child.terminate()
            await child_wait
        shutil.rmtree(directory)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--socket')
    parser.add_argument('--token-fd', type=int, default=int(os.environ['HYPRUNE_TOKEN_FD']) if 'HYPRUNE_TOKEN_FD' in os.environ else None)
    parser.add_argument('--output', action='append', default=[], metavar='OPAQUE_ID=WAYLAND_NAME')
    parser.add_argument('--world-package', action='append', default=[], metavar='WORLD_JSON')
    parser.add_argument('--presentation', help='DEV ONLY: local camera/map fixture, never IPC fields')
    parser.add_argument('--mock-preview', action='store_true', help='DEV ONLY: SDK protocol 0.1-mock.1')
    parser.add_argument('--tour', action='store_true')
    args = parser.parse_args()
    if args.mock_preview and not args.presentation: parser.error('--mock-preview requires --presentation')
    try: asyncio.run(main(args))
    except KeyboardInterrupt: pass
