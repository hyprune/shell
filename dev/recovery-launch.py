#!/usr/bin/env python3
"""Nested-only fault launcher; production has no injection endpoint."""
import argparse,asyncio,json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(os.environ['HYPRUNE_RECOVERY_SHELL'])/'bridge'))
import client,launch
control=Path(os.environ['HYPRUNE_RECOVERY_CONTROL'])
original=client.read_packet
async def read_packet(reader):
    data=await original(reader)
    if (control/'invalid').exists():
        obj=json.loads(data)
        if obj.get('method')=='state.delta':
            (control/'invalid').unlink()
            obj['params']['changes']['world']={'id':'','spawnId':'redaction-canary'}
            (control/'injected').touch()
            return json.dumps(obj).encode()
    return data
client.read_packet=read_packet
class FaultClient(client.Client):
    async def run(self):
        async def faults():
            while True:
                if (control/'load-world').exists() and self.ready:
                    world=(control/'load-world').read_text();(control/'load-world').unlink()
                    await self.call('world.load',{'worldId':world})
                if (control/'disconnect').exists() and self.writer and self.ready:
                    (control/'disconnect').unlink();self.writer.close();(control/'disconnected').touch()
                await asyncio.sleep(.05)
        task=asyncio.create_task(faults())
        try:await super().run()
        finally:task.cancel();await asyncio.gather(task,return_exceptions=True)
launch.Client=FaultClient
p=argparse.ArgumentParser()
p.add_argument('--protocol',default='0.15');p.add_argument('--world-package',action='append',default=[])
a=p.parse_args();a.socket=os.environ['HYPRUNE_SOCKET'];a.token_fd=int(os.environ['HYPRUNE_TOKEN_FD']);a.output=[];a.presentation=None;a.client_id='com.hyprune.shell';a.tour=False
asyncio.run(launch.main(a))
