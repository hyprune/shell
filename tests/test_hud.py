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

class PerspectiveGeometry(unittest.TestCase):
    def test_convex_edges_default_angles_and_off_identity(self):
        # Project actual corners, checking the visible result rather than signs
        # of matrix coefficients. Screen y increases downwards.
        import subprocess,json
        script=(Path(__file__).resolve().parents[1]/'qml/components/HudPerspective.js').read_text()
        script='const Qt={matrix4x4:(...v)=>v};\n'+script+'''
function p(m,x,y){let w=m[12]*x+m[13]*y+m[15];return [(m[0]*x+m[1]*y+m[3])/w,(m[4]*x+m[5]*y+m[7])/w]}
function corners(x,y,s){let m=matrix(590,203,x,y,s);return [p(m,0,0),p(m,590,0),p(m,0,203),p(m,590,203)]}
console.log(JSON.stringify({strengths:[.25,.8,1].map(s=>({left:corners(-1,1,s),right:corners(1,1,s),top:corners(0,-1,s),bottom:corners(0,1,s)})),off:corners(-1,1,0)}));
'''
        out=json.loads(subprocess.check_output(['node','--input-type=module','-e',script],text=True))
        import math
        ratios=[]
        for planes in out['strengths']:
            tl,tr,bl,br=planes['left']
            ratios.append((br[1]-tr[1])/(bl[1]-tl[1]))
            self.assertGreater(ratios[-1],1)
            self.assertLess(tr[1],tl[1])  # Upper border rises toward screen centre.
            for left,right in zip(planes['left'],[planes['right'][i] for i in [1,0,3,2]]):
                self.assertAlmostEqual(left[0]+right[0],590,places=5)
                self.assertAlmostEqual(left[1],right[1],places=5)
            tl,tr,bl,br=planes['top']
            self.assertGreater(br[0]-bl[0],tr[0]-tl[0])  # Top/outer edge recedes.
            tl,tr,bl,br=planes['bottom']
            self.assertGreater(tr[0]-tl[0],br[0]-bl[0])
        self.assertEqual(ratios,sorted(ratios))
        self.assertGreater(ratios[1],1.04)
        self.assertLess(ratios[1],1.06)
        tl,tr,bl,br=out['strengths'][1]['left']
        for a,b in [(tl,tr),(bl,br)]:
            angle=math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))
            self.assertGreater(angle,-3.5)
            self.assertLess(angle,-2.3)
        self.assertEqual(out['off'],[[0,0],[590,0],[0,203],[590,203]])
