import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bridge'))
from client import Client, GRANTS
from protocol import V12_VALIDATOR, V13_VALIDATOR, WORLD_VALIDATORS, validate_response
from outline import OutlineController

class Contract(unittest.TestCase):
    def test_013_additions_do_not_widen_012(self):
        for method,params in [('graphics.set',{'patch':{'outline':True,'visibility_culling':False}}),('camera.photo',{'position':[0,2,4],'orientation':[0,0,0,1],'fov':15,'renderScale':.5})]:
            msg={'jsonrpc':'2.0','id':'test','method':method,'params':params}
            V13_VALIDATOR.validate(msg)
            with self.assertRaises(Exception):V12_VALIDATOR.validate(msg)
        self.assertIs(Client('/unused',lambda e:None,protocol='0.13').validator,V13_VALIDATOR)
        self.assertNotIn('camera.author',GRANTS)

    def test_revision_response_overlap_keeps_method_validation_strict(self):
        response={'jsonrpc':'2.0','id':'r','result':{'revision':2}}
        V13_VALIDATOR.validate(response)
        validate_response(response,'atmosphere.set',V13_VALIDATOR)
        with self.assertRaises(Exception):validate_response(response,'camera.get',V13_VALIDATOR)
        with self.assertRaises(Exception):V13_VALIDATOR.validate({**response,'result':{'unexpected':True}})

    def test_world_05_visibility_and_ink(self):
        # Start from the maintained original sample and validate new authored data.
        p=Path(__file__).resolve().parents[1]/'dev/observatory.world.json'
        world=json.loads(p.read_text())
        world['formatVersion']='0.5'
        world['visibility']={'areas':[{'id':'upper','bounds':{'min':[-10,0,-10],'max':[10,6,10]},'nodes':[0],'visibleFrom':[]}]}
        WORLD_VALIDATORS['0.5'].validate(world)
        bad=copy.deepcopy(world);bad['visibility']['areas'][0]['bounds']['min'][0]='wrong'
        with self.assertRaises(Exception):WORLD_VALIDATORS['0.5'].validate(bad)
        ink=V13_VALIDATOR.evolve(schema={'$ref':V13_VALIDATOR.schema['$id']+'#/$defs/authorAtmosphere/properties/outline'})
        ink.validate({'enabled':True,'colour':[.1,.2,.3],'widthPx':2,'depthThreshold':.02,'normalThreshold':.2})
        from launch import catalog
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'world.json';path.write_text(json.dumps(world))
            self.assertEqual(catalog([path])[0]['formatVersion'],'0.5')

class OutlineEdits(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.state={'world':{'id':'world'}}
        self.profile={'sky':{'type':'gradient'},'exposure':2,'outline':{'enabled':True,'colour':[.1,.2,.3],'widthPx':2,'depthThreshold':.02,'normalThreshold':.2}}
        self.calls=[];self.controller=OutlineController(self)
    async def call(self,method,params):
        self.calls.append((method,params))
        if method=='atmosphere.get':return {'profile':copy.deepcopy(self.profile)}
        self.profile=copy.deepcopy(params['profile']);return {'revision':2}
    async def test_fresh_merge_and_colour_reset(self):
        await self.controller.update('world')
        self.profile['exposure']=4
        await self.controller.update('world',{'widthPx':3,'colour':[1,0,0]})
        self.assertEqual(self.profile['exposure'],4)
        self.assertEqual(self.profile['outline']['depthThreshold'],.02)
        await self.controller.update('world',{'colour':None})
        self.assertEqual(self.profile['outline']['colour'],[.1,.2,.3])
    async def test_invalid_patch_or_changed_world_never_writes(self):
        for patch in [{'enabled':True},{'widthPx':0},{'colour':[1,2,3]},{'widthPx':True}]:
            with self.assertRaises(ValueError):await self.controller.update('world',patch)
        with self.assertRaises(ValueError):await self.controller.update('another',{'widthPx':2})
        self.assertFalse(any(m=='atmosphere.set' for m,p in self.calls))
    async def test_unauthored_world_never_gains_an_invented_style(self):
        self.profile.pop('outline')
        self.assertIsNone((await self.controller.update('world'))['style'])
        with self.assertRaises(ValueError):await self.controller.update('world',{'widthPx':2})
