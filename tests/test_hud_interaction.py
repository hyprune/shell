import json
from pathlib import Path
import subprocess
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bridge'))
from client import Client
from protocol import V10_VALIDATOR,V11_VALIDATOR,V12_VALIDATOR

class InteractionContract(unittest.TestCase):
    def test_versions_keep_cursor_and_climbing_boundaries(self):
        movement={'modeId':'com.hyprune.walk','position':[0,4,0],'orientation':[0,0,0,1],'state':'climbing','ladderId':'ladder','prompt':'Core prompt'}
        message={'jsonrpc':'2.0','method':'state.delta','params':{'subscriptionId':'s','sessionId':'session','baseRevision':1,'revision':2,'changes':{'movement':movement}}}
        V11_VALIDATOR.validate(message);V12_VALIDATOR.validate(message)
        with self.assertRaises(Exception):V10_VALIDATOR.validate(message)
        message['params']['changes']={'interaction':{'mode':'cursor','tool':1,'tools':['pointer','mount','path','path','path'],'noclip':False,'cursor':'virtual','taggedSurfaceId':None}}
        V12_VALIDATOR.validate(message)
        with self.assertRaises(Exception):V11_VALIDATOR.validate(message)
        for version,validator in [('0.11',V11_VALIDATOR),('0.12',V12_VALIDATOR)]:
            self.assertIs(Client('/unused',lambda e:None,protocol=version).validator,validator)

    def test_prompts_follow_authoritative_activity_and_cursor_wins(self):
        script=(Path(__file__).resolve().parents[1]/'qml/HudInteraction.js').read_text()+'''
let c={movement:{state:'climbing',prompt:'Core-authored prompt'}};
console.log(JSON.stringify([
 climbPrompt(c), climbPrompt({movement:{state:'climbing',prompt:''}}),
 climbPrompt({...c,editor:{mode:'cursor'}}),
 climbPrompt({...c,interaction:{mode:'cursor'}}),
 climbing({movement:{state:'walking',prompt:'stale'}}),
 freeCursor({interaction:{mode:'typing'}}), climbing(null),climbPrompt({})]));
'''
        result=json.loads(subprocess.check_output(['node','-e',script],text=True))
        self.assertEqual(result,['Core-authored prompt','W/S climb · Space let go','','',False,False,False,''])
