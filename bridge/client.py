"""Connection-scoped authority, snapshot ordering and lease lifecycle."""
import asyncio
import contextlib
import itertools
import json
from jsonschema.exceptions import ValidationError, best_match
import random
import time
import os
from pathlib import Path
from diagnostics import diagnostic
from protocol import read_packet, decode
import socket
import stat
import struct
from protocol import frame, read_frame, validate_response, VALIDATORS, SUPPORTED_PROTOCOLS, at_least


class OutgoingInvalid(ValueError):
    """A request this shell built does not match the negotiated protocol (never sent)."""


class CoreError(RuntimeError):
    """A JSON-RPC error from core. str() stays "<code>: <message>"; data keeps the
    validated error.data (IPC 0.22: {retryable, rule?})."""

    def __init__(self, code, message, data=None):
        super().__init__(str(code) + ': ' + message)
        self.code, self.message, self.data = code, message, data or {}

    @property
    def rule(self):
        return self.data.get('rule')

GRANTS = ['state.read', 'world.control', 'surface.control', 'movement.control', 'shell.control', 'runtime.control']
# Grants that exist only from a protocol on: older cores reject unknown capabilities.
VERSIONED_GRANTS = [(6, 'input.control'), (21, 'quest.control'), (22, 'objects.control')]
# RFC-0012 presentation hints (IPC 0.21): forwarded to QML, never replayed.
QUEST_EVENTS = ['quest.progress', 'focus.phase']


def capabilities(protocol):
    """The hello capabilities for the offered protocol."""
    return GRANTS + [grant for minor, grant in VERSIONED_GRANTS if at_least(protocol, minor)]
REQUIRED = ['session.hello', 'session.ping', 'state.subscribe', 'state.snapshot', 'state.unsubscribe',
            'shell.claim', 'shell.release', 'shell.overlay', 'surface.focus', 'movement.set', 'world.load', 'runtime.exit']

class QuarantinedFrame(RuntimeError):
    pass


