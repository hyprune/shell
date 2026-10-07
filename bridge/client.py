"""Connection-scoped authority, snapshot ordering and lease lifecycle."""
import asyncio
import contextlib
import itertools
import random
import os
from pathlib import Path
import socket
import stat
import struct
from protocol import frame, read_frame, validate_response, VALIDATOR, MOCK_VALIDATOR

GRANTS = ['state.read', 'world.control', 'surface.control', 'movement.control', 'shell.control', 'runtime.control']
REQUIRED = ['session.hello', 'session.ping', 'state.subscribe', 'state.snapshot', 'state.unsubscribe',
            'shell.claim', 'shell.release', 'shell.overlay', 'surface.focus', 'movement.set', 'world.load', 'runtime.exit']


class Client:
    def __init__(self, path, emit, token_source=None, bindings=None, mock_preview=False):
        self.path, self.emit, self.token_source = path, emit, token_source
        self.bindings = bindings or {}
        self.protocol = '0.1-mock.1' if mock_preview else '0.1'
        self.validator = MOCK_VALIDATOR if mock_preview else VALIDATOR
        self.metadata = None
        self.screens = []
        self.pending = {}
        self.pending_methods = {}
        self.counter = itertools.count(1)
        self.writer = None
        self.hello = {}
        self.state = None
        self.revision = -1
        self.session = self.subscription = self.lease = self.output = None
        self.resyncing = False
        self.director = False
        self.overlay_revision = -1
        self.ready = False
        self.stopping = False
        self.write_lock = asyncio.Lock()
        self.ui_lock = asyncio.Lock()
        self.lease_seen = False
        self.claim_blocked = False
        self.tasks = set()

    async def call(self, method, params, bootstrap=False):
        if not self.writer or (not bootstrap and method not in self.hello.get('methods', [])):
            raise RuntimeError('Unavailable: ' + method)
        if len(self.pending) >= 64:
            raise RuntimeError('Too many outstanding requests')
        rid = 'shell-' + str(next(self.counter))
        future = asyncio.get_running_loop().create_future()
        self.pending[rid] = future
        self.pending_methods[rid] = method
        try:
            async with self.write_lock:
                packet = frame({'jsonrpc': '2.0', 'id': rid, 'method': method, 'params': params}, self.validator)
                if self.writer.transport.get_write_buffer_size() + len(packet) > 4 * 1024 * 1024:
                    self.writer.close()
                    raise ConnectionError('Core write queue overflow')
                self.writer.write(packet)
                await asyncio.wait_for(self.writer.drain(), 10)
            return await asyncio.wait_for(future, 35 if not bootstrap else 5)
        finally:
            self.pending.pop(rid, None)
            self.pending_methods.pop(rid, None)

    def publish(self):
        self.emit({'type': 'state', 'state': self.state, 'revision': self.revision,
                   'lease': self.lease, 'output': self.output,
                   'screen': self.bindings.get(self.output), 'director': self.director})

    def snapshot(self, snapshot):
        if snapshot['sessionId'] != self.session:
            raise ValueError('snapshot belongs to another session')
        self.state = snapshot['state']
        self.revision = snapshot['revision']
        self.publish()

    async def resync(self):
        try:
            result = await self.call('state.snapshot', {'subscriptionId': self.subscription})
        finally:
            self.resyncing = False
        await self.reconcile()

    async def receive(self, reader):
        while True:
            msg = await read_frame(reader, self.validator)
            if 'id' in msg:
                future = self.pending.get(msg['id'])
                if not future or future.done():
                    raise ValueError('unexpected response ID')
                validate_response(msg, self.pending_methods[msg['id']], self.validator)
                if 'error' in msg:
                    err = msg['error']
                    future.set_exception(RuntimeError(str(err['code']) + ': ' + err['message']))
                else:
                    method = self.pending_methods[msg['id']]
                    if method == 'state.subscribe':
                        self.subscription = msg['result']['subscriptionId']
                        self.snapshot(msg['result']['snapshot'])
                    elif method == 'state.snapshot':
                        self.snapshot(msg['result']['snapshot'])
                        self.resyncing = False
                    future.set_result(msg['result'])
                continue
            if msg['method'] not in self.hello.get('events', []):
                raise ValueError('unadvertised event')
            p = msg['params']
            if msg['method'] == 'session.revoked':
                raise RuntimeError('Session revoked: ' + p['reason'])
            if msg['method'] == 'runtime.notice':
                if self.protocol == '0.1-mock.1' and p['code'] == 'dev.location.transition':
                    from protocol import decode, TRANSITION_VALIDATOR
                    transition = decode(p['message'].encode())
                    TRANSITION_VALIDATOR.validate(transition)
                    self.emit({'type': 'transition', **transition})
                    if transition['phase'] == 'departing' and self.director:
                        self.spawn(self.overlay(False))
                else:
                    self.emit({'type': 'notice', **p})
            elif msg['method'] == 'world.metadata':
                self.metadata = p
                self.emit({'type': 'metadata', **p})
            elif msg['method'] == 'ui.opened':
                if p['leaseId'] == self.lease and p['outputId'] == self.output and p['panel'] == 'director':
                    self.spawn(self.overlay(True))
            elif msg['method'] == 'state.delta':
                if p['subscriptionId'] != self.subscription or p['sessionId'] != self.session:
                    raise ValueError('delta identity mismatch')
                if self.resyncing:
                    continue
                if p['baseRevision'] != self.revision or p['revision'] <= self.revision:
                    self.resyncing = True
                    self.spawn(self.resync())
                    continue
                self.state = {**self.state, **p['changes']}
                self.revision = p['revision']
                self.publish()
                self.spawn(self.reconcile())

    def spawn(self, coro):
        task = asyncio.create_task(coro)
        self.tasks.add(task)
        def done(task):
            self.tasks.discard(task)
            if not task.cancelled() and task.exception():
                self.emit({'type': 'notice', 'level': 'warning', 'message': str(task.exception()), 'code': 'shell.operation'})
                # Resync failure must disconnect; never keep presenting stale state.
                if self.resyncing or task.get_coro().__name__ == 'resync':
                    if self.writer: self.writer.close()
        task.add_done_callback(done)
        return task

    async def heartbeat(self):
        while True:
            await asyncio.sleep(10)
            await asyncio.wait_for(self.call('session.ping', {}), 30)

    async def reconcile(self):
        async with self.ui_lock:
            if not self.ready or not self.state:
                return
            runtime = self.state['runtime']
            leases = self.state['shell']['leases']
            own = next((v for v in leases if v['id'] == self.lease), None)
            if own: self.lease_seen = True
            invalid = self.lease and (self.output not in runtime['outputs'] or self.bindings.get(self.output) not in self.screens or
                                      (self.lease_seen and not own) or
                                      (own and self.output not in own['outputs']))
            if invalid or not runtime['active']:
                self.director = False
                self.emit({'type': 'director', 'open': False})
                if self.lease and 'shell.release' in self.hello['methods']:
                    with contextlib.suppress(RuntimeError):
                        await self.call('shell.release', {'leaseId': self.lease})
                self.lease = self.output = None
                self.lease_seen = False
                self.publish()
                return
            # A cleared exclusive flag means lock/exit/lease loss: unmap immediately.
            if self.director and self.revision >= self.overlay_revision and own and not any(v['outputId'] == self.output and v['exclusiveInput'] for v in own['overlays']):
                self.director = False
                self.emit({'type': 'director', 'open': False})
            target = next((v for v in runtime['outputs'] if self.bindings.get(v) in self.screens), None)
            if not self.lease and target and not self.claim_blocked and 'shell.claim' in self.hello.get('methods', []):
                try:
                    result = await self.call('shell.claim', {'outputs': [target]})
                except RuntimeError:
                    self.claim_blocked = True  # No fight/retry loop against another shell.
                    raise
                self.lease, self.output = result['leaseId'], target
                self.lease_seen = any(v['id'] == self.lease for v in self.state['shell']['leases'])
                self.publish()

    async def overlay(self, visible):
        async with self.ui_lock:
            if not self.lease or not self.ready:
                raise RuntimeError('Director unavailable: no authenticated output lease')
            if not visible:
                self.director = False
                self.emit({'type': 'director', 'open': False})
            try:
                result = await self.call('shell.overlay', {'leaseId': self.lease, 'outputId': self.output,
                                                           'visible': visible, 'exclusiveInput': visible})
            except Exception:
                # Closing a failed grab must clear authority even if its RPC fails.
                if not visible and self.writer: self.writer.close()
                raise
            # State may lag a committed reply; only a later authoritative delta can revoke.
            if visible and self.lease and self.state['runtime']['active']:
                self.overlay_revision = result['revision']
                self.director = True
                self.emit({'type': 'director', 'open': True, 'revision': result['revision']})

    async def run(self):
        backoff = .25
        while not self.stopping:
            self.tasks = set()
            self.emit({'type': 'connection', 'status': 'connecting'})
            reader_task = heartbeat = None
            try:
                token = await self.token_source() if self.token_source else None
                info = os.lstat(self.path)
                if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
                    raise ValueError('Core socket must be an owned 0600 socket, without symlinks')
                reader, self.writer = await asyncio.open_unix_connection(self.path)
                peer = self.writer.get_extra_info('socket').getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
                if struct.unpack('3i', peer)[1] != os.getuid():
                    raise ValueError('Core peer UID mismatch')
                reader_task = asyncio.create_task(self.receive(reader))
                params = {'protocols': [self.protocol], 'client': {'id': 'com.hyprune.shell', 'name': 'Hyprune shell'}, 'capabilities': GRANTS}
                if token: params['token'] = token
                self.hello = await self.call('session.hello', params, bootstrap=True)
                if self.hello['protocol'] != self.protocol: raise ValueError('protocol mismatch')
                self.session = self.hello['sessionId']
                self.emit({'type': 'hello', **self.hello, 'missing': [v for v in REQUIRED if v not in self.hello['methods']]})
                result = await self.call('state.subscribe', {'topics': ['state']})
                # Receive may observe queued deltas immediately after resolving this response.
                self.subscription = result['subscriptionId']
                self.ready = True
                self.emit({'type': 'connection', 'status': 'live'})
                try:
                    await self.reconcile()
                except RuntimeError as error:
                    self.emit({'type':'notice','level':'warning','code':'shell.lease','message':str(error)})
                backoff = .25
                heartbeat = asyncio.create_task(self.heartbeat())
                done, _ = await asyncio.wait([reader_task, heartbeat], return_when=asyncio.FIRST_COMPLETED)
                for task in done: task.result()
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self.emit({'type': 'connection', 'status': 'disconnected', 'message': str(error)})
            finally:
                self.ready = self.director = False
                self.state = None
                self.lease = self.output = self.subscription = self.session = None
                self.lease_seen = self.claim_blocked = False
                self.hello = {}
                self.emit({'type': 'director', 'open': False})
                self.publish()
                for task in [reader_task, heartbeat, *self.tasks]:
                    if task: task.cancel()
                await asyncio.gather(*(t for t in [reader_task, heartbeat, *self.tasks] if t), return_exceptions=True)
                for future in self.pending.values():
                    if not future.done(): future.set_exception(ConnectionError('Connection lost; action outcome unknown'))
                if self.writer:
                    self.writer.close()
                    with contextlib.suppress(Exception): await self.writer.wait_closed()
                self.writer = None
            await asyncio.sleep(backoff * random.uniform(.8, 1.2))
            backoff = min(backoff * 2, 10)

    async def shutdown(self):
        self.stopping = True
        if self.writer and self.ready:
            with contextlib.suppress(Exception):
                await asyncio.wait_for(self.overlay(False), 2)
            if self.lease:
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(self.call('shell.release', {'leaseId': self.lease}), 2)
            if self.subscription:
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(self.call('state.unsubscribe', {'subscriptionId': self.subscription}), 2)
