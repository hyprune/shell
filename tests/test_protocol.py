import asyncio
import json
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bridge'))
from protocol import decode, frame, read_frame, validate_response, V2_VALIDATOR

PING = {'jsonrpc':'2.0','id':'a','method':'session.ping','params':{}}

class CodecTests(unittest.IsolatedAsyncioTestCase):
    async def test_split_multibyte_and_coalesced_frames(self):
        obj={'jsonrpc':'2.0','method':'runtime.notice','params':{'level':'info','code':'test','message':'árvíz 🌌'}}
        data=frame(obj)+frame(PING)
        reader=asyncio.StreamReader()
        async def feed():
            for byte in data:
                reader.feed_data(bytes([byte]))
                await asyncio.sleep(0)
        task=asyncio.create_task(feed())
        self.assertEqual(await read_frame(reader),obj)
        self.assertEqual(await read_frame(reader),PING)
        await task
    async def test_reject_lengths_before_body(self):
        for length in [0,1_048_577,0xffffffff]:
            reader=asyncio.StreamReader();reader.feed_data(struct.pack('!I',length))
            with self.assertRaises(ValueError): await read_frame(reader)
    def test_duplicate_nonfinite_depth_invalid_utf8(self):
        for data in [b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":1e999}',b'['*65+b'0'+b']'*65,b'"\xff"']:
            with self.assertRaises((ValueError,UnicodeDecodeError)): decode(data)
        self.assertEqual(decode(b'{"x":"[[[\\\""}'),{'x':'[[["'})
    def test_no_batches_unknown_fields(self):
        for obj in [[PING],{**PING,'surprise':True},{**PING,'id':1}]:
            with self.assertRaises(Exception): frame(obj)
    def test_native_transition_is_exact_02_only(self):
        params={'id':'jump-1','outputId':'world','phase':'loading','progress':None,
                'to':{'worldId':'com.hyprune.garden'},'monotonicMs':10,'sessionId':'session','revision':2}
        message={'jsonrpc':'2.0','method':'location.transition','params':params}
        frame(message,V2_VALIDATOR)
        with self.assertRaises(Exception):frame(message)
        for bad in [{**params,'progress':1.5},{**params,'phase':'ready'},{**params,'extra':'unknown'}]:
            with self.assertRaises(Exception):frame({**message,'params':bad},V2_VALIDATOR)
    def test_method_matched_response(self):
        obj={'jsonrpc':'2.0','id':'a','result':{'revision':1}}
        frame(obj)
        with self.assertRaises(Exception): validate_response(obj,'session.ping')

if __name__=='__main__': unittest.main()

class SessionContractTests(unittest.TestCase):
    def test_03_methods_do_not_widen_02(self):
        from protocol import V3_VALIDATOR, V2_VALIDATOR
        for method, params in [('shell.bind', {'leaseId':'lease','pid':123}), ('workspace.activate',{'id':11})]:
            message={'jsonrpc':'2.0','id':'first','method':method,'params':params}
            V3_VALIDATOR.validate(message)
            with self.assertRaises(Exception): V2_VALIDATOR.validate(message)
            with self.assertRaises(Exception): V3_VALIDATOR.validate({**message,'params':{**params,'_pid':123}})

    def test_04_mount_methods_do_not_widen_older_protocols(self):
        from protocol import V4_VALIDATOR, V3_VALIDATOR
        for method, params in [('surfaces.recall', {}), ('surface.pull', {'surfaceId':'terminal'}), ('workspace.bind', {'id':10,'worldId':'com.hyprune.lumen-reach','areaId':'sun-court'}), ('camera.fov', {'degrees':72})]:
            request={'jsonrpc':'2.0','id':'m2','method':method,'params':params}
            V4_VALIDATOR.validate(request)
            with self.assertRaises(Exception): V3_VALIDATOR.validate(request)
            with self.assertRaises(Exception): V4_VALIDATOR.validate({**request,'params':{**params,'unexpected':True}})

class HandsContractTests(unittest.TestCase):
    def test_05_modes_apps_are_isolated_and_closed(self):
        from protocol import V4_VALIDATOR,V5_VALIDATOR
        msg={'jsonrpc':'2.0','method':'state.delta','params':{'subscriptionId':'sub','sessionId':'session','baseRevision':1,'revision':2,'changes':{'interaction':{'mode':'typing','tool':2,'tools':['pointer','mount','path','path','path'],'noclip':False,'cursor':'virtual','taggedSurfaceId':None},'apps':[{'surfaceId':'surface-1','workspaceId':10,'title':'Terminal','appClass':'kitty','icon':'kitty'}]}}}
        V5_VALIDATOR.validate(msg)
        with self.assertRaises(Exception): V4_VALIDATOR.validate(msg)
        msg['params']['changes']['interaction']['tool']=6
        with self.assertRaises(Exception): V5_VALIDATOR.validate(msg)

class KeymapContractTests(unittest.TestCase):
    def test_06_input_capture_is_closed_and_versioned(self):
        from protocol import V5_VALIDATOR, V6_VALIDATOR
        params = {'leaseId':'director','mode':'world','action':'debug','slot':2}
        message = {'jsonrpc':'2.0','id':'capture','method':'input.capture','params':params}
        V6_VALIDATOR.validate(message)
        with self.assertRaises(Exception): V5_VALIDATOR.validate(message)
        for update in [{'slot':3}, {'mode':'typing'}, {'unexpected':True}]:
            with self.assertRaises(Exception):
                V6_VALIDATOR.validate({**message,'params':{**params,**update}})

    def test_06_config_bounds_and_three_variants(self):
        from protocol import V6_VALIDATOR
        defs = V6_VALIDATOR.schema['$defs']['inputConfig']
        config = dict(version=2,longHoldMs=1000,scopeVignette=True,useDistance=6,
                      useTolerance=.12,captureInputLimit=256,
                      modes={mode:{action:[] for action in schema['properties']}
                             for mode,schema in defs['properties']['modes']['properties'].items()})
        message = {'jsonrpc':'2.0','id':'save','method':'input.set','params':{'config':config}}
        V6_VALIDATOR.validate(message)
        config['modes']['world']['forward'] = ['k','w','Up','F1']
        with self.assertRaises(Exception): V6_VALIDATOR.validate(message)
        config['modes']['world']['forward'] = ['k','w','Up']
        config['longHoldMs'] = 99
        with self.assertRaises(Exception): V6_VALIDATOR.validate(message)

    def test_06_map_intent_has_closed_panels(self):
        from protocol import V5_VALIDATOR, V6_VALIDATOR
        message = {'jsonrpc':'2.0','method':'ui.opened','params':dict(
            leaseId='director',outputId='world',panel='map',
            sessionId='session',revision=2)}
        V6_VALIDATOR.validate(message)
        V5_VALIDATOR.validate(message)  # Older versions allowed arbitrary panel strings.
        message['params']['panel'] = 'unknown'
        with self.assertRaises(Exception): V6_VALIDATOR.validate(message)
