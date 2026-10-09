"""Vendored logo provenance, verbatim geometry and the brand size rule."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / 'qml/components/brand'
META = ROOT.parent / 'hyprune/brand'
MARKS_JS = (BRAND / 'BrandMarks.js').read_text()
NS = '{http://www.w3.org/2000/svg}'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recorded():
    """Vendored file -> (source path, SHA-256) from BRAND.md."""
    rows = re.findall(r'^\| `([^`]+\.svg)` \| `(brand/[^`]+)` \| `([0-9a-f]{64})` \|$',
                      (BRAND / 'BRAND.md').read_text(), re.M)
    return {name: (source, digest) for name, source, digest in rows}


def evaluate(expression):
    return json.loads(subprocess.check_output(
        ['node', '-e', MARKS_JS + '\nconsole.log(JSON.stringify(' + expression + '));'], text=True))


class Provenance(unittest.TestCase):
    def test_brand_note_cites_commit_and_lists_every_vendored_svg(self):
        self.assertIn('352e777', (BRAND / 'BRAND.md').read_text())
        self.assertEqual(set(recorded()), {p.name for p in BRAND.glob('*.svg')})

    def test_vendored_bytes_match_recorded_hashes(self):
        for name, (_, digest) in recorded().items():
            self.assertEqual(sha256(BRAND / name), digest, name)

    @unittest.skipUnless((META / 'SHA256SUMS').exists(), 'meta repo checkout not beside shell')
    def test_recorded_hashes_match_meta_masters(self):
        sums = dict(reversed(line.split('  ', 1)) for line in (META / 'SHA256SUMS').read_text().splitlines() if line)
        for name, (source, digest) in recorded().items():
            relative = source.removeprefix('brand/')
            self.assertEqual(sums[relative], digest, source)
            self.assertEqual((META / relative).read_bytes(), (BRAND / name).read_bytes(), source)


class Geometry(unittest.TestCase):
    def test_generated_table_is_current(self):
        spec = importlib.util.spec_from_file_location('sync_brand', ROOT / 'dev/sync-brand.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.render(), MARKS_JS, 'run python3 dev/sync-brand.py')

    def test_path_data_and_shapes_are_verbatim(self):
        masters = evaluate('masters')
        for variant, m in masters.items():
            root = ET.parse(BRAND / m['file']).getroot()
            paths = [(e.get('d'), float(e.get('stroke-width'))) for e in root.iter(NS + 'path')]
            self.assertEqual([(s['d'], s['width']) for s in m['strokes']], paths, variant)
            for tag, keys, key in [('ellipse', ('cx', 'cy', 'rx', 'ry'), 'ellipses'), ('rect', ('x', 'y', 'width', 'height', 'rx'), 'rects'),
                                   ('circle', ('cx', 'cy', 'r'), 'circles')]:
                expected = [{k: float(e.get(k)) for k in keys} for e in root.iter(NS + tag)]
                self.assertEqual(m[key], expected, (variant, tag))
            # Every grouped stroke path is a plain concatenation of master paths.
            for group in evaluate(f"strokeGroups('{variant}')"):
                self.assertEqual(group['d'], ''.join(s['d'] for s in m['strokes'] if s['width'] == group['width']))

    def test_room_drawings_carry_the_clear_space(self):
        for variant in ('optical', 'primary'):
            m = evaluate(f"masters.{variant}")
            x0, y0, x1, y1 = m['ink']
            self.assertGreaterEqual(min(x0, y0, m['viewBox'] - x1, m['viewBox'] - y1), 32, variant)

    def test_fills_cover_player_shadow_and_footsteps(self):
        self.assertEqual(evaluate("[fillPath('h16'), fillPath('h32')]"), ['', ''])
        self.assertEqual(evaluate("fillPath('optical').split('Z').length - 1"), 10)
        self.assertEqual(evaluate("fillPath('primary').split('Z').length - 1"), 10)


class SizeRule(unittest.TestCase):
    def test_variant_follows_physical_pixels(self):
        cases = {12: 'h16', 16: 'h16', 17: 'h32', 31: 'h32', 32: 'h32', 47: 'h32', 48: 'optical',
                 64: 'optical', 95: 'optical', 96: 'primary', 144: 'primary', 512: 'primary'}
        self.assertEqual(evaluate(f"{list(cases)}.map(variantFor)"), list(cases.values()))

    def test_fractional_sizes_round_to_the_nearest_pixel(self):
        self.assertEqual(evaluate("[16.4, 16.5, 47.4, 47.5, 95.49, 95.5].map(variantFor)"),
                         ['h16', 'h32', 'h32', 'optical', 'optical', 'primary'])


class Integration(unittest.TestCase):
    def test_mark_follows_theme_and_physical_scale(self):
        qml = (ROOT / 'qml/components/BrandMark.qml').read_text()
        self.assertIn('property color color: Tokens.accent', qml)
        self.assertIn('Window.window.devicePixelRatio', qml)
        self.assertIn('ratio *= item.scale', qml)
        self.assertIn('Shape.CurveRenderer', qml)

    def test_surfaces_use_the_mark(self):
        self.assertIn("objectName: 'brandMark:director'", (ROOT / 'qml/components/Director.qml').read_text())
        self.assertIn("objectName: 'brandMark:about'", (ROOT / 'qml/components/DirectorSettings.qml').read_text())

    def test_about_version_matches_version_file(self):
        version = (ROOT / 'VERSION').read_text().strip()
        self.assertIn(f"readonly property string shellVersion: '{version}'", (ROOT / 'qml/ShellState.qml').read_text())


if __name__ == '__main__':
    unittest.main()
