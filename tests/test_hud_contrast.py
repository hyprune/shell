import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'dev'))
from hud_contrast import luminance, measure_pixels


class HudContrast(unittest.TestCase):
    def test_srgb_reference_values(self):
        self.assertAlmostEqual(float(luminance([0,0,0])),0)
        self.assertAlmostEqual(float(luminance([255,255,255])),1)
        self.assertAlmostEqual(float(luminance([128,128,128])),.2158605,places=6)

    def test_bright_wall_fails_and_dark_scrim_passes(self):
        white=np.full((1,3,3),255)
        mask=np.array([[[255]*3,[128]*3,[0]*3]])
        good=measure_pixels(white,np.full((1,3,3),90),mask,[255]*3)
        bad=measure_pixels(white,np.full((1,3,3),230),mask,[255]*3)
        self.assertTrue(good['passContrast'])
        self.assertFalse(bad['passContrast'])
        self.assertEqual(good['corePixels'],1)

    def test_faint_rendered_glyph_fails_even_with_good_nominal_colour(self):
        gray=np.full((1,1,3),128)
        result=measure_pixels(gray,np.full((1,1,3),90),np.full((1,1,3),255),[255]*3)
        self.assertGreater(result['nominalMin'],4.5)
        self.assertLess(result['rasterCoreMin'],4.5)
        self.assertFalse(result['passContrast'])

    def test_empty_mask_cannot_pass(self):
        with self.assertRaises(ValueError):
            measure_pixels(np.zeros((1,1,3)),np.zeros((1,1,3)),np.zeros((1,1,3)),[255]*3)
