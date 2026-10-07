#!/usr/bin/env node
// Development supervisor around the SDK's actual MockDaemon. No protocol fork.
// Node inherited stdio pipes are duplex socketpairs on Linux. FD 3 supplies a
// new one-shot launch token only when the bridge asks for one; never a token file.
import {spawn} from 'node:child_process';
import {randomUUID} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
const sdk=process.env.HYPRUNE_SDK_DIR || '../sdk';
const {validateWire}=await import(pathToFileURL(sdk+'/dist/src/validation.js'));
const {MockDaemon,GRANTS}=await import(pathToFileURL(sdk+'/dist/src/mock.js'));
const [scenarioPath,...launch]=process.argv.slice(2);
const daemon=new MockDaemon({protocol:process.env.HYPRUNE_MOCK_PREVIEW==='1'?'0.1-mock.1':'0.1',scenario:JSON.parse(readFileSync(scenarioPath,'utf8'))});
// A local scenario decorator delays mock world activation and emits loading
// notices from the daemon side. The frames remain schema-valid SDK protocol.
// `dev.location.transition` is NEVER interpreted in production IPC 0.1.
const warp=JSON.parse(readFileSync(new URL('./warp-scenario.json',import.meta.url),'utf8'));
let warping=false;
const originalHandle=daemon.handle.bind(daemon);
async function jump(peer,message,to,workspace=false) {
    if(warping) { daemon.error(peer,message.id,-32004,'A location jump is already in progress');return; }
    warping=true;
    const id=randomUUID(),details=warp.destinations[to] || {name:to,subtitle:'WORLD DESTINATION'};
    const publish=(phase,progress)=>daemon.broadcast('runtime.notice',{level:'info',code:'dev.location.transition',message:JSON.stringify({id,phase,progress,to:{id:to,...details}})});
    const started=Date.now();
    try {
        for(const sample of warp.samples) {
            await new Promise(r=>setTimeout(r,Math.max(0,started+sample.at-Date.now())));
            if(peer.socket.destroyed || peer.closing){publish('failed',sample.progress);return;}
            publish(sample.phase,sample.progress);
        }
        await new Promise(r=>setTimeout(r,Math.max(0,started+warp.durationMs-Date.now())));
        if(peer.socket.destroyed || peer.closing){publish('failed',.94);return;}
        if(workspace) daemon.commit({world:{id:to,spawnId:'arrival'}});
        originalHandle(peer,message); // normal SDK validation, grant check, mutation and reply
        publish(daemon.state.world?.id===to?'arrived':'failed',1);
    } finally {warping=false;}
}
if(process.env.HYPRUNE_MOCK_PREVIEW==='1') {
    daemon.handle=(peer,message)=>{
        try{validateWire(message,daemon.protocol);}catch{return originalHandle(peer,message)}
        if(peer.ids.has(message.id))return originalHandle(peer,message);
        const validLoad=message?.method==='world.load' && peer.methods.includes('world.load') && daemon.scenario.worlds.some(w=>w.id===message.params?.worldId && (!message.params.spawnId || w.spawns.includes(message.params.spawnId)));
        const workspace=message?.method==='surface.focus' && message.params?.intent==='keyboard' && peer.methods.includes('surface.focus') && warp.workspaceLocations[message.params.surfaceId];
        const to=validLoad?message.params.worldId:workspace;
        if(to && to!==daemon.state.world?.id) void jump(peer,message,to,!!workspace);
        else originalHandle(peer,message);
    };
}
await daemon.start();
console.error('hyprune-mock (SDK API): '+daemon.protocol+' listening at '+daemon.path);
const child=spawn(launch[0],launch.slice(1),{stdio:['inherit','inherit','inherit','pipe'],env:{...process.env,HYPRUNE_TOKEN_FD:'3',HYPRUNE_TOKEN_REFRESH:'1'}});
let input='';
child.stdio[3].on('data',data=>{
    input+=data.toString();
    while(input.includes('\n')) {
        const end=input.indexOf('\n'),request=input.slice(0,end);input=input.slice(end+1);
        if(request==='renew') child.stdio[3].write(daemon.issueToken('com.hyprune.shell',GRANTS)+'\n');
    }
});
child.stdio[3].on('error',()=>{});
let stopping=false;
async function stop() {if(stopping)return;stopping=true;child.kill('SIGTERM');await daemon.stop();}
process.once('SIGTERM',()=>void stop());process.once('SIGINT',()=>void stop());
child.once('exit',code=>{process.exitCode=stopping?0:(code || 0);void stop()});
child.once('error',e=>{console.error(e.message);process.exitCode=1;void stop()});
// Test-only faults, delivered to this supervisor PID by the locked capture harness.
process.on('SIGUSR1',()=>daemon.disconnectClients());
process.on('SIGUSR2',()=>daemon.revokeClients());
