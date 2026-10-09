"""Real core 0.12 HUD checks, called within hud-concepts.py's nested flock."""
import json, subprocess, time
from pathlib import Path
import session as s
from m2 import keys, wait, pose


def check(client,children,ui,status,state,shot,resolution):
    assert client.hello['protocol']==status()['protocol']=='0.12'
    ui('worldStyles','false');ui('curvature',.8)
    device=s.envrun(str(s.ROOT/'build/nested-pointer'),'serve',stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
    children.append(device)
    def back():
        device.stdin.write('button 275\n');device.stdin.flush()
        assert device.stdout.readline().strip()=='ok'
    def chord():keys('-M','logo','-P','Super_L','-s','40','-k','Tab','-p','Super_L','-m','logo')
    def hud():return json.loads(ui('interactionHud'))
    def cursor_on(gesture):
        gesture();wait(lambda:state()['editor']['mode']=='cursor')
        wait(lambda:hud()['hudCursorChip']['visible'])
        h=hud()
        assert h['hudCursorText']['text']=='CURSOR · Back / Super+Tab to return'
        assert not h['hudCursorText']['truncated']
        assert not any(h[n]['visible'] for n in ['hudClimbPrompt','hudWorldHints','hudToolHint'])
        assert s.camera()['nativeCursorVisible']
        return h
    def cursor_off(gesture):
        gesture();wait(lambda:state()['editor']['mode']!='cursor')
        wait(lambda:not hud()['hudCursorChip']['visible'] and hud()['hudWorldHints']['visible'])
    # A normal world entry and both real return gestures, before climbing.
    cursor_on(chord);shot('cursor-world-ipc012');cursor_off(back)
    client.call('world.load',{'worldId':'org.hyprune.climbing'})
    wait(lambda:status()['world']=='org.hyprune.climbing' and not status()['warp'])
    client.call('movement.set',{'modeId':'com.hyprune.walk'})
    results=[]
    for width,height,scale in [(1920,1080,1),(2560,1440,1),(3840,2160,1),(1920,1080,2)]:
        resolution(width,height,scale)
        for concept,mechanic in [('Adventure','grab'),('Instrument','look-to-climb'),('Minimal','auto-traverse')]:
            ui('concept',concept)
            s.ctl('eval',f'hl.plugin.hyprune.config({{movement={{climb_mode="{mechanic}"}},player={{move_inertia=0,look_inertia=0}}}})')
            # Falling into the climb volume catches and holds in every mechanic.
            s.ctl('eval','hl.plugin.hyprune.camera(0,4,.55,0,.9)')
            wait(lambda:state()['movement']['state']=='climbing')
            wait(lambda:hud()['hudClimbPrompt']['visible'])
            h=hud();prompt=state()['movement']['prompt']
            assert h['hudClimbText']['text']==prompt and prompt
            assert not h['hudClimbText']['truncated'],h
            name=f'{concept.lower()}-{height}p-s{scale}-ipc012'
            shot('climb-'+name)
            cursor=cursor_on(back);shot('cursor-'+name)
            before=state()['movement']['position'];keys('-P','w','-s','180','-p','w')
            assert state()['movement']['position']==before
            cursor_off(chord)
            # Input handover clears climbing; a fresh attach restores the prompt.
            s.ctl('eval','hl.plugin.hyprune.camera(0,4,.55,0,.9)')
            wait(lambda:state()['movement']['state']=='climbing' and hud()['hudClimbPrompt']['visible'])
            keys('-k','space');wait(lambda:state()['movement']['state']!='climbing')
            wait(lambda:not hud()['hudClimbPrompt']['visible'])
            results.append(dict(concept=concept,mechanic=mechanic,resolution=f'{width}x{height}',scale=scale,prompt=prompt,cursorPromptsHidden=True,detachedPromptHidden=True))
            print('PASS HUD interaction',name,flush=True)
    log=(s.STATE/'shell.log').read_text()
    assert not any(x in log for x in ['ERROR','ReferenceError','TypeError','Binding loop','Unable to assign','Invalid core frame','Presentation:']),log[-5000:]
    evidence={'protocol':'0.12','coreCommit':subprocess.check_output(['git','-C',str(s.ROOT),'rev-parse','HEAD'],text=True).strip(),'results':results,'worldEntry':'Super+Tab entry / Back return','climbingEntry':'Back entry / Super+Tab return; native cursor and frozen camera verified','validation':'No QML/schema errors; layout audits and actual visible-item checks passed','coreFollowups':['Core-owned centre ladder hint remains visible in cursor mode (Plugin.cpp climbing prompt generation lacks suspended-cursor guard). Shell-owned hints are hidden.','Core dev/live/live.py explicitly requests 0.10; switch to 0.12 for new states.']}
    dest=Path(__file__).resolve().parents[1]/'docs/evidence/hud-interaction-012.json'
    dest.write_text(json.dumps(evidence,indent=2)+'\n')
    print('PASS IPC 0.12 HUD interactions',flush=True)
