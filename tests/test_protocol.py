import asyncio
import json
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bridge'))
from protocol import decode, frame, read_frame, validate_response, TRANSITION_VALIDATOR

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
    def test_transition_fixture_is_not_a_new_ipc_event(self):
        obj={'id':'jump-1','phase':'transit','progress':.4,'to':{'id':'com.hyprune.garden','name':'Garden','subtitle':'Sector 02'}}
        TRANSITION_VALIDATOR.validate(obj)
        with self.assertRaises(Exception):frame({'jsonrpc':'2.0','method':'location.transition','params':obj})
        for bad in [{**obj,'progress':1.5},{**obj,'phase':'ready'},{**obj,'extra':'unknown'}]:
            with self.assertRaises(Exception):TRANSITION_VALIDATOR.validate(bad)
    def test_method_matched_response(self):
        obj={'jsonrpc':'2.0','id':'a','result':{'revision':1}}
        frame(obj)
        with self.assertRaises(Exception): validate_response(obj,'session.ping')

if __name__=='__main__': unittest.main()
