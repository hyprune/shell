"""Sliders that reconfigure the renderer (target FPS, power cap, scale, sharpening) apply
once they settle (released, or 300 ms after the last key step), not on every step, and the
handle is not pushed back by state polls while it is dragged."""
import re
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


class SliderSettle(unittest.TestCase):
    def test_slider_settles(self):
        slider = (ROOT / 'qml/components/SettingSlider.qml').read_text()
        for needle in ['signal settled(real value)', 'property int settleMs: 300', "when: root.target !== undefined && !root.settling",
                       'onPressedChanged: if (!pressed) settle_()', 'onMoved: { unsettled = true; settle.restart(); }']:
            self.assertIn(needle, slider)

    def test_graphics_sliders_apply_on_settle(self):
        graphics = (ROOT / 'qml/components/GraphicsSettings.qml').read_text()
        sliders = re.findall(r'SettingSlider \{[^\n]*', graphics)
        self.assertEqual(len(sliders), 3)
        for s in sliders:
            self.assertIn('onSettled:', s)
            self.assertNotIn('onMoved:', s)
            self.assertIn('target:', s)


if __name__ == '__main__':
    unittest.main()
