import hashlib, json, pathlib, sys, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bridge'))
from protocol import WORLD_VALIDATORS  # noqa: E402


class WorldFormats(unittest.TestCase):
    def test_every_vendored_world_pin_is_accepted(self):
        pins = {d.name[1:] for d in (ROOT / 'protocol' / 'worlds').iterdir() if (d / 'world.schema.json').exists()}
        self.assertTrue({'0.6', '0.7'} <= pins)
        self.assertTrue(pins <= set(WORLD_VALIDATORS))

    def test_vendored_world_pins_match_their_source_hashes(self):
        for source in (ROOT / 'protocol' / 'worlds').glob('v*/SOURCE.json'):
            record = json.loads(source.read_text())
            for name, digest in record['sha256'].items():
                self.assertEqual(hashlib.sha256((source.parent / name).read_bytes()).hexdigest(), digest, source)


if __name__ == '__main__':
    unittest.main()
