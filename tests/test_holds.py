import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bridge'))
from client import Client
from protocol import V7_VALIDATOR, V8_VALIDATOR

class HoldTests(unittest.TestCase):
    def test_monotonic_progress_reload_cancel_and_reconnect(self):
        events = []
        client = Client('/unused', events.append, protocol='0.8')
        hold = dict(action='menu', binding='TAB:hold', startedAtMs=1000, durationMs=1000)
        client.state = {'keymap': {'holds': [hold]}}
        with patch('client.time.monotonic', return_value=1.4):
            client.publish_hold()
            self.assertAlmostEqual(events[-1]['hold']['progress'], .4)
            self.assertEqual(events[-1]['hold']['remainingMs'], 600)
            client.publish_hold()
            self.assertEqual(len(events), 1)  # Unrelated deltas do not restart animation.
            hold['durationMs'] = 2000
            client.publish_hold()
            self.assertEqual(events[-1]['hold']['startedAtMs'], 1000)
            self.assertEqual(events[-1]['hold']['remainingMs'], 1600)
        with patch('client.time.monotonic', return_value=2):
            client.publish_hold(force=True)  # Replacement QML gets fresh timing.
            self.assertAlmostEqual(events[-1]['hold']['progress'], .5)
        client.state['keymap']['holds'] = []
        client.publish_hold()
        self.assertIsNone(events[-1]['hold'])
        client.state['keymap']['holds'] = [hold]
        with patch('client.time.monotonic', return_value=4):
            client.publish_hold()
            self.assertEqual(events[-1]['hold']['progress'], 1)
        client.state = None
        client.publish_hold()
        self.assertIsNone(events[-1]['hold'])

    def test_08_is_explicit_and_hold_shape_is_closed(self):
        config_schema = V8_VALIDATOR.schema['$defs']['inputConfig']
        config = dict(version=2, longHoldMs=1000, scopeVignette=True, useDistance=6,
                      useTolerance=.12, captureInputLimit=256,
                      modes={mode:{action:[] for action in schema['properties']}
                             for mode,schema in config_schema['properties']['modes']['properties'].items()})
        hold = dict(action='menu', binding='TAB:hold', startedAtMs=1000, durationMs=1000)
        keymap = dict(config=config,path='',steals=[],conflicts=[],capture=None,error='',holds=[hold])
        new = V8_VALIDATOR.evolve(schema={'$ref':V8_VALIDATOR.schema['$id']+'#/$defs/keymap'})
        old = V7_VALIDATOR.evolve(schema={'$ref':V7_VALIDATOR.schema['$id']+'#/$defs/keymap'})
        new.validate(keymap)
        with self.assertRaises(Exception): old.validate(keymap)
        for update in [{'durationMs':0},{'startedAtMs':-1},{'extra':True}]:
            with self.assertRaises(Exception): new.validate({**keymap,'holds':[{**hold,**update}]})
        V8_VALIDATOR.validate({'jsonrpc':'2.0','id':'hello','method':'session.hello','params':{'protocols':['0.8'],'client':{'id':'com.hyprune.shell','name':'Shell'},'capabilities':['input.control','world.control']}})
