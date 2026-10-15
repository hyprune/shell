"""IPC 0.29 (draft, motion feel): the debug recording (Ctrl+R). The bridge opens the note
prompt as a label prompt when a recording stops, Enter labels it (recording.label with the
shell version), an empty Enter or Esc keeps the time-only name; the HUD's REC indicator reads
state.recording. Input version 3 (Shift sprints, Ctrl goes down, Ctrl+R records) is a core keymap.

Wire checks run against the vendored 0.29 pin; 0.28 must refuse the new shapes."""
import asyncio
import hashlib
import json
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bridge'))
from client import Client, SHELL_VERSION, capabilities  # noqa: E402
from protocol import VALIDATORS, SUPPORTED_PROTOCOLS, frame  # noqa: E402

V29 = VALIDATORS['0.29']
V28 = VALIDATORS['0.28']
PATH = '/home/u/.local/state/hyprune/recordings/rec-20261015-101500.jsonl'
STATS = {'t': 5.0, 'windowS': 5.0, 'final': False, 'presents': 245, 'presentHz': 49.0, 'fps': 49.0,
         'frameMs': {'p50': 20.4, 'p95': 20.6, 'p99': 30.6, 'max': 40.8}, 'dtMs': {'mean': 20.4, 'std': .3, 'max': 30.6},
         'refreshMs': 10.207, 'missedVblanks': 245, 'hitches': []}


def recording(active, last=None):
    return {'active': active, 'startedAt': 123456 if active else None, 'path': PATH if active else None,
            'stats': STATS if active else None, 'last': last}


class Pin(unittest.TestCase):
    def test_vendored_pin(self):
        source = json.loads((ROOT / 'protocol/v0.29/SOURCE.json').read_text())
        self.assertEqual(source['protocol'], '0.29')
        self.assertEqual(source['file'], 'v0.29/ipc.schema.json')
        self.assertEqual(hashlib.sha256((ROOT / 'protocol/v0.29/ipc.schema.json').read_bytes()).hexdigest(), source['sha256'])
        self.assertIn('0.29', SUPPORTED_PROTOCOLS)
        self.assertEqual(capabilities('0.29'), capabilities('0.28'))

    def test_label_request_and_state(self):
        frame({'jsonrpc': '2.0', 'id': 'r', 'method': 'recording.label', 'params': {'label': 'pan test', 'meta': {'shell': {'version': SHELL_VERSION}}}}, V29)
        with self.assertRaises(Exception):
            frame({'jsonrpc': '2.0', 'id': 'r', 'method': 'recording.label', 'params': {'label': 'pan test'}}, V28)
        V29.evolve(schema={'$ref': V29.schema['$id'] + '#/$defs/recordingState'}).validate(recording(True))


