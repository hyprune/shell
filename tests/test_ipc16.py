import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bridge'))
from protocol import VALIDATORS, SUPPORTED_PROTOCOLS, at_least  # noqa: E402


class Ipc16(unittest.TestCase):
    def test_upscaler_negotiation_and_validation(self):
        self.assertEqual(SUPPORTED_PROTOCOLS[-1], '0.16')
        self.assertTrue(at_least('0.16', 16))
        self.assertEqual(sorted(VALIDATORS, key=lambda v: int(v.split('.')[1])), list(SUPPORTED_PROTOCOLS))
        frame = {'jsonrpc': '2.0', 'id': 'u', 'method': 'graphics.set', 'params': {'patch': {'upscaler': 'bilinear'}}}
        VALIDATORS['0.16'].validate(frame)
        with self.assertRaises(Exception):
            VALIDATORS['0.15'].validate(frame)


if __name__ == '__main__':
    unittest.main()
