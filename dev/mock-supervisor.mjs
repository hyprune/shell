#!/usr/bin/env node
// Actual SDK IPC 0.2 MockDaemon. Test-only adapters emulate the still-missing
// Wayland association and workspace mapping; no protocol fields/events are added.
import {spawn} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {fileURLToPath, pathToFileURL} from 'node:url';
const sdk=process.env.HYPRUNE_SDK_DIR || fileURLToPath(new URL('../../sdk', import.meta.url));
const {MockDaemon,GRANTS}=await import(pathToFileURL(sdk+'/dist/src/mock.js'));
const [scenarioPath,...launch]=process.argv.slice(2);
const scenario=JSON.parse(readFileSync(scenarioPath,'utf8'));
const daemon=new MockDaemon({protocol:'0.2',scenario});
const preview=process.env.HYPRUNE_MOCK_UI_ASSOCIATION==='1';
const workspaceLocations=JSON.parse(readFileSync(new URL('./workspace-locations.json',import.meta.url),'utf8'));
let child;
function associated(peer) {
    if(!preview || peer.clientId!=='com.hyprune.shell' || !child || child.exitCode!==null) return false;
    try {
        return readFileSync(`/proc/${child.pid}/task/${child.pid}/children`,'utf8').trim().split(/\s+/).some(pid=> {
            const name=readFileSync(`/proc/${pid}/comm`,'utf8').trim();
            const command=readFileSync(`/proc/${pid}/cmdline`,'utf8').split('\0');
            return ['qs','quickshell'].includes(name) && command.includes(process.env.HYPRUNE_SHELL_ROOT+'/qml');
        });
    } catch {return false;}
}
// The SDK handles framing, IDs, grants, schema checks and RPC responses first.
// This narrow execute hook models an accepted association only for our supervised
// QML child. Core never receives it; production keeps the real unsupported error.
const execute=daemon.execute.bind(daemon);
daemon.execute=(peer,method,params)=> {
    if(method==='shell.overlay' && params.exclusiveInput && associated(peer)) {
        const lease=daemon.lease(peer,params.leaseId);
        if(!lease.outputs.includes(params.outputId)) return execute(peer,method,params);
        daemon.commit({shell:{leases:daemon.state.shell.leases.map(l=>l.id===lease.id?{...l,overlays:l.overlays.map(o=>o.outputId===params.outputId?{...o,visible:params.visible,exclusiveInput:true}:o)}:l)}});
        return {revision:daemon.revision};
    }
    const to=workspaceLocations[params.surfaceId];
    if(method==='surface.focus' && params.intent==='keyboard' && associated(peer) && peer.methods.includes('world.load') &&
       to && to!==daemon.state.world?.id && daemon.state.surfaces.some(s=>s.id===params.surfaceId)) {
        return Promise.resolve(execute(peer,'world.load',{worldId:to})).then(()=>execute(peer,method,params));
    }
    return execute(peer,method,params);
};
await daemon.start();
console.error(`hyprune-mock (SDK API): ${daemon.protocol}; association emulator ${preview?'on':'off'}; ${daemon.path}`);
child=spawn(launch[0],launch.slice(1),{stdio:['inherit','inherit','inherit','pipe'],env:{...process.env,HYPRUNE_TOKEN_FD:'3',HYPRUNE_TOKEN_REFRESH:'1'}});
let input='';
child.stdio[3].on('data',data=> {
    input+=data.toString();
    while(input.includes('\n')) {
        const end=input.indexOf('\n'),request=input.slice(0,end);input=input.slice(end+1);
        if(request==='renew') child.stdio[3].write(daemon.issueToken('com.hyprune.shell',GRANTS.filter(g=>g!=='data.publish'))+'\n');
    }
});
child.stdio[3].on('error',()=>{});
let stopping=false;
async function stop(){if(stopping)return;stopping=true;child.kill('SIGTERM');await daemon.stop();}
process.once('SIGTERM',()=>void stop());process.once('SIGINT',()=>void stop());
child.once('exit',code=>{process.exitCode=stopping?0:(code || 0);void stop();});
child.once('error',error=>{console.error(error.message);process.exitCode=1;void stop();});
process.on('SIGUSR1',()=>daemon.disconnectClients());
process.on('SIGUSR2',()=>daemon.revokeClients());
// A diagnostic supervisor trigger feeds the SDK's core-owned hold timer. The
// shell has no hold timer; it receives canonical ui.opened after 350 ms.
process.on('SIGWINCH',()=>{daemon.hold(true);setTimeout(()=>daemon.hold(false),450);});
