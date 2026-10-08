from pathlib import Path
import sys,tempfile,json,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bridge'))
from world_style import svg,load,contrast
class WorldStyleTests(unittest.TestCase):
    def test_svg_rejects_active_external_and_unbounded_content(self):
        for data in [b'<svg><script/></svg>',b'<svg><image href="https://bad"/></svg>',b'<svg onload="bad"/>',b'<!DOCTYPE svg><svg/>',b'<svg><path fill="url(https://bad)"/></svg>',b'<svg><foreignObject/></svg>',b'<svg>'+b'<g/>'*257+b'</svg>']:
            with self.assertRaises(ValueError):svg(data)
        self.assertIn(b'path',svg(b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><path d="M1 1L39 39" stroke="#ffffff"/></svg>'))
    def test_package_containment_contrast_and_cached_icons(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'hud/icons').mkdir(parents=True)
            manifest=root/'world.json';manifest.write_text(json.dumps({'id':'world','extensions':{'com.hyprune.hud-style':{'theme':'hud/theme.json'}}}))
            (root/'hud/theme.json').write_text(json.dumps({'version':1,'colors':{'foreground':'#000000','outline':'#ffffff','tile':'#ffffff'},'icons':{'window':'hud/icons/window.svg'}}))
            icon=root/'hud/icons/window.svg';icon.write_text('<svg><path d="M0 0L40 40"/></svg>')
            value=load(manifest,root/'cache');self.assertGreaterEqual(contrast(value['colors']['foreground'],value['colors']['outline']),4.5)
            self.assertTrue(value['icons']['window'].startswith((root/'cache').as_uri()))
            icon.unlink();icon.symlink_to('/etc/passwd')
            rejected=load(manifest,root/'cache');self.assertNotIn('window',rejected['icons']);self.assertIn('icon window',rejected['warning'])
