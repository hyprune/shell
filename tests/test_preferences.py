import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bridge'))
from preferences import Preferences
class PreferenceTests(unittest.TestCase):
    def test_restart_and_invalid_patch_preserve_last_good_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'config/shell.json';p=Preferences(path)
            p.update({'concept':'Instrument','curvature':.9,'curved':False,'resource':'cpu'})
            self.assertEqual(Preferences(path).value,p.value)
            before=path.read_bytes()
            for patch in [{'concept':'Unknown'},{'curvature':float('nan')},{'curvature':2},{'curved':1},{'password':'secret'}]:
                with self.assertRaises(ValueError):p.update(patch)
                self.assertEqual(path.read_bytes(),before)
            self.assertEqual(list(path.parent.glob('.shell-*')),[])
    def test_corrupt_file_defaults_and_repair(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'shell.json';path.write_text('{broken')
            p=Preferences(path);self.assertEqual(p.value['concept'],'Vanguard')
            p.update({'concept':'Minimal'})
            self.assertEqual(json.loads(path.read_text())['concept'],'Minimal')
