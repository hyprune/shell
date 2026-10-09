import copy
import test_authoring
from protocol import V13_VALIDATOR, V14_VALIDATOR, validate_response
from client import Client
import unittest

class Contract014(unittest.TestCase):
    def test_persistent_controls_are_versioned_and_bounded(self):
        def request(patch): return {'jsonrpc':'2.0','id':'test','method':'graphics.set','params':{'patch':patch}}
        patch={'outline_quality':'smooth','outline_width_px':3.25,'outline_colour':[.2,.4,.6]}
        V14_VALIDATOR.validate(request(patch))
        V14_VALIDATOR.validate(request(dict.fromkeys(patch)))
        with self.assertRaises(Exception): V13_VALIDATOR.validate(request(patch))
        for patch in [{'outline_quality':'ultra'},{'outline_width_px':4.1},{'outline_width_px':True},{'outline_colour':[1,2,3]}]:
            with self.assertRaises(Exception): V14_VALIDATOR.validate(request(patch))
        self.assertIs(Client('/unused',lambda e:None,protocol='0.14').validator,V14_VALIDATOR)

    def test_canonical_revision_response_preserves_method_validation(self):
        response={'jsonrpc':'2.0','id':'r','result':{'revision':2}}
        V14_VALIDATOR.validate(response)
        validate_response(response,'atmosphere.set',V14_VALIDATOR)
        with self.assertRaises(Exception):validate_response(response,'camera.get',V14_VALIDATOR)

class PersistentInk(test_authoring.OutlineEdits):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.protocol='0.14'
        self.authored=copy.deepcopy(self.profile['outline'])
        self.config={}
    async def call(self,method,params):
        if method!='graphics.set':return await super().call(method,params)
        self.calls.append((method,params))
        self.config.update(params['patch'])
        for key,field in [('outline_width_px','widthPx'),('outline_colour','colour')]:
            if key in params['patch']:
                value=params['patch'][key]
                self.profile['outline'][field]=self.authored[field] if value is None else value
        return {'config':self.config}
    async def test_fresh_merge_and_colour_reset(self):
        await super().test_fresh_merge_and_colour_reset()
        self.assertEqual(self.config,{'outline_width_px':3,'outline_colour':None})
        self.assertFalse(any(m=='atmosphere.set' for m,p in self.calls))
    async def test_reset_follows_current_world_not_first_loaded_colour(self):
        await self.controller.update('world',{'widthPx':4,'colour':[1,0,0]})
        self.authored['colour']=[.5,.5,.5]
        await self.controller.update('world',{'widthPx':None,'colour':None})
        self.assertEqual(self.profile['outline'],self.authored)
        self.assertEqual(self.config,{'outline_width_px':None,'outline_colour':None})
