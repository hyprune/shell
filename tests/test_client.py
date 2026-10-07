import asyncio
import contextlib
import copy
from pathlib import Path
import sys
import tempfile
import os
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bridge'))
from client import Client, GRANTS, REQUIRED
from protocol import frame, read_frame, VALIDATOR, V2_VALIDATOR

STATE={'runtime':{'active':True,'outputs':['world','unrelated']},'world':{'id':'com.hyprune.observatory','spawnId':'arrival'},'surfaces':[],
       'movement':{'modeId':'com.hyprune.fly','position':[0,1,0],'orientation':[0,0,0,1]},'shell':{'leases':[]}}

class ClientTests(unittest.IsolatedAsyncioTestCase):
    protocol = '0.1'
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=self.tmp.name+'/core.sock'
        self.events=[];self.calls=[];self.peers=[];self.state=copy.deepcopy(STATE);self.revision=0
        self.validator = V2_VALIDATOR if self.protocol == '0.2' else VALIDATOR
        if self.protocol == '0.2':
            self.state.update(location={'zones':[], 'waypoint':None, 'route':[], 'autodrive':False, 'transition':None}, integrations={'sources':[]})
        self.connections=0;self.tokens=0;self.revoked=False;self.hold_overlay_delta=False;self.snapshot_requests=0;self.reverse_responses=False;self.held=None;self.claim_conflict=False
        async def token():self.tokens+=1;return format(self.tokens,'064x')
        self.client=Client(self.path,self.events.append,token,{'world':'TEST'},protocol=self.protocol)
        self.client.screens=['TEST']
        self.server=await asyncio.start_unix_server(self.peer,self.path)
        os.chmod(self.path,0o600)
        self.task=asyncio.create_task(self.client.run())
        await self.until(lambda:self.client.lease is not None)
    async def asyncTearDown(self):
        self.task.cancel()
        await asyncio.gather(self.task,return_exceptions=True)
        for p in self.peers:p.close()
        self.server.close();await self.server.wait_closed();self.tmp.cleanup()
    async def until(self,predicate):
        async with asyncio.timeout(4):
            while not predicate():await asyncio.sleep(.01)
    def delta(self,base,revision,changes):
        return {'jsonrpc':'2.0','method':'state.delta','params':{'sessionId':'session','subscriptionId':'sub','baseRevision':base,'revision':revision,'changes':changes}}
    async def peer(self,reader,writer):
        self.connections+=1;self.peers.append(writer)
        try:
            while True:
                msg=await read_frame(reader,self.validator);method=msg['method'];p=msg['params'];self.calls.append((method,p))
                revision=self.revision
                if method=='session.hello': result={'protocol':self.protocol,'sessionId':'session','capabilities':GRANTS,'methods':REQUIRED + (['travel.start','waypoint.set','ui.close'] if self.protocol=='0.2' else []),'events':['state.delta','runtime.notice','session.revoked'] + (['location.transition','ui.opened','ui.closed'] if self.protocol=='0.2' else [])}
                elif method=='session.ping':result={'monotonicMs':10}
                elif method=='state.subscribe':result={'subscriptionId':'sub','snapshot':{'sessionId':'session','revision':revision,'state':self.state}}
                elif method=='state.snapshot':
                    self.snapshot_requests+=1
                    result={'snapshot':{'sessionId':'session','revision':self.revision,'state':self.state}}
                elif method=='shell.claim':
                    if self.claim_conflict:
                        writer.write(frame({'jsonrpc':'2.0','id':msg['id'],'error':{'code':-32004,'message':'Output already claimed'}},self.validator));await writer.drain();continue
                    self.assertEqual(p['outputs'],['world'])
                    self.state['shell']={'leases':[{'id':'lease-'+str(self.connections),'outputs':['world'],'overlays':[]}]}
                    result={'leaseId':'lease-'+str(self.connections),'revision':revision+1};self.revision+=1
                elif method in ['shell.overlay','ui.close']:
                    self.state['shell']['leases'][0]['overlays']=[{'outputId':'world','visible':p.get('visible',False),'exclusiveInput':p.get('exclusiveInput',False)}]
                    result={'revision':revision+1};self.revision+=1
                elif method=='shell.release':
                    self.state['shell']={'leases':[]};result={'revision':revision+1};self.revision+=1
                elif method=='state.unsubscribe':result={'ok':True}
                else:result={'revision':revision}
                data=frame({'jsonrpc':'2.0','id':msg['id'],'result':result},self.validator)
                # Deliberately coalesce a snapshot reply with its FIRST delta:
                # subscription must be installed before receiving the latter.
                if method=='state.subscribe':
                    self.revision+=1
                    data+=frame(self.delta(revision,self.revision,{'movement':self.state['movement']}))
                elif method in ['shell.claim','shell.overlay','shell.release','ui.close'] and not (method=='shell.overlay' and self.hold_overlay_delta):
                    data+=frame(self.delta(revision,self.revision,{'shell':self.state['shell']}))
                if self.reverse_responses and method in ['session.ping','movement.set']:
                    if self.held is None:self.held=data;continue
                    data+=self.held;self.held=None;self.reverse_responses=False
                writer.write(data);await writer.drain()
        except (asyncio.IncompleteReadError,ConnectionError):pass
        finally:writer.close()
    async def test_atomic_subscribe_and_exclusive_mapping(self):
        await self.client.overlay(True)
        self.assertTrue(self.client.director)
        self.assertTrue(self.events[-1]['open'])
        await self.client.overlay(False)
        self.assertFalse(self.client.director)
        expected=('ui.close',{'leaseId':self.client.lease,'outputId':'world'}) if self.protocol=='0.2' else ('shell.overlay',{'leaseId':self.client.lease,'outputId':'world','visible':False,'exclusiveInput':False})
        self.assertIn(expected,self.calls)
        self.assertEqual(self.snapshot_requests,0)
    async def test_committed_overlay_reply_may_precede_delta(self):
        self.hold_overlay_delta=True
        await self.client.overlay(True)
        self.assertLess(self.client.revision,self.client.overlay_revision)
        await self.client.reconcile()
        self.assertTrue(self.client.director, 'Old state cannot revoke a newer committed overlay')
        self.peers[-1].write(frame(self.delta(self.client.revision,self.revision,{'shell':self.state['shell']})))
        await self.until(lambda:self.client.revision==self.revision)
        self.assertTrue(self.client.director)
    async def test_response_order_is_independent_of_call_order(self):
        self.reverse_responses=True
        ping=asyncio.create_task(self.client.call('session.ping',{}))
        movement=asyncio.create_task(self.client.call('movement.set',{'modeId':'com.hyprune.fly'}))
        self.assertEqual(await ping,{'monotonicMs':10})
        self.assertIn('revision',await movement)
    async def test_second_shell_conflict_does_not_retry_or_evict(self):
        owner=self.client.lease
        self.claim_conflict=True
        second=Client(self.path,self.events.append,bindings={'world':'TEST'},protocol=self.protocol)
        second.screens=['TEST']
        task=asyncio.create_task(second.run())
        try:
            await self.until(lambda:second.claim_blocked)
            count=sum(m=='shell.claim' for m,p in self.calls)
            await asyncio.sleep(.3)
            self.assertEqual(sum(m=='shell.claim' for m,p in self.calls),count)
            self.assertIsNone(second.lease)
            self.assertEqual(self.client.lease,owner)
        finally:
            task.cancel();await asyncio.gather(task,return_exceptions=True)
    async def test_gap_resync_drops_stale_delta(self):
        p=self.peers[-1]
        new={**self.state['movement'],'position':[4,2,-3]}
        self.state['movement']=new;self.revision+=5
        p.write(frame(self.delta(999,self.revision,{'movement':new})))
        await p.drain()
        await self.until(lambda:self.snapshot_requests==1 and self.client.state['movement']['position']==[4,2,-3])
        self.assertEqual(self.client.revision,self.revision)
    async def test_disconnect_new_token_fresh_lease_no_mutation_replay(self):
        await self.client.call('surface.focus',{'surfaceId':'a','intent':'keyboard'})
        await self.client.overlay(True)
        old=self.client.lease
        self.peers[-1].close();self.state['shell']={'leases':[]}
        await self.until(lambda:self.connections>=2 and self.client.ready and self.client.lease is not None)
        self.assertNotEqual(self.client.lease,old)
        self.assertFalse(self.client.director)
        self.assertEqual(self.tokens,2)
        self.assertEqual(sum(m=='surface.focus' for m,p in self.calls),1)
    async def test_lock_clears_director(self):
        await self.client.overlay(True)
        await asyncio.sleep(.03)
        self.state['shell']['leases'][0]['overlays'][0]['exclusiveInput']=False
        base=self.revision;self.revision+=1
        self.peers[-1].write(frame(self.delta(base,self.revision,{'shell':self.state['shell']})))
        await self.until(lambda:not self.client.director)
    async def test_unplug_releases_output_and_director(self):
        await self.client.overlay(True)
        base=self.revision;self.revision+=1;self.state['runtime']={'active':True,'outputs':['unrelated']};self.state['shell']={'leases':[]}
        self.peers[-1].write(frame(self.delta(base,self.revision,{'runtime':self.state['runtime'],'shell':self.state['shell']})))
        await self.until(lambda:self.client.lease is None)
        self.assertFalse(self.client.director)
        self.assertIsNone(self.client.output)
    async def test_revocation_unmaps(self):
        await self.client.overlay(True)
        self.peers[-1].write(frame({'jsonrpc':'2.0','method':'session.revoked','params':{'reason':'policy'}}))
        await self.until(lambda:any(e['type']=='connection' and e.get('status')=='disconnected' for e in self.events))
        self.assertFalse(self.client.director)
    async def test_dev_notice_never_becomes_production_transition(self):
        self.peers[-1].write(frame({'jsonrpc':'2.0','method':'runtime.notice','params':{'level':'info','code':'dev.location.transition','message':'{"phase":"departing"}'}}))
        await self.until(lambda:any(e['type']=='notice' and e.get('code')=='dev.location.transition' for e in self.events))
        self.assertFalse(any(e['type']=='transition' for e in self.events))
    async def test_unadvertised_action_never_sent(self):
        with self.assertRaises(RuntimeError):await self.client.call('camera.get',{})
        self.assertFalse(any(m=='camera.get' for m,p in self.calls))


