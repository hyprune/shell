import json
from pathlib import Path
import subprocess
import unittest


SCRIPT = (Path(__file__).resolve().parents[1] / 'qml/components/PerformanceText.js').read_text()


def evaluate(expression):
    return json.loads(subprocess.check_output(
        ['node', '-e', SCRIPT + '\nconsole.log(JSON.stringify(' + expression + '));'], text=True))


class PerformanceText(unittest.TestCase):
    def test_shared_cost_is_never_an_individual_measurement(self):
        self.assertEqual(evaluate("effectCost({controls:{fog:{gpuMs:null,passGpuMs:3.92}}},{},'fog')"), '')
        self.assertEqual(evaluate("effectCost({controls:{bloom:{gpuMs:0,passGpuMs:3.92}}},{},'bloom')"), '0.00 ms')
        self.assertEqual(evaluate("effectCost(null,{gpuEffectsMs:{world_shading_shared:3.92,msaa_resolve:.2}},'msaa')"), '')
        self.assertEqual(evaluate("effectCost(null,{gpuEffectsMs:{bloom:.125}},'bloom')"), '0.13 ms')
        self.assertEqual(evaluate("effectCost(null,{},'fog')"), '')

    def test_ink_cost_includes_its_measured_geometry_pass(self):
        self.assertEqual(evaluate("effectCost({controls:{outline:{gpuMs:1.25,sharedPass:'outline',passGpuMs:1.25}}},{},'outline')"),'1.25 ms')

    def test_shared_summary_follows_core_membership_and_handles_missing_timers(self):
        self.assertEqual(evaluate("worldShading({controls:{fog:{sharedPass:'world_shading_shared',passGpuMs:3.92},anisotropy:{sharedPass:null}}},{},{fog:'Fog'})"), 'World shading 3.92 ms, shared by:\nFog')
        self.assertIn('timing unavailable', evaluate("worldShading(null,{},{})"))

    def test_power_policy_distinguishes_cap_block_and_handover(self):
        self.assertEqual(evaluate("policy({profile:'usb-c',capW:50,targetFPS:45,reason:'inactive'})"), 'On USB-C power: offload capped at 50 W / 45 FPS.')
        self.assertEqual(evaluate("policy({profile:'usb-c',capW:50,targetFPS:45,reason:'auto requires qualified full AC'})"), 'On USB-C power: offload capped at 50 W / 45 FPS. Automatic offload needs full AC power.')
        self.assertEqual(evaluate("policy({status:'warming'})"), 'Switching renderer…')
        self.assertNotIn('undefined', evaluate("policy({profile:'unknown'})"))
        self.assertIn('unavailable', evaluate('policy(null)'))


class IdleText(unittest.TestCase):
    def test_no_new_rendered_frames_reads_idle(self):
        self.assertTrue(evaluate("idle({renderedFrames:10,idleFrames:3},{renderedFrames:10,idleFrames:9})"))
        # No compositor repaint at all: idleFrames flat, still idle.
        self.assertTrue(evaluate("idle({renderedFrames:10,idleFrames:3},{renderedFrames:10,idleFrames:3})"))

    def test_rendering_or_old_core_is_not_idle(self):
        self.assertFalse(evaluate("idle({renderedFrames:10,idleFrames:3},{renderedFrames:17,idleFrames:3})"))
        self.assertFalse(evaluate("idle({renderedFrames:10},{renderedFrames:10})"))  # pre-on-demand core
        self.assertFalse(evaluate("idle(null,{renderedFrames:10,idleFrames:0})"))

    def test_stats_text(self):
        self.assertEqual(evaluate("stats(3,850,.5,true)"), 'IDLE   /   no changes   /   50% SCALE')
        self.assertEqual(evaluate("stats(59.6,16.7,.5,false)"), '60 FPS   /   16.7 ms   /   50% SCALE')
        self.assertEqual(evaluate("stats(-1,-1,-1,false)"), 'FRAME TELEMETRY UNAVAILABLE')
