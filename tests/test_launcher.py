"""The presentation restart gate accepts owned descendants, never unrelated peers."""
import os
from pathlib import Path
import subprocess
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bridge'))
from launch import presentation_child

class LauncherTests(unittest.TestCase):
    def test_owned_replacement_and_unrelated_peer(self):
        children=[subprocess.Popen(['sleep','5']) for _ in range(2)]
        try:
            self.assertTrue(all(presentation_child(child.pid) for child in children))
            self.assertFalse(presentation_child(os.getppid()))
            self.assertFalse(presentation_child(1))
            self.assertFalse(presentation_child(2**30))
        finally:
            for child in children:child.terminate();child.wait()