class Client:
    def __init__(self, path, emit, token_source=None, bindings=None, protocol='0.2', client_id='com.hyprune.shell'):
        self.path, self.emit, self.token_source = path, emit, token_source
        self.bindings = bindings or {}
        if protocol not in SUPPORTED_PROTOCOLS: raise ValueError('Unsupported core protocol')
        self.protocol = protocol
        self.client_id = client_id
        self.validator = VALIDATORS[protocol]
        self.wayland_pid = None
        self.worlds = []
        self.native_transition = None
        self.native_hint = None
        self.transition_signature = None
        self.metadata = None
        self.hold_signature = object()
        self.hud_subscription = None
        self.hud_sequence = -1
        self.hud_times = {}
        self.bound_child = None
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
        self.note_id = None  # capture awaiting a note (IPC 0.17 prompt); owns exclusive input
        # IPC 0.23: the open character choice list (npcs.interaction type choose) shown with
        # the keyboard, keyed by object and choices; choice_grab: this prompt took exclusive input.
        self.choice_key = None
        self.choice_grab = False
        self.overlay_revision = -1
        self.ui_epoch = 0
        self.ready = False
        self.stopping = False
        self.write_lock = asyncio.Lock()
        self.ui_lock = asyncio.Lock()
        self.lease_seen = False
        self.claim_blocked = False
        self.stale_lease = None  # a release core refused while the session was locked
        self.tasks = set()
        self.invalid_frames = 0
        self.last_invalid_log = float('-inf')
        self.clock_offset = None  # core monotonic ms minus local wall-clock ms (QML Date.now())

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
                try:
                    packet = frame({'jsonrpc': '2.0', 'id': rid, 'method': method, 'params': params}, self.validator)
                except ValidationError as error:
                    raise OutgoingInvalid(method) from error
                if self.writer.transport.get_write_buffer_size() + len(packet) > 4 * 1024 * 1024:
                    self.writer.close()
                    raise ConnectionError('Core write queue overflow')
                self.writer.write(packet)
                await asyncio.wait_for(self.writer.drain(), 10)
            return await asyncio.wait_for(future, 35 if not bootstrap else 5)
        finally:
            self.pending.pop(rid, None)
            self.pending_methods.pop(rid, None)
            if future.done() and not future.cancelled(): future.exception()  # Drain errors during shutdown cancellation.

    def publish(self):
        self.emit({'type': 'state', 'state': self.state, 'revision': self.revision,
                   'lease': self.lease, 'output': self.output,
                   'screen': self.bindings.get(self.output), 'director': self.director})
        self.present_location()
        self.publish_hold()

    def publish_hold(self, force=False):
        holds = self.state.get('keymap', {}).get('holds', []) if self.state and at_least(self.protocol, 8) else []
        hold = next((h for h in holds if h['action'] == 'menu'), None)
        signature = json.dumps(hold, sort_keys=True)
        if not force and signature == self.hold_signature:
            return
        self.hold_signature = signature
        timing = None
        if hold:
            remaining = max(0, min(hold['durationMs'], hold['startedAtMs'] + hold['durationMs'] - time.monotonic() * 1000))
            timing = {**hold, 'remainingMs': remaining, 'progress': 1 - remaining / hold['durationMs']}
        self.emit({'type': 'menu.hold', 'hold': timing})

    def publish_clock(self, core_ms=None, wall_ms=None):
        """Core's monotonic clock (keymap holds, focus phases) relative to QML's Date.now().
        A session.ping sample wins; before it, the local CLOCK_MONOTONIC (same host)."""
        if core_ms is None:
            offset = time.monotonic() * 1000 - time.time() * 1000
        else:
            offset = core_ms - wall_ms
        if self.clock_offset is not None and abs(offset - self.clock_offset) < 2: return
        self.clock_offset = offset
        self.emit({'type': 'clock', 'offsetMs': round(offset, 1)})

    async def ping(self):
        before = time.time() * 1000
        result = await self.call('session.ping', {})
        after = time.time() * 1000
        if after - before < 1000:  # a slow round trip is a poor sample
            self.publish_clock(result['monotonicMs'], (before + after) / 2)
        return result

    def present_location(self, hint=None):
        # Core emits loading before a pending RPC returns. A validated hint can
        # present that phase without patching state. Arrival still waits for its
        # committed baseline revision in QML; gaps/reconnect use the snapshot.
        if not at_least(self.protocol, 2): return
        if hint is not None:
            self.native_hint = hint
        if self.native_hint and self.native_hint['revision'] <= self.revision:
            self.native_hint = None
        transition = self.native_hint or (hint if hint is not None else self.state.get('location', {}).get('transition') if self.state else None)
        revision = transition.get('revision', self.revision) if transition else self.revision
        eligible = self.ready and self.lease and self.state and self.state['runtime']['active']
        if not eligible or not transition or transition['outputId'] != self.output:
            if self.native_transition: self.emit({'type': 'transition.clear'})
            self.native_transition = self.transition_signature = self.native_hint = None
            return
        signature = json.dumps({k:v for k,v in transition.items() if k not in ['sessionId','revision']}, sort_keys=True)
        if signature == self.transition_signature: return
        self.transition_signature = signature
        phase = transition['phase']
        new = not self.native_transition or self.native_transition['id'] != transition['id']
        if new and phase in ['arrived', 'cancelled', 'failed']: return
        target = transition['to']
        if new:
            name = 'Selected coordinate'
            world_id = target.get('worldId') or self.state['world']['id']
            world = next((w for w in self.worlds if w['id'] == world_id), None)
            if 'worldId' in target:
                name = world['name'] if world else next((w['label'] for w in self.state.get('workspaces', {}).get('locations', []) if w['worldId'] == world_id), world_id.rsplit('.', 1)[-1].replace('-', ' ').replace('_', ' ').title())
            elif 'zoneId' in target:
                zone = next((z for z in self.state['location']['zones'] if z['id'] == target['zoneId']), None)
                name = zone['name'] if zone else target['zoneId']
            else:
                spawn = next((s for s in world['spawns'] if [s['pose']['position'][0], s['pose']['position'][1] + 1.7, s['pose']['position'][2]] == target['position']), None) if world else None
                if spawn: name = spawn['id'].replace('-', ' ').title()
                if at_least(self.protocol, 3):
                    place = next((p for p in self.state.get('spatial', {}).get('world', {}).get('places', []) if all(abs(a-b)<.01 for a,b in zip(p['position'],target['position']))), None)
                    if place: name = place['name'].replace('-', ' ').title()
            self.native_transition = {'id': transition['id'],
                                      'to': {'id': world_id, 'name': name, 'subtitle': 'WORLD TRANSIT' if 'worldId' in target else (world['name'].upper() if world else 'LOCATION')}}
            self.emit({'type': 'transition', 'id': transition['id'], 'phase': 'departing',
                       'progress': transition['progress'] or 0, 'to': self.native_transition['to'],
                       'revision': revision, 'indeterminate': transition['progress'] is None})
            if self.director: self.spawn(self.overlay(False))
        if 'worldId' in target and self.native_transition:
            current = self.state.get('spatial', {}).get('world')
            known = next((w for w in self.worlds if w['id'] == target['worldId']), None)
            if current and current['id'] == target['worldId']:
                self.native_transition['to']['name'] = current['name']
            elif known:
                self.native_transition['to']['name'] = known['name']
        mapped = {'loading': 'loading', 'departing': 'departing', 'travelling': 'transit',
                  'arrived': 'arrived', 'cancelled': 'failed', 'failed': 'failed'}[phase]
        if phase == 'travelling' and transition['progress'] >= .82: mapped = 'approach'
        if phase != 'departing' or not new:
            self.emit({'type': 'transition', 'id': transition['id'], 'phase': mapped,
                       'progress': transition['progress'] or 0, 'to': self.native_transition['to'],
                       'revision': revision, 'indeterminate': transition['progress'] is None})

    def snapshot(self, snapshot):
        if snapshot['sessionId'] != self.session:
            raise ValueError('snapshot belongs to another session')
        self.state = snapshot['state']
        self.revision = snapshot['revision']
        self.publish()

    async def resync(self):
        delay = .25
        try:
            while True:
                try:
                    await self.call('state.snapshot', {'subscriptionId': self.subscription})
                    break
                except (QuarantinedFrame, asyncio.TimeoutError):
                    # A persistently bad snapshot must not consume credentials or
                    # spin. Keep the connection reader alive for a repaired state.
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 5)
        finally:
            self.resyncing = False
        await self.reconcile()

    def request_resync(self):
        if self.subscription and not self.resyncing:
            self.resyncing = True
            self.native_hint = None
            self.emit({'type':'transition.clear'})
            self.spawn(self.resync())

    def quarantine(self, msg, error, method):
        self.invalid_frames += 1
        now = time.monotonic()
        if now - self.last_invalid_log >= 5:
            self.last_invalid_log = now
            self.emit({**diagnostic(self.validator,msg,error,method),'count':self.invalid_frames})
        rid = msg.get('id') if isinstance(msg,dict) else None
        future = self.pending.get(rid) if isinstance(rid,str) else None
        if future and not future.done():
            future.set_exception(QuarantinedFrame('Core response quarantined; refreshing state'))
        self.request_resync()

    def reader_finished(self, task):
        if task.cancelled(): return
        error = task.exception()
        if error is not None:
            # Fail bootstrap/resync promptly if response validation or framing fails.
            for future in self.pending.values():
                if not future.done(): future.set_exception(error)

    async def receive(self, reader):
        while True:
            # Length/framing errors still disconnect: their next boundary is
            # unknown. A complete invalid body is safe to discard independently.
            data = await read_packet(reader)
            msg, method = None, None
            try:
                msg = decode(data)
                if isinstance(msg,dict):
                    rid = msg.get('id')
                    if isinstance(rid,str):method=self.pending_methods.get(rid)
                    elif isinstance(msg.get('method'),str) and msg['method']+'.notification' in self.validator.schema.get('$defs',{}):
                        method=msg['method']
                if isinstance(msg,dict) and 'id' not in msg and method:
                    self.validator.evolve(schema={'$ref':self.validator.schema['$id']+'#/$defs/'+method+'.notification'}).validate(msg)
                elif isinstance(msg,dict) and 'id' in msg and method and 'error' not in msg:
                    validate_response(msg,method,self.validator)
                else:
                    self.validator.validate(msg)
            except (ValidationError, ValueError) as error:
                self.quarantine(msg,error,method)
                continue
            if 'id' in msg:
                future = self.pending.get(msg['id'])
                if not future or future.done():
                    self.quarantine(msg,ValueError('unexpected response ID'),method)
                    continue
                if 'error' in msg:
                    err = msg['error']
                    future.set_exception(CoreError(err['code'], err['message'], err.get('data')))
                else:
                    method = self.pending_methods[msg['id']]
                    if method in ('state.subscribe','state.snapshot') and msg['result']['snapshot']['sessionId'] != self.session:
                        self.quarantine(msg,ValueError('snapshot identity mismatch'),method)
                        continue
                    if method == 'state.subscribe':
                        self.subscription = msg['result']['subscriptionId']
                        self.snapshot(msg['result']['snapshot'])
                    elif method == 'hud.subscribe':
                        self.hud_subscription = msg['result']['subscriptionId']
                    elif method == 'state.snapshot':
                        self.snapshot(msg['result']['snapshot'])
                        self.resyncing = False
                    future.set_result(msg['result'])
                continue
            if msg['method'] not in self.hello.get('events', []):
                self.quarantine(msg,ValueError('unadvertised event'),method)
                continue
            p = msg['params']
            if at_least(self.protocol, 2) and msg['method'] in ['location.transition', 'ui.opened', 'ui.closed', 'data.updated']:
                if p['sessionId'] != self.session or p['revision'] < self.revision:
                    continue  # Transient hints are not a replay log.
            if self.hud_event(msg['method'], p):
                continue
            if msg['method'] in QUEST_EVENTS:
                # Transient hints for toasts; state stays authoritative.
                if at_least(self.protocol, 21) and p['sessionId'] == self.session and self.ready:
                    self.emit({'type': msg['method'], 'value': p})
                continue
            if msg['method'] == 'session.revoked':
                raise RuntimeError('Session revoked: ' + p['reason'])
            if msg['method'] == 'runtime.notice':
                self.emit({'type': 'notice', **p})
            elif msg['method'] == 'capture.taken':
                self.spawn(self.capture_taken(p))
            elif msg['method'] == 'ui.opened':
                self.end_note('director')
                if p['leaseId'] == self.lease and p['outputId'] == self.output and p['panel'] in ['director', 'overview', 'map'] and (not at_least(self.protocol, 2) or p['revision'] >= self.overlay_revision):
                    self.emit({'type':'menu.panel','panel':p['panel']})
                    self.ui_epoch += 1
                    self.spawn(self.overlay(True, self.ui_epoch))
            elif msg['method'] == 'ui.closed':
                if p['leaseId'] == self.lease and p['outputId'] == self.output and p['revision'] >= self.overlay_revision:
                    self.end_note('dismissed')  # core's Escape (menu exit): no note
                    self.end_choice(dismiss=True)  # and closes a character's choice list
                    self.ui_epoch += 1
                    self.overlay_revision = p['revision']
                    self.director = False
                    self.emit({'type': 'director', 'open': False})
            elif msg['method'] == 'location.transition':
                if not self.resyncing: self.present_location(p)
            elif msg['method'] == 'state.delta':
                if p['subscriptionId'] != self.subscription or p['sessionId'] != self.session:
                    self.quarantine(msg,ValueError('delta identity mismatch'),method)
                    continue
                if self.resyncing:
                    continue
                if p['baseRevision'] != self.revision or p['revision'] <= self.revision:
                    self.request_resync()
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
                if task.get_coro().__name__ == 'resync':
                    if self.writer: self.writer.close()
        task.add_done_callback(done)
        return task

    async def heartbeat(self):
        while True:
            await asyncio.sleep(10)
            try:
                await asyncio.wait_for(self.ping(), 30)
            except QuarantinedFrame:
                continue

    async def reconcile(self):
        async with self.ui_lock:
            if not self.ready or not self.state or self.resyncing:
                return
            runtime = self.state['runtime']
            if at_least(self.protocol, 3) and self.state.get('spatial', {}).get('output'):
                descriptor = self.state['spatial']['output']
                self.bindings = {descriptor['id']: descriptor['name']}
                current = self.state['spatial'].get('world')
                if current:
                    known = next((w for w in self.worlds if w['id'] == current['id']), None)
                    if not known or known['name'] != current['name']:
                        self.worlds = [w for w in self.worlds if w['id'] != current['id']] + [{'id': current['id'], 'name': current['name'], 'spawns': []}]
                        self.emit({'type': 'catalog', 'worlds': self.worlds})
            leases = self.state['shell']['leases']
            own = next((v for v in leases if v['id'] == self.lease), None)
            if own: self.lease_seen = True
            invalid = self.lease and (self.output not in runtime['outputs'] or self.bindings.get(self.output) not in self.screens or
                                      (self.lease_seen and not own) or
                                      (own and self.output not in own['outputs']))
            if invalid or not runtime['active']:
                self.end_note('lost')
                self.end_choice()
                self.director = False
                self.emit({'type': 'director', 'open': False})
                if self.lease and 'shell.release' in self.hello['methods']:
                    try:
                        await self.call('shell.release', {'leaseId': self.lease})
                    except CoreError as error:
                        if error.code == -32005:
                            self.stale_lease = self.lease  # locked (core 0.8.2): give it back after the unlock
                    except RuntimeError:
                        pass
                self.lease = self.output = None
                self.lease_seen = False
                # Left world mode (a lock, display off, exit): the next entry may claim again.
                self.claim_blocked = False
                self.publish()
                return
            # A cleared exclusive flag means lock/exit/lease loss: unmap immediately.
            if self.note_id and self.revision >= self.overlay_revision and own and not any(v['outputId'] == self.output and v['exclusiveInput'] for v in own['overlays']):
                self.end_note('lost')
            if self.choice_grab and self.revision >= self.overlay_revision and own and not any(v['outputId'] == self.output and v['exclusiveInput'] for v in own['overlays']):
                self.end_choice()  # lock, exit or core's own close: the list goes, the key stays
            if self.director and self.revision >= self.overlay_revision and own and not any(v['outputId'] == self.output and v['exclusiveInput'] for v in own['overlays']):
                self.director = False
                self.emit({'type': 'director', 'open': False})
            target = next((v for v in runtime['outputs'] if self.bindings.get(v) in self.screens), None)
            if not self.lease and target and not self.claim_blocked and 'shell.claim' in self.hello.get('methods', []):
                if self.stale_lease:
                    stale, self.stale_lease = self.stale_lease, None
                    if any(v['id'] == stale for v in leases):
                        with contextlib.suppress(RuntimeError):
                            await self.call('shell.release', {'leaseId': stale})
                try:
                    result = await self.call('shell.claim', {'outputs': [target]})
                except RuntimeError:
                    self.claim_blocked = True  # No fight/retry loop against another shell.
                    raise
                self.lease, self.output = result['leaseId'], target
                self.lease_seen = any(v['id'] == self.lease for v in self.state['shell']['leases'])
                self.publish()

            if at_least(self.protocol, 9) and self.lease and self.wayland_pid and self.bound_child != (self.lease,self.wayland_pid):
                try:
                    await self.call('shell.bind', {'leaseId':self.lease,'pid':self.wayland_pid})
                except RuntimeError as error:
                    if 'no credential-matched HUD' in str(error): return  # Mapping races the first snapshot.
                    raise
                self.emit({'type':'hud.bound'})
                self.bound_child = (self.lease,self.wayland_pid)
            await self.sync_choice()

    def npc_interaction(self):
        """The running character interaction (IPC 0.23 npcs.interaction), or None."""
        if not at_least(self.protocol, 23) or not self.state: return None
        return (self.state.get('npcs') or {}).get('interaction')

    async def sync_choice(self):
        """A choice list (npcs.interaction type choose) takes the keyboard like the note
        prompt: exclusive input for the shell's Wayland child, then the list is shown. It is
        released when core ends the interaction. Called from reconcile (ui_lock held)."""
        current = self.npc_interaction()
        want = current if current and current['type'] == 'choose' and self.lease and self.state['runtime']['active'] else None
        key = json.dumps([want['objectId'], want['choices']], sort_keys=True) if want else None
        if key == self.choice_key:
            return
        if key is None:
            grabbed = self.choice_grab
            self.end_choice()
            self.choice_key = None
            if grabbed and self.lease and not self.director and not self.note_id:
                result = await self.call('shell.overlay', {'leaseId': self.lease, 'outputId': self.output,
                                                           'visible': False, 'exclusiveInput': False})
                self.overlay_revision = max(self.overlay_revision, result['revision'])
            return
        self.choice_key = key
        if not self.choice_grab and not self.director and not self.note_id:
            # Hold the keyboard before the list is shown: number keys and Enter go to it.
            if not self.wayland_pid: raise RuntimeError('Wayland child unavailable')
            await self.call('shell.bind', {'leaseId': self.lease, 'pid': self.wayland_pid})
            result = await self.call('shell.overlay', {'leaseId': self.lease, 'outputId': self.output,
                                                       'visible': True, 'exclusiveInput': True})
            self.overlay_revision = max(self.overlay_revision, result['revision'])
            if self.choice_key != key: return  # ended meanwhile
            self.choice_grab = True
        self.emit({'type': 'interaction.prompt', 'value': want})

    def end_choice(self, dismiss=False):
        """Hide the choice list. dismiss: core's Escape closed the overlay, so the
        interaction is ended for core too (interaction.choose with null)."""
        if self.choice_grab or (dismiss and self.choice_key):
            self.emit({'type': 'interaction.prompt', 'value': None})
        self.choice_grab = False
        current = self.npc_interaction()
        if dismiss and self.choice_key and current and current['type'] == 'choose' and 'interaction.choose' in self.hello.get('methods', []):
            self.spawn(self.call('interaction.choose', {'objectId': current['objectId'], 'interactionId': None}))

    async def interaction_panel(self, object_id):
        """A character's panel interaction (IPC 0.23): open the Director, then end the
        interaction (interaction.choose with null). Only while core runs one for that object."""
        current = self.npc_interaction()
        if not current or current['type'] != 'panel' or current['objectId'] != object_id:
            raise ValueError('No panel interaction for ' + object_id)
        try:
            if self.lease and not self.director and 'ui.open' in self.hello.get('methods', []):
                await self.call('ui.open', {'leaseId': self.lease, 'outputId': self.output, 'panel': 'overview'})
        finally:
            await self.call('interaction.choose', {'objectId': object_id, 'interactionId': None})

    def hud_event(self, method, params):
        if method not in ['ui.hud.cycle','hud.frame','hud.pose','zone.entered','zone.exited','tool.changed']:
            return False
        if params['sessionId'] != self.session or not self.ready or self.resyncing:
            return True
        if method == 'ui.hud.cycle':
            # Concept selection belongs to Settings, including on legacy cores.
            return True
        if params['subscriptionId'] != self.hud_subscription or params['monotonicMs'] <= self.hud_times.get(method,-1):
            return True
        if method == 'hud.pose' and (params['outputId'] != self.output or not self.state or params['worldId'] != (self.state.get('world') or {}).get('id')):
            return True
        self.hud_times[method] = params['monotonicMs']
        self.emit({'type':method,'value':params})
        return True

    async def overlay(self, visible, expected_epoch=None):
        async with self.ui_lock:
            if expected_epoch is not None and expected_epoch != self.ui_epoch:
                return
            if not self.lease or not self.ready:
                raise RuntimeError('Overview unavailable: no authenticated output lease')
            if not visible:
                self.end_note('lost')
                self.ui_epoch += 1
                self.director = False
                self.emit({'type': 'director', 'open': False})
            epoch = self.ui_epoch
            try:
                if not visible and at_least(self.protocol, 2) and 'ui.close' in self.hello['methods']:
                    result = await self.call('ui.close', {'leaseId': self.lease, 'outputId': self.output})
                else:
                    if visible and at_least(self.protocol, 3):
                        if not self.wayland_pid: raise RuntimeError('Wayland child unavailable')
                        await self.call('shell.bind', {'leaseId': self.lease, 'pid': self.wayland_pid})
                    result = await self.call('shell.overlay', {'leaseId': self.lease, 'outputId': self.output,
                                                               'visible': visible, 'exclusiveInput': visible})
            except Exception:
                # Closing a failed grab must clear authority even if its RPC fails.
                if not visible and self.writer: self.writer.close()
                raise
            self.overlay_revision = max(self.overlay_revision, result['revision'])
            # State may lag a committed reply; only a later authoritative delta can revoke.
            if visible and epoch == self.ui_epoch and self.lease and self.state['runtime']['active']:
                self.director = True
                self.emit({'type': 'director', 'open': True, 'revision': result['revision']})
            elif visible and epoch != self.ui_epoch:
                self.spawn(self.overlay(False))

    def end_note(self, reason):
        """Close the note prompt (no note is written here)."""
        if self.note_id:
            self.note_id = None
            self.emit({'type': 'capture.prompt', 'captureId': None, 'reason': reason})

    async def capture_taken(self, p):
        """U in navigation opens a note prompt with exclusive keyboard; U again (the
        mode's capture binding) while it is open moves the prompt to the new capture."""
        async with self.ui_lock:
            if not self.lease or not self.ready or not self.state or not self.state['runtime']['active']:
                return
            previous = self.note_id
            if previous is None and (p['mode'] != 'world' or self.director):
                return  # Busy in an app, focus, free cursor or the Director: capture only.
            self.note_id = p['captureId']
            if previous is None:
                # Hold the keyboard before the prompt is shown: anything typed once it is
                # visible goes to the prompt, never to world bindings (F, E, X, 1-5).
                try:
                    if not self.wayland_pid: raise RuntimeError('Wayland child unavailable')
                    await self.call('shell.bind', {'leaseId': self.lease, 'pid': self.wayland_pid})
                    result = await self.call('shell.overlay', {'leaseId': self.lease, 'outputId': self.output,
                                                               'visible': True, 'exclusiveInput': True})
                    self.overlay_revision = max(self.overlay_revision, result['revision'])
                except Exception:
                    self.note_id = None
                    raise
                if self.note_id != p['captureId']:
                    return  # Closed meanwhile (lease loss, Director).
            # QML saves the previous capture's text as-is before clearing the field.
            self.emit({'type': 'capture.prompt', 'captureId': p['captureId'], 'previous': previous})

    async def capture_note(self, capture_id, note, release=True):
        """Enter: write the note (empty allowed); release=False keeps input for the next prompt."""
        if note is not None:
            await self.call('capture.annotate', {'captureId': capture_id, 'note': note})
        if release:
            await self.capture_release(capture_id)

    async def capture_release(self, capture_id):
        async with self.ui_lock:
            if self.note_id != capture_id:
                return  # Superseded by a newer capture or already closed.
            self.end_note('closed')
            if self.lease and self.ready and not self.director:
                result = await self.call('shell.overlay', {'leaseId': self.lease, 'outputId': self.output,
                                                           'visible': False, 'exclusiveInput': False})
                self.overlay_revision = max(self.overlay_revision, result['revision'])

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
                reader_task.add_done_callback(self.reader_finished)
                params = {'protocols': [self.protocol], 'client': {'id': self.client_id, 'name': 'Hyprune shell'}, 'capabilities': capabilities(self.protocol)}
                if token: params['token'] = token
                self.hello = await self.call('session.hello', params, bootstrap=True)
                if self.hello['protocol'] != self.protocol: raise ValueError('protocol mismatch')
                self.session = self.hello['sessionId']
                self.emit({'type': 'hello', **self.hello, 'missing': [v for v in REQUIRED if v not in self.hello['methods']]})
                result = await self.call('state.subscribe', {'topics': ['state']})
                # Receive may observe queued deltas immediately after resolving this response.
                self.subscription = result['subscriptionId']
                self.ready = True
                self.publish_clock()
                self.emit({'type': 'connection', 'status': 'live'})
                try:
                    await self.reconcile()
                except RuntimeError as error:
                    self.emit({'type':'notice','level':'warning','code':'shell.lease','message':str(error)})
                if at_least(self.protocol,9) and 'hud.subscribe' in self.hello['methods']:
                    await self.call('hud.subscribe',{'topics':['hud.frame','hud.pose','zone.entered','zone.exited','tool.changed']})
                if at_least(self.protocol, 21):
                    with contextlib.suppress(RuntimeError, QuarantinedFrame, asyncio.TimeoutError):
                        await asyncio.wait_for(self.ping(), 5)  # focus countdowns need the offset now
                backoff = .25
                heartbeat = asyncio.create_task(self.heartbeat())
                done, _ = await asyncio.wait([reader_task, heartbeat], return_when=asyncio.FIRST_COMPLETED)
                for task in done: task.result()
            except asyncio.CancelledError:
                raise
            except Exception as error:
                if isinstance(error,ValidationError): error = best_match([error])
                message = ('Invalid core frame at ' + '/'.join(map(str,error.absolute_path)) + ': ' + error.validator) if isinstance(error,ValidationError) else str(error)
                self.emit({'type': 'connection', 'status': 'disconnected', 'message': message})
            finally:
                self.hud_subscription = self.bound_child = None
                self.hud_sequence = -1
                self.hud_times = {}
                self.clock_offset = None
                self.ready = self.director = False
                self.end_note('lost')
                self.end_choice()
                self.choice_key = None
                self.resyncing = False
                self.overlay_revision = -1
                self.ui_epoch += 1
                self.state = None
                self.lease = self.output = self.subscription = self.session = None
                self.lease_seen = self.claim_blocked = False
                self.stale_lease = None
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
