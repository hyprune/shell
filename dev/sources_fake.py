#!/usr/bin/env python3
"""DEV ONLY: a stand-in for the source helper's control socket (sources.sock) for the bridge
tests and mock captures of Director > Objects > Placed > Data source. It runs nothing: status
is canned, test answers come from a table keyed by argv[0], and restart / restart-all /
reload are recorded and answered ok.

    python3 dev/sources_fake.py SOCKET [--config PATH] [--disconnected]

Point the bridge at it with --sources-control SOCKET (or HYPRUNE_SOURCES_CONTROL).
"""
import argparse
import asyncio
import json
import os
import time

LIMITS = {'command': {'intervalS': [5, 86400], 'devIntervalS': 1, 'timeoutS': [1, 60]}}


def status(config, connected=True, now=None):
    """A status answer with one command source, u-3f9a1c, that ran 4 s ago."""
    now = int(time.time() * 1000) if now is None else now
    return {'ok': True, 'config': config, 'connected': connected, 'limits': LIMITS, 'sources': {
        'u-3f9a1c': {'kind': 'command', 'argv': ['/home/user/bin/ram-gauge', '--json'], 'intervalS': 10, 'enabled': True,
                     'running': False, 'resets': 0, 'nextRunAt': now + 6000,
                     'lastRun': {'at': now - 4000, 'ok': True, 'error': None, 'exitCode': 0, 'durationMs': 42,
                                 'values': {'value': 71, 'display': '71%', 'label': 'RAM', 'level': 'ok', '_status': 'ok'}}}}}


TEST = {'ok': True, 'values': {'value': 71, 'display': '71%', 'label': 'RAM', 'level': 'ok', '_status': 'ok'},
        'stdout': '{"value": 71, "display": "71%", "label": "RAM", "level": "ok"}\n', 'stderr': '',
        'error': None, 'exitCode': 0, 'durationMs': 38}
# An HTTP source's test (data sources phase 2): the raw body beside the mapped values.
TEST_HTTP = {'ok': True, 'values': {'name': 'ingest', 'value': 66.67, 'level': 'warn', 'display': '40 s behind', 'label': 'Ingest'},
             'stdout': '', 'stderr': '', 'error': None, 'exitCode': None, 'durationMs': 112,
             'raw': '{"items": [{"state": "ok", "lag": 3}, {"state": "late", "lag": 40}], "name": "ingest"}',
             'rawBytes': 84, 'httpStatus': 200, 'contentType': 'application/json', 'secrets': {'api-key': 'file'}}
SECRETS = {'ok': True, 'file': '/home/user/.config/hyprune/secrets.json', 'fileProblem': None, 'keyring': False,
           'names': {'api-key': 'file', 'ci-token': None}}


class FakeHelper:
    """replies: op -> a reply dict, or 'hang' (never answers), 'close' (no answer), 'garbage'
    (not JSON) or 'huge' (more than 64 KiB)."""

    def __init__(self, config='/home/user/.config/hyprune/sources.json', connected=True, tests=None, replies=None):
        self.config, self.connected = config, connected
        self.tests = tests or {}
        self.replies = dict(replies or {})
        self.requests = []
        self.server = None
        self.release = None

    def answer(self, message):
        op = message.get('op') if isinstance(message, dict) else None
        if op in self.replies:
            return self.replies[op]
        if op == 'status':
            return status(self.config, self.connected)
        if op == 'test':
            source = message.get('source') or {}
            if source.get('kind') == 'http':
                return self.tests.get(source.get('url'), TEST_HTTP)
            argv = (source.get('argv') or [''])
            return self.tests.get(argv[0], TEST)
        if op == 'secrets':
            return SECRETS
        if op in ('restart', 'restart-all', 'reload'):
            return {'ok': True}
        return {'ok': False, 'error': 'unknown op'}

    async def handle(self, reader, writer):
        try:
            line = await reader.readline()
            message = json.loads(line) if line else None
            self.requests.append(message)
            reply = self.answer(message)
            if reply == 'hang':
                await self.release.wait()
            elif reply == 'garbage':
                writer.write(b'not json\n')
            elif reply == 'huge':
                writer.write(b'{"ok": true, "pad": "' + b'x' * 70000 + b'"}\n')
            elif reply != 'close':
                writer.write((json.dumps(reply) + '\n').encode())
            await writer.drain()
        except (ConnectionError, asyncio.CancelledError):
            pass
        finally:
            writer.close()

    async def start(self, path):
        self.release = asyncio.Event()
        self.server = await asyncio.start_unix_server(self.handle, path)
        os.chmod(path, 0o600)
        return self

    async def stop(self):
        if self.server:
            self.release.set()
            self.server.close()
            await self.server.wait_closed()


async def main(args):
    helper = await FakeHelper(args.config, not args.disconnected).start(args.socket)
    print('fake source helper on', args.socket, flush=True)
    try:
        await asyncio.Event().wait()
    finally:
        await helper.stop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('socket')
    parser.add_argument('--config', default=os.path.join(os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config'), 'hyprune', 'sources.json'))
    parser.add_argument('--disconnected', action='store_true')
    try:
        asyncio.run(main(parser.parse_args()))
    except KeyboardInterrupt:
        pass
