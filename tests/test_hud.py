import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bridge'))
from client import Client
from protocol import V9_VALIDATOR, at_least
class HudEvents(unittest.TestCase):
    def setUp(self):
        self.events=[];self.client=Client('/unused',self.events.append,protocol='0.9')
        self.client.ready=True;self.client.session='session';self.client.lease='lease';self.client.output='output';self.client.revision=10
        self.client.hud_subscription='hud';self.client.state={'world':{'id':'world'}}
    def cycle(self,**patch):
        return dict(sessionId='session',leaseId='lease',outputId='output',revision=10,sequence=1,monotonicMs=123,**patch)
    def test_cycle_scope_duplicates_and_resync(self):
        p=self.cycle()
        for key,value in [('sessionId','old'),('leaseId','other'),('outputId','other'),('revision',9)]:
            self.client.hud_event('ui.hud.cycle',{**p,key:value})
        self.assertEqual(self.events,[])
        V9_VALIDATOR.validate({'jsonrpc':'2.0','method':'ui.hud.cycle','params':p})
        self.client.hud_event('ui.hud.cycle',p);self.client.hud_event('ui.hud.cycle',p)
        self.assertEqual(self.events,[{'type':'hud.cycle'}])
        self.client.resyncing=True;self.client.hud_event('ui.hud.cycle',{**p,'sequence':2})
        self.assertEqual(len(self.events),1)
    def test_telemetry_order_and_subscription(self):
        p={'sessionId':'session','subscriptionId':'hud','revision':10,'monotonicMs':123}
        self.client.hud_event('hud.frame',{**p,'subscriptionId':'old'})
        self.client.hud_event('hud.frame',p);self.client.hud_event('hud.frame',p)
        self.client.hud_event('hud.frame',{**p,'monotonicMs':122})
        self.assertEqual(len(self.events),1)
        self.client.hud_event('hud.pose',{**p,'outputId':'other','worldId':'world'})
        self.assertEqual(len(self.events),1)
    def test_exact_versions_and_inherited_floors(self):
        self.assertTrue(at_least('0.9',8));self.assertFalse(at_least('0.2',8));self.assertFalse(at_least('0.100',8))
        with self.assertRaises(ValueError):Client('/unused',lambda e:None,protocol='0.100')
