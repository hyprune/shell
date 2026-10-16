"""RFC-0016 (IPC 0.33) in the shell: an assistant's pairing request (the Director's prompt: Allow
once, Always allow, Deny; the HUD banner), the Assistant chip and Connected assistants (Pause,
Disconnect, Revoke). Pure helpers in qml/Assistants.js run with node."""
import json
from pathlib import Path
import subprocess
import unittest
ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'qml/Assistants.js').read_text()


def call(name, *args):
    return json.loads(subprocess.check_output(['node', '-e', SRC + '\nconsole.log(JSON.stringify(' + name + '(' + ', '.join(json.dumps(a) for a in args) + ')));'], text=True))


REQUEST = {'requestId': 'p-0a1b2c3d', 'clientId': 'com.hyprune.mcp', 'clientName': 'Hyprune MCP server', 'agent': {'name': 'Example Chat', 'version': '1.4'},
           'profile': 'assistant', 'expiresInMs': 117400}
LIVE = {'actor': 'a1', 'clientId': 'com.hyprune.mcp', 'agent': {'name': 'Example Chat'}, 'profile': 'assistant', 'connectedMs': 125000, 'changes': 12,
        'action': 'placed cpu-tower', 'paused': False, 'remembered': True}


class Assistants(unittest.TestCase):
    def test_prompt(self):
        self.assertEqual(call('connectionsOf', {}), {'pending': [], 'live': [], 'approvals': []})
        self.assertEqual(call('promptTitle', REQUEST), 'Example Chat 1.4 wants to build in Hyprune')
        text = call('promptText', REQUEST)
        self.assertIn("can't see or use your windows", text)
        self.assertIn('what the assistant says it is', text)
        self.assertEqual(call('secondsLeft', REQUEST), 118)
        self.assertEqual(call('answerParams', REQUEST, 'always'), {'requestId': 'p-0a1b2c3d', 'decision': 'always'})
        self.assertEqual(call('bannerText', [REQUEST]), 'EXAMPLE CHAT 1.4 WANTS TO BUILD · OPEN THE DIRECTOR TO ANSWER')
        self.assertEqual(call('bannerText', []), '')

    def test_chip_and_rows(self):
        self.assertEqual(call('chipText', [LIVE]), 'ASSISTANT · EXAMPLE CHAT · 12 CHANGES')
        self.assertEqual(call('chipText', [dict(LIVE, paused=True, changes=1), LIVE]), 'ASSISTANT · EXAMPLE CHAT · 1 CHANGE · PAUSED · +1')
        self.assertEqual(call('chipDetail', [LIVE]), 'placed cpu-tower')
        row = call('liveRow', LIVE)
        self.assertEqual(row['line'], '12 changes · connected 2 min · always allowed')
        self.assertEqual(call('approvalRow', {'clientId': 'com.hyprune.mcp', 'agent': 'Tool X', 'profile': 'assistant', 'approvedAt': '2026-10-16T03:00:00Z'})['line'],
                         'Always allowed since 2026-10-16')

    def test_wiring(self):
        launch = (ROOT / 'bridge/launch.py').read_text()
        self.assertIn("CONNECTION_ACTIONS if at_least(protocol, 33)", launch)
        state = (ROOT / 'qml/ShellState.qml').read_text()
        for name in ['assistantAnswer', 'assistantPause', 'assistantDisconnect', 'assistantRevoke']:
            self.assertIn('function ' + name, state)
        self.assertIn('AssistantPrompt', (ROOT / 'qml/components/Director.qml').read_text())
        hud = (ROOT / 'qml/components/Hud.qml').read_text()
        self.assertIn('hudAssistantChip', hud)
        self.assertIn('hudAssistantBanner', hud)
        self.assertIn('builderAssistants', (ROOT / 'qml/components/DirectorBuilder.qml').read_text())


if __name__ == '__main__':
    unittest.main()
