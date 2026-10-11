"""dev/devenv.py: environment over ~/.config/hyprune/dev.env; unset output dirs warn, never silence."""
import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'dev'))
import devenv  # noqa: E402


class DevEnv(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        env = {k: v for k, v in os.environ.items() if k not in devenv.KEYS}
        env.update(XDG_CONFIG_HOME=str(self.tmp / 'config'), HOME=str(self.tmp / 'home'))
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        devenv._warned.clear()
        fallback = mock.patch.object(devenv, 'fallback_root', lambda: self.tmp / 'run')
        fallback.start()
        self.addCleanup(fallback.stop)

    def test_file_then_environment(self):
        self.assertIsNone(devenv.get('HYPRUNE_GALLERY_DIR'))
        (self.tmp / 'config/hyprune').mkdir(parents=True)
        (self.tmp / 'config/hyprune/dev.env').write_text('# review\nHYPRUNE_GALLERY_DIR=~/g\nexport HYPRUNE_VIDEO_DIR="/v"\n')
        self.assertEqual(devenv.get('HYPRUNE_GALLERY_DIR'), str(self.tmp / 'home/g'))
        self.assertEqual(devenv.get('HYPRUNE_VIDEO_DIR'), '/v')
        os.environ['HYPRUNE_VIDEO_DIR'] = str(self.tmp / 'env-videos')
        self.assertEqual(devenv.video_dir(), self.tmp / 'env-videos')

    def test_unconfigured_output_warns_once_with_its_fallback(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            shots = devenv.gallery_dir('screenshots/a')
            devenv.gallery_dir('screenshots/b')
        self.assertEqual(shots, devenv.fallback_root() / 'gallery/screenshots/a')
        self.assertTrue(shots.is_dir())
        self.assertEqual(err.getvalue().count('HYPRUNE_GALLERY_DIR is not set'), 1)
        self.assertIn(str(devenv.fallback_root() / 'gallery'), err.getvalue())


if __name__ == '__main__':
    unittest.main()
