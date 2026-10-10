"""IPC 0.17 capture note prompt in the bridge: open, Enter, Esc, U again, ordering."""
import asyncio
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bridge'))
from client import Client  # noqa: E402
from protocol import VALIDATORS, SUPPORTED_PROTOCOLS  # noqa: E402


class Prompt(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.events, self.calls = [], []
        self.client = Client('/unused', self.events.append, protocol='0.17')
        c = self.client
        c.lease, c.output, c.ready, c.wayland_pid = 'lease-1', 'world', True, 42
        c.state = {'runtime': {'active': True}}
        c.hello = {'methods': ['capture.annotate', 'shell.overlay', 'shell.bind'], 'events': ['capture.taken']}
        self.revision = 0
        async def call(method, params, **kw):
            self.calls.append((method, params))
            self.revision += 1
            return {'revision': self.revision}
        c.call = call

    def prompts(self):
        return [e for e in self.events if e['type'] == 'capture.prompt']

    def taken(self, n, mode='world'):
        return {'captureId': 'capture-%d' % n, 'timestampMs': n, 'mode': mode, 'sessionId': 's', 'revision': 1}

    async def test_world_capture_opens_prompt_with_exclusive_input(self):
        await self.client.capture_taken(self.taken(1))
        self.assertEqual(self.client.note_id, 'capture-1')
        self.assertEqual(self.prompts()[-1], {'type': 'capture.prompt', 'captureId': 'capture-1', 'previous': None})
        self.assertEqual([m for m, _ in self.calls], ['shell.bind', 'shell.overlay'])
        self.assertEqual(self.calls[-1][1]['visible'], True)
        self.assertEqual(self.calls[-1][1]['exclusiveInput'], True)

    async def test_prompt_is_shown_only_after_the_keyboard_grab(self):
        seen = []
        self.client.emit = lambda e: seen.append([m for m, _ in self.calls]) if e['type'] == 'capture.prompt' else None
        await self.client.capture_taken(self.taken(1))
        self.assertEqual(seen, [['shell.bind', 'shell.overlay']])  # keys typed once visible reach the prompt

    async def test_enter_writes_note_then_releases_input(self):
        await self.client.capture_taken(self.taken(1))
        await self.client.capture_note('capture-1', 'rail clips the stair')
        self.assertEqual(self.calls[-2], ('capture.annotate', {'captureId': 'capture-1', 'note': 'rail clips the stair'}))
        self.assertEqual(self.calls[-1][0], 'shell.overlay')
        self.assertEqual((self.calls[-1][1]['visible'], self.calls[-1][1]['exclusiveInput']), (False, False))
        self.assertIsNone(self.client.note_id)
        self.assertEqual(self.prompts()[-1]['captureId'], None)

    async def test_empty_enter_still_annotates(self):
        await self.client.capture_taken(self.taken(1))
        await self.client.capture_note('capture-1', '')
        self.assertIn(('capture.annotate', {'captureId': 'capture-1', 'note': ''}), self.calls)

    async def test_escape_from_core_writes_nothing(self):
        await self.client.capture_taken(self.taken(1))
        self.client.end_note('dismissed')  # ui.closed after core's menu exit
        self.assertNotIn('capture.annotate', [m for m, _ in self.calls])
        self.assertEqual(self.prompts()[-1], {'type': 'capture.prompt', 'captureId': None, 'reason': 'dismissed'})
        await self.client.capture_release('capture-1')  # a late dismiss is a no-op
        self.assertEqual([m for m, _ in self.calls].count('shell.overlay'), 1)

    async def test_u_again_moves_prompt_and_keeps_input(self):
        await self.client.capture_taken(self.taken(1))
        await self.client.capture_taken(self.taken(2, mode='menu'))  # Super+U while the prompt is open
        self.assertEqual(self.prompts()[-1], {'type': 'capture.prompt', 'captureId': 'capture-2', 'previous': 'capture-1'})
        await self.client.capture_note('capture-1', 'first', release=False)  # QML saves the old text
        await self.client.capture_taken(self.taken(3, mode='menu'))
        await self.client.capture_note('capture-2', '', release=False)
        await self.client.capture_note('capture-3', 'third')
        annotated = [p['captureId'] + ':' + p['note'] for m, p in self.calls if m == 'capture.annotate']
        self.assertEqual(annotated, ['capture-1:first', 'capture-2:', 'capture-3:third'])
        overlays = [(p['visible'], p['exclusiveInput']) for m, p in self.calls if m == 'shell.overlay']
        self.assertEqual(overlays, [(True, True), (False, False)])  # one grab, one release
        self.assertIsNone(self.client.note_id)

    async def test_busy_modes_and_director_capture_without_prompt(self):
        for mode in ['interactive', 'focus', 'cursor', 'menu']:
            await self.client.capture_taken(self.taken(1, mode=mode))
        self.client.director = True
        await self.client.capture_taken(self.taken(2))
        self.assertEqual(self.calls, [])
        self.assertEqual(self.prompts(), [])

    async def test_director_replaces_prompt(self):
        await self.client.capture_taken(self.taken(1))
        self.client.end_note('director')
        self.assertEqual(self.prompts()[-1]['reason'], 'director')
        self.assertIsNone(self.client.note_id)

    def test_wire_contract_is_0_17_only(self):
        self.assertIn('0.17', SUPPORTED_PROTOCOLS)
        self.assertEqual(sorted(VALIDATORS, key=lambda v: int(v.split('.')[1])), list(SUPPORTED_PROTOCOLS))
        frame = {'jsonrpc': '2.0', 'id': 'n', 'method': 'capture.annotate', 'params': {'captureId': 'capture-1', 'note': 'Brücke 橋'}}
        VALIDATORS['0.17'].validate(frame)
        for old in ['0.16', '0.2']:
            with self.assertRaises(Exception):
                VALIDATORS[old].validate(frame)
        with self.assertRaises(Exception):
            VALIDATORS['0.17'].validate({**frame, 'params': {'captureId': 'capture-1', 'note': 'x' * 1001}})


if __name__ == '__main__':
    unittest.main()
