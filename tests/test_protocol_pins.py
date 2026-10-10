import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bridge'))
import protocol  # noqa: E402


class VendoredPins(unittest.TestCase):
    """IPC and world catalogs follow the vendored pins, never a hand list."""

    def pins(self, base, schema):
        return sorted((d.name[1:] for d in base.iterdir() if d.name.startswith('v0.') and (d / schema).exists()),
                      key=lambda v: int(v.split('.')[1]))

    def test_ipc_catalog_is_the_vendored_pins(self):
        pins = ['0.1', *self.pins(ROOT / 'protocol', 'ipc.schema.json')]
        self.assertEqual(list(protocol.SUPPORTED_PROTOCOLS), pins)
        self.assertEqual(list(protocol.VALIDATORS), pins)
        for version in pins[1:]:
            self.assertIs(getattr(protocol, 'V%d_VALIDATOR' % int(version.split('.')[1])), protocol.VALIDATORS[version])
        self.assertIn('anyOf', protocol.VALIDATORS['0.13'].schema)

    def test_world_catalog_is_the_vendored_pins(self):
        pins = ['0.1', '0.2', *self.pins(ROOT / 'protocol/worlds', 'world.schema.json')]
        self.assertEqual(list(protocol.WORLD_VALIDATORS), pins)


if __name__ == '__main__':
    unittest.main()