class LabelPrompt(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.events, self.calls = [], []
        self.client = Client('/unused', self.events.append, protocol='0.29')
        c = self.client
        c.lease, c.output, c.ready, c.wayland_pid = 'lease-1', 'world', True, 42
        c.state = {'runtime': {'active': True}, 'recording': recording(True)}
        c.hello = {'methods': ['recording.label', 'capture.annotate', 'shell.overlay', 'shell.bind'], 'events': ['capture.taken']}
        self.revision = 0
        async def call(method, params, **kw):
            self.calls.append((method, params))
            self.revision += 1
            return {'revision': self.revision}
        c.call = call

    async def settle(self):
        for _ in range(5):
            await asyncio.sleep(0)

    def prompts(self):
        return [e for e in self.events if e['type'] == 'capture.prompt']

    async def test_stop_opens_the_label_prompt_and_enter_labels(self):
        self.client.recording_stopped(recording(True), recording(False, {'path': PATH, 'label': None}))
        await self.settle()
        self.assertEqual(self.prompts()[-1]['captureId'], 'recording:' + PATH)
        self.assertEqual([m for m, _ in self.calls], ['shell.bind', 'shell.overlay'])
        await self.client.capture_note('recording:' + PATH, '  pan test 98 Hz ')
        self.assertEqual(self.calls[-2], ('recording.label', {'label': 'pan test 98 Hz', 'meta': {'shell': {'version': SHELL_VERSION}}}))
        self.assertEqual((self.calls[-1][0], self.calls[-1][1]['exclusiveInput']), ('shell.overlay', False))

    async def test_empty_enter_or_escape_keeps_the_time_name(self):
        self.client.recording_stopped(recording(True), recording(False, {'path': PATH, 'label': None}))
        await self.settle()
        await self.client.capture_note('recording:' + PATH, '')
        self.assertNotIn('recording.label', [m for m, _ in self.calls])
        self.assertNotIn('capture.annotate', [m for m, _ in self.calls])

    async def test_no_prompt_without_a_stop_or_once_labelled(self):
        for before, after in [(None, recording(False, {'path': PATH, 'label': None})),
                              (recording(False), recording(False, {'path': PATH, 'label': None})),
                              (recording(True), recording(True)),
                              (recording(True), recording(False, {'path': PATH, 'label': 'walk'}))]:
            self.client.recording_stopped(before, after)
        await self.settle()
        self.assertEqual(self.prompts(), [])

    async def test_older_protocols_never_prompt(self):
        self.client.protocol = '0.28'
        self.client.recording_stopped(recording(True), recording(False, {'path': PATH, 'label': None}))
        await self.settle()
        self.assertEqual(self.prompts(), [])


class FeelSettings(unittest.TestCase):
    def test_ranges_defaults_and_patches_match_the_schema(self):
        import subprocess
        script = (ROOT / 'qml/PlayerSettings.js').read_text()
        js = lambda e: json.loads(subprocess.check_output(['node', '-e', script + '\nconsole.log(JSON.stringify(' + e + '));'], text=True))
        keys = js('FEEL_KEYS')
        self.assertEqual(keys, ['look_inertia', 'move_inertia', 'view_bob_roll', 'carry_turn', 'carry_follow'])
        props = V29.schema['$defs']['playerPatch']['properties']
        for key in keys:
            number = next(b for b in props[key]['anyOf'] if b.get('type') == 'number')
            self.assertEqual([number['minimum'], number['maximum']], js('RANGES.' + key), key)
        frame({'jsonrpc': '2.0', 'id': 'r', 'method': 'player.set', 'params': {'patch': js('DEFAULTS')}}, V29)
        frame({'jsonrpc': '2.0', 'id': 'r', 'method': 'player.set', 'params': {'patch': js('resetPatch(FEEL_KEYS)')}}, V29)
        self.assertEqual(js("patch(null, 'carry_turn', 0.1234)"), {'carry_turn': 0.123})
        self.assertEqual(js("[ms(0.11), feelText(FEEL[2], 0.4)]"), ['110 ms', '0.4°'])
        with self.assertRaises(Exception):
            frame({'jsonrpc': '2.0', 'id': 'r', 'method': 'player.set', 'params': {'patch': {'carry_turn': .2}}}, V28)

    def test_frame_pacing_choice(self):
        model = (ROOT / 'qml/SettingsModel.js').read_text()
        self.assertIn("{key: 'graphics.frame_pacing', category: 'display'", model)
        frame({'jsonrpc': '2.0', 'id': 'r', 'method': 'graphics.set', 'params': {'patch': {'frame_pacing': 'max_rate'}}}, V29)


class Qml(unittest.TestCase):
    def test_hud_and_prompt_wiring(self):
        hud = (ROOT / 'qml/components/Hud.qml').read_text()
        self.assertIn("objectName: 'hudRecording'", hud)
        self.assertIn('state.recording', hud)
        prompt = (ROOT / 'qml/components/NotePrompt.qml').read_text()
        self.assertIn('noteRecording', prompt)
        self.assertIn("readonly property bool noteRecording: notePrompt.indexOf('recording:') === 0",
                      (ROOT / 'qml/ShellState.qml').read_text())


if __name__ == '__main__':
    unittest.main()
