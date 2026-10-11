"""overlay.style is lease-scoped: no lease, nothing to send; a lost lease is not a warning."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bridge'))
from jsonschema.exceptions import ValidationError  # noqa: E402
from client import OutgoingInvalid  # noqa: E402
from launch import LEASE_LOST, action_notice, lease_params  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STYLE = {'style': {'fontFamily': 'DejaVu Sans Mono'}}


def action(method):
    return {'type': 'action', 'method': method, 'params': {}}


class LeaseStyleTests(unittest.TestCase):
    def test_style_waits_for_a_lease(self):
        self.assertIsNone(lease_params('overlay.style', STYLE, None))
        self.assertIsNone(lease_params('overlay.style', STYLE, ''))
        self.assertEqual(lease_params('overlay.style', STYLE, 'lease-1'), {**STYLE, 'leaseId': 'lease-1'})
        self.assertEqual(lease_params('graphics.get', {}, None), {})

    def test_lost_lease_is_not_a_warning(self):
        self.assertIsNone(action_notice(action('overlay.style'), RuntimeError('-32602: ' + LEASE_LOST)))
        notice = action_notice(action('graphics.set'), RuntimeError('-32602: ' + LEASE_LOST))
        self.assertEqual((notice['code'], notice['method']), ('shell.action', 'graphics.set'))

    def test_request_and_response_mismatches_are_told_apart(self):
        shell = action_notice(action('overlay.style'), OutgoingInvalid('overlay.style'))
        core = action_notice(action('overlay.style'), ValidationError('bad'))
        self.assertEqual(shell['message'], 'Shell request does not match the negotiated protocol.')
        self.assertEqual(core['message'], 'Core response does not match the negotiated protocol.')

    def test_theme_changes_restyle_only_with_a_lease(self):
        qml = (ROOT / 'qml/ShellState.qml').read_text()
        self.assertIn('function onLightChanged() { if (root.lease) root.applyCoreStyle(); }', qml)


if __name__ == '__main__':
    unittest.main()