class ClientV2Tests(ClientTests):
    """Run lease/framing lifecycle against the distinct frozen 0.2 schema too."""
    protocol = '0.2'

    def notify(self, method, params):
        self.peers[-1].write(frame({'jsonrpc':'2.0','method':method,'params':{
            **params, 'sessionId':'session','revision':self.revision}}, self.validator))

    def location(self, phase, progress, target=None, output='world'):
        value={'id':'jump-1','outputId':output,'monotonicMs':100,'phase':phase,'progress':progress,'to':target or {'position':[4,1,-3]}}
        self.state['location']={**self.state['location'],'transition':value}
        base=self.revision;self.revision+=1
        self.peers[-1].write(frame(self.delta(base,self.revision,{'location':self.state['location']}),self.validator))
        self.notify('location.transition',value)

    async def test_loading_hint_presents_without_patching_baseline(self):
        self.peers[-1].write(frame({'jsonrpc':'2.0','method':'location.transition','params':{
            'id':'jump-1','outputId':'world','monotonicMs':100,'phase':'departing','progress':0,'to':{'position':[4,1,-3]},'sessionId':'session','revision':self.revision+1}},self.validator))
        await asyncio.sleep(.03)
        self.assertTrue(any(e['type']=='transition' for e in self.events))
        self.assertIsNone(self.client.state['location']['transition'])
        self.assertLess(self.client.revision,self.client.native_hint['revision'])
        self.location('departing',0)
        await self.until(lambda:any(e['type']=='transition' for e in self.events))
        first=next(e for e in self.events if e['type']=='transition')
        self.location('travelling',.5)
        await self.until(lambda:any(e.get('phase')=='transit' for e in self.events))
        self.location('arrived',1)
        await self.until(lambda:any(e.get('phase')=='arrived' for e in self.events))
        arrivals=[e for e in self.events if e.get('phase')=='arrived']
        self.assertEqual(arrivals[0]['id'],first['id'])
        self.assertEqual(arrivals[0]['revision'],self.revision)
        self.client.publish()
        self.assertEqual(sum(e.get('phase')=='arrived' for e in self.events),1)
        self.peers[-1].close();self.state['shell']={'leases':[]}
        await self.until(lambda:self.connections>=2 and self.client.ready and self.client.lease)
        self.assertEqual(sum(e.get('phase')=='arrived' for e in self.events),1,'Terminal reconnect snapshot must not replay the warp')

    async def test_snapshot_mid_jump_and_cancellation(self):
        self.state['location']['transition']={'id':'jump-1','outputId':'world','monotonicMs':100,'phase':'travelling','progress':.4,'to':{'zoneId':'courtyard'}}
        self.state['location']['zones']=[{'id':'courtyard','name':'Quiet courtyard','bounds':{'min':[-10,-10,-10],'max':[10,10,10]}}]
        self.revision+=1
        await self.client.resync()
        events=[e for e in self.events if e['type']=='transition']
        self.assertEqual([e['phase'] for e in events],['departing','transit'])
        self.assertEqual(events[0]['to']['name'],'Quiet courtyard')
        self.location('cancelled',.4)
        await self.until(lambda:any(e.get('phase')=='failed' for e in self.events))

    async def test_native_ui_events_are_lease_scoped(self):
        self.notify('ui.opened',{'leaseId':'some-other-shell','outputId':'world','panel':'overview'})
        await asyncio.sleep(.03)
        self.assertFalse(self.client.director)
        self.notify('ui.opened',{'leaseId':self.client.lease,'outputId':'world','panel':'overview'})
        await self.until(lambda:self.client.director)
        self.notify('ui.closed',{'leaseId':self.client.lease,'outputId':'world'})
        await self.until(lambda:not self.client.director)
        self.assertFalse(any(m=='ui.close' for m,p in self.calls), 'A core close hint must not cause a dismissal feedback loop')

    async def test_world_loading_is_indeterminate_and_output_scoped(self):
        self.client.worlds=[{'id':'com.hyprune.garden','name':'Quiet garden','spawns':[]}]
        self.location('loading',None,{'worldId':'com.hyprune.garden'},output='unrelated')
        await self.until(lambda:self.client.revision==self.revision)
        self.assertFalse(any(e['type']=='transition' for e in self.events))
        self.location('loading',None,{'worldId':'com.hyprune.garden'})
        await self.until(lambda:any(e.get('phase')=='loading' for e in self.events))
        loading=next(e for e in self.events if e.get('phase')=='loading')
        self.assertTrue(loading['indeterminate'])
        self.assertEqual(loading['to'],{'id':'com.hyprune.garden','name':'Quiet garden','subtitle':'LOCATION / CORE TRAVEL'})
        self.location('failed',None,{'worldId':'com.hyprune.garden'})
        await self.until(lambda:any(e.get('phase')=='failed' for e in self.events))
        self.assertEqual(self.client.state['world']['id'],'com.hyprune.observatory')

    async def test_native_events_discard_other_session(self):
        self.peers[-1].write(frame({'jsonrpc':'2.0','method':'ui.opened','params':{
            'leaseId':self.client.lease,'outputId':'world','panel':'overview','sessionId':'stale','revision':self.revision}},self.validator))
        await asyncio.sleep(.03)
        self.assertTrue(self.client.ready)
        self.assertFalse(self.client.director)

    async def test_coalesced_open_close_does_not_reopen(self):
        self.notify('ui.opened',{'leaseId':self.client.lease,'outputId':'world','panel':'overview'})
        self.notify('ui.closed',{'leaseId':self.client.lease,'outputId':'world'})
        await asyncio.sleep(.05)
        self.assertFalse(self.client.director)
        self.assertFalse(any(m=='shell.overlay' and p['visible'] for m,p in self.calls))

    async def test_daemon_revision_reset_accepts_fresh_ui_request(self):
        self.revision=1000
        await self.client.overlay(True)
        await self.until(lambda:self.client.revision==self.revision)
        self.peers[-1].close();self.state['shell']={'leases':[]};self.revision=0
        await self.until(lambda:self.connections>=2 and self.client.ready and self.client.lease)
        self.notify('ui.opened',{'leaseId':self.client.lease,'outputId':'world','panel':'overview'})
        await self.until(lambda:self.client.director)

if __name__=='__main__':unittest.main()
