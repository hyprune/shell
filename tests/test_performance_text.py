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
    def test_ipc_018_cap_source_and_offload_gpu(self):
        gpu = "{pci:'0000:02:00.0',node:'renderD129',name:'RTX 5090 Laptop',enforcedLimitW:135,selection:'auto',drivesCompositor:false}"
        self.assertEqual(evaluate("policy({profile:'usb-c',capW:50,targetFPS:45,reason:'auto requires qualified full AC',capSource:'profile',device:" + gpu + "})"),
                         'On USB-C power: offload capped at 50 W / 45 FPS. Offload GPU: RTX 5090 Laptop. Automatic offload needs full AC power.')
        self.assertEqual(evaluate("policy({profile:'full-ac',capW:101,targetFPS:60,reason:'ready',capSource:'device',device:" + gpu + "})"),
                         "On AC power: offload capped at 101 W / 60 FPS. Cap is 75 % of the GPU's 135 W limit. Offload GPU: RTX 5090 Laptop.")
        self.assertIn('pinned', evaluate("policy({profile:'full-ac',capW:80,reason:'ready',capSource:'configured',device:{pci:'0000:65:00.0',name:null,enforcedLimitW:null,selection:'explicit',drivesCompositor:true}})"))
        self.assertIn('default cap', evaluate("policy({profile:'full-ac',capW:80,reason:'ready',capSource:'fallback',device:null})"))
        self.assertNotIn('undefined', evaluate("policy({profile:'full-ac',capW:80,reason:'ready'})"))  # pre-0.18 cores

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


class UpscalerText(unittest.TestCase):
    def test_labels_and_fallback(self):
        self.assertEqual(evaluate("upscalerName(null)"), 'Preset')
        self.assertEqual(evaluate("upscalerName('fsr1')"), 'FSR 1')
        self.assertEqual(evaluate("upscaler({requested:'fsr1',active:'fsr1',error:null})"), 'Active: FSR 1')
        self.assertEqual(evaluate("upscaler({requested:'fsr1',active:'bilinear',error:'GLSL ES 3.1'})"), 'Active: Bilinear (FSR 1 unavailable)')
        self.assertEqual(evaluate("upscaler(null)"), 'Active: —')

    def test_settings_row_uses_shared_protocol_helper(self):
        model = (Path(__file__).resolve().parents[1] / 'qml/SettingsModel.js').read_text()
        self.assertIn("{key: 'graphics.upscaler', category: 'display'", model)
        self.assertIn("protocol: 16", model[model.index("graphics.upscaler"):model.index("graphics.upscaler") + 300])
        row = (Path(__file__).resolve().parents[1] / 'qml/components/SettingRow.qml').read_text()
        self.assertIn("readonly property string objectKey: row.key.replace('.', '-')", row)  # graphics-upscaler
