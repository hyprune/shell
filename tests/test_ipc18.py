import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bridge'))
from protocol import VALIDATORS, SUPPORTED_PROTOCOLS  # noqa: E402


class Ipc18(unittest.TestCase):
    """IPC 0.18: automatic (null) offload cap up to 1000 W and offload_device."""

    def request(self, patch):
        return {'jsonrpc': '2.0', 'id': 'o', 'method': 'graphics.set', 'params': {'patch': patch}}

    def test_offload_cap_and_device_patches(self):
        self.assertIn('0.18', SUPPORTED_PROTOCOLS)
        for patch in [{'offload_power_cap_w': None}, {'offload_power_cap_w': 350}, {'offload_device': 'auto'},
                      {'offload_device': '0000:02:00.0'}]:
            VALIDATORS['0.18'].validate(self.request(patch))
            with self.assertRaises(Exception):
                VALIDATORS['0.17'].validate(self.request(patch))
        for patch in [{'offload_power_cap_w': 2000}, {'offload_device': 'renderD129'}, {'offload_device': None}]:
            with self.assertRaises(Exception):
                VALIDATORS['0.18'].validate(self.request(patch))


if __name__ == '__main__':
    unittest.main()
