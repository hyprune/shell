"""Real IPC 0.15 shell acceptance. Parent owns the isolated nested flock."""
import hashlib,json,math,subprocess,time
from pathlib import Path
import session as s
from m2 import wait,keys,pose

def check(client,children,ui,status,state,shot,resolution,opened,closed):
    assert client.hello['protocol']==status()['protocol']=='0.15'
    binary=next(s.STATE.glob('hyprune-*.so'))
    build_sha=hashlib.sha256(binary.read_bytes()).hexdigest()
    assert status()['concept']=='Adventure',status()
    children.append(s.envrun('wtype','-s','300000'));time.sleep(.2)
    device=s.envrun(str(s.ROOT/'build/nested-pointer'),'serve',stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True);children.append(device)
    def pointer(*args):
        device.stdin.write(' '.join(map(str,args))+'\n');device.stdin.flush();assert device.stdout.readline().strip()=='ok';time.sleep(.1)
    def hud():return json.loads(ui('interactionHud'))
    def queue():return state()['editor']['unplaced']
    def cap(sid):return next(v for v in s.camera()['captures'] if v['id']==sid)
    def aim(sid):
        v=cap(sid);x,y,z,w=v['rotation'];n=[2*(x*z+y*w),2*(y*z-x*w),1-2*(x*x+y*y)]
        pose(client,[v['position'][i]+3*n[i] for i in range(3)],math.atan2(-n[0],n[2]),math.asin(-n[1]));time.sleep(.3)
        wait(lambda:s.camera()['aim']==sid)
    def modified(mods,action,duration=650,midway=None):
        names={'Super_L':'logo','Shift_L':'shift','Control_L':'ctrl'}
        # Keep held modifiers and a test key in the same virtual keyboard/keymap.
        middle=['-s',str(duration)] if midway is None else ['-s',str(duration//2),*midway,'-s',str(duration-duration//2)]
        proc=s.envrun('wtype',*[x for mod in mods for x in ['-M',names[mod],'-P',mod]],*middle,*[x for mod in reversed(mods) for x in ['-p',mod,'-m',names[mod]]])
        children.append(proc);time.sleep(.15)
        try:action()
        finally:proc.wait(timeout=duration/1000+5)
    def click(button):pointer('button',button,1);pointer('button',button,0)
    client.call('runtime.exit',{});wait(lambda:not state()['runtime']['active'])
    client.call('world.load',{'worldId':'org.hyprune.m3b'})
    client.call('workspace.bind',{'id':20,'worldId':'org.hyprune.m3b','areaId':'sun-court'})
    s.ctl('eval','hl.dispatch(hl.dsp.focus({monitor="HEADLESS-1"}))')
    s.ctl('eval','hl.dispatch(hl.dsp.focus({workspace="20"}))')
    for i in range(3):
        title='Pocket '+str(i)+' — engineering notes, localisation review and extended workspace planning'
        children.append(s.envrun('kitty','--class','hyprune-pocket-'+str(i),'--title',title,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
        wait(lambda:any(a['title']==title for a in json.loads(s.ctl('clients','-j'))));time.sleep(.4)
    s.ctl('eval','hl.dispatch(hl.dsp.focus({workspace="1"}))')
    s.ctl('eval','hl.plugin.hyprune.toggle("HEADLESS-1")')
    wait(lambda:queue()['count']>=3 and state()['editor']['tool']==5)
    client.call('movement.set',{'modeId':'com.hyprune.fly'});pose(client,[0,2.3,4]);time.sleep(.4)
    wait(lambda:hud()['hudPlacementTile']['visible']);shot('adventure-pocket-first-entry-ipc015')
    for slot in range(1,6):
        keys('-k',str(slot));wait(lambda:state()['editor']['tool']==slot)
        expected=[value['label'] for value in state()['editor']['toolSlots'].values() if value]
        wait(lambda:sorted(a['label'] for a in status()['manipulation']['hints']['actions'])==sorted(expected))
    print('PASS all five tools use live core labels',flush=True)
    def gestures(name):
        expected=wait(lambda:state()['editor']['toolInput'] if state()['editor']['toolInput']['override'] else None)
        wait(lambda:status()['manipulation']['hints']['context']=='GLOBAL GESTURES')
        shown=status()['manipulation']['hints']['actions']
        assert [(a['slot'],a['label'],a['bindings']) for a in shown]==[(a['action'],a['label'],a['bindings']) for a in expected['gestures']]
        assert hud()['hudToolHints']['visible']
        shot('adventure-global-'+name+'-ipc015')
    modified(['Super_L'],lambda:gestures('super'),3500)
    wait(lambda:status()['manipulation']['hints']['context']=='')
    modified(['Super_L','Shift_L'],lambda:gestures('super-shift'),3500)
    wait(lambda:status()['manipulation']['hints']['context']=='')
    modified(['Super_L','Control_L'],lambda:gestures('super-ctrl'),3500)
    wait(lambda:status()['manipulation']['hints']['context']=='')
    print('PASS Super, Super+Shift, Super+Ctrl generic gesture overrides',flush=True)
    selected=queue()['selectedId'];pointer('scroll',-1);wait(lambda:queue()['selectedId']!=selected)
    sid=queue()['selectedId'];title=next(a['title'] for a in queue()['windows'] if a['surfaceId']==sid)
    pose(client,[0,2.3,4]);time.sleep(.3);click(272);wait(lambda:all(w['surfaceId']!=sid for w in queue()['windows']));aim(sid)
    keys('-k','5');wait(lambda:state()['editor']['tool']==5)
    assert status()['concept']=='Adventure'
    before=queue()['count']
    config=state()['keymap']['config'];original=config['modes']['world']['alternate']
    config['modes']['world']['alternate']=['F8'];client.call('input.set',{'config':config})
    wait(lambda:'F8' in hud()['hudToolHints']['text'])
    keys('-k','F8')
    wait(lambda:queue()['count']==before+1 and queue()['selectedId']==sid)
    wait(lambda:status()['manipulation']['placement']['app'] and status()['manipulation']['placement']['app']['title']==title)
    wait(lambda:status()['banner'].startswith('POCKETED'))
    shot('adventure-pocketed-ipc015')
    assert hud()['hudPlacementTile']['visible'] and hud()['hudPlacementTitle']['truncated']
    assert 'Pocket' in hud()['hudToolHints']['text']
    config['modes']['world']['alternate']=original;client.call('input.set',{'config':config})
    wait(lambda:'MMB' in hud()['hudToolHints']['text'])
    print('PASS physical 5, stash, long-title card and pocketed banner',flush=True)
    keys('-k','1');wait(lambda:hud()['hudUnplacedBadge']['visible']);shot('adventure-pocket-badge-ipc015')
    # Core owns entry selection; shell merely reflects it.
    client.call('runtime.exit',{});wait(lambda:not state()['runtime']['active'])
    s.ctl('eval','hl.plugin.hyprune.toggle("HEADLESS-1")')
    wait(lambda:state()['runtime']['active'] and state()['editor']['tool']==5)
    wait(lambda:hud()['hudPlacementTile']['visible']);shot('adventure-pocket-entry-ipc015')
    # True native free cursor must hide all actionable hints.
    pointer('button',275)
    wait(lambda:state()['editor']['mode']=='cursor')
    hidden=hud();assert not hidden['hudToolHints']['visible'] and not hidden['hudGhostIndicator']['visible'],hidden
    shot('adventure-pocket-cursor-ipc015');pointer('button',275);wait(lambda:state()['editor']['mode']=='world')
    # Place the selected pocket entry ahead, then pocket it again.
    pose(client,[0,2.3,4]);time.sleep(.3);click(272);wait(lambda:all(w['surfaceId']!=sid for w in queue()['windows']))
    aim(sid)
    click(274);wait(lambda:queue()['selectedId']==sid)
    pose(client,[0,2.3,4]);time.sleep(.3);click(272);wait(lambda:all(w['surfaceId']!=sid for w in queue()['windows']));keys('-k','1');aim(sid)
    # Hold the real carry gesture while checking both orientation labels.
    def carry():
        pointer('button',272,1)
        try:
            wait(lambda:isinstance(state()['editor']['carryFacing'],bool))
            start=state()['editor']['carryFacing'];wait(lambda:hud()['hudCarryOrientation']['visible'])
            shot('adventure-carry-'+('facing-you' if start else 'keep-angle')+'-ipc015')
            wait(lambda:state()['editor']['carryFacing']!=start)
            wait(lambda:('FACING YOU' if not start else 'KEEP ANGLE') in hud()['hudCarryOrientation']['text'])
            shot('adventure-carry-'+('facing-you' if not start else 'keep-angle')+'-ipc015')
        finally:pointer('button',272,0)
    modified(['Super_L'],carry,8000,midway=['-k','r'])
    aim(sid)
    modified(['Super_L','Shift_L'],lambda:pointer('scroll',1))
    feedback=wait(lambda:state()['editor']['contentScale'])
    wait(lambda:'SCALE ' in hud()['hudContentScale'].get('text','') and hud()['hudContentScale']['visible'])
    assert str(round(feedback['scale']*100))+'%' in hud()['hudContentScale']['text']
    shot('adventure-content-scale-ipc015')
    aim(sid);modified(['Super_L','Shift_L'],lambda:click(274))
    wait(lambda:state()['editor']['contentScale']['sequence']>feedback['sequence'])
    wait(lambda:hud()['hudContentScale']['visible'] and hud()['hudContentScale']['text'].startswith('RESET'))
    shot('adventure-content-reset-ipc015')
    sequence=state()['editor']['contentScale']['sequence']
    aim(sid);modified(['Super_L','Shift_L'],lambda:click(274))
    wait(lambda:state()['editor']['contentScale']['sequence']>sequence)
    wait(lambda:hud()['hudContentScale']['visible'] and hud()['hudContentScale']['text'].startswith('RESET'))
    # Resize outputs only after physical manipulation; native clients resize too.
    keys('-k','5');aim(sid);click(274);wait(lambda:queue()['selectedId']==sid)
    for w,h,scale in [(1920,1080,1),(2560,1440,1),(3840,2160,1),(1920,1080,2),(2560,1440,2),(3840,2160,2)]:
        resolution(w,h,scale)
        for concept in ['Adventure','Instrument','Minimal']:
            ui('concept',concept);shot(f'{concept.lower()}-pocket-{h}p-s{scale}-ipc015')
    resolution(1920,1080,1);ui('concept','Adventure')
    # Inspect updated Help and Appearance in the actual Director.
    opened();ui('tab',5);shot('help-placement-ipc015');ui('scrollPage',1);shot('help-placement-bindings-ipc015')
    ui('tab',6);ui('settingsSection',0);shot('appearance-adventure-ipc015');closed()
    client.call('runtime.exit',{});wait(lambda:not state()['runtime']['active'])
    client.call('world.load',{'worldId':'com.hyprune.switchyard'})
    wait(lambda:status()['readyText'])
    dest=Path.home()/'hyprune-gallery/screenshots/hud-concepts/ready-loaded-inactive-ipc015.png'
    subprocess.run([str(s.HERE/'ctl.py'),'shot',str(dest)],check=True)
    log=(s.STATE/'shell.log').read_text()
    assert not any(x in log for x in ['ERROR','ReferenceError','TypeError','Binding loop','Unable to assign','Invalid core frame','Presentation:']),log[-6000:]
    evidence={'protocol':'0.15','coreBaseCommit':subprocess.check_output(['git','-C',str(s.ROOT),'rev-parse','HEAD'],text=True).strip(),'coreBinarySha256':build_sha,'checks':['physical tool 5 preserves Adventure','core labels for all five tools','Super / Super+Shift / Super+Ctrl gesture overrides','Alternate remapped to F8 and physically used','stash and pocketed banner','MMB pockets and LMB places ahead','entry reflects core tool 5','free-cursor prompts hidden','carry facing/keep-angle with Super still held','live content scale and repeated reset','readiness notification','Help and Appearance','three concepts at three resolutions and scales 1/2'],'contentScale':feedback,'validation':'QML logs and layout audits passed'}
    (Path(__file__).resolve().parents[1]/'docs/evidence/placement-hud-015.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print('PASS IPC 0.15 Adventure, pocket and manipulation HUD',flush=True)
