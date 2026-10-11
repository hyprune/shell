#!/usr/bin/env python3
"""IPC 0.7/0.8 graphics, hold and workspace acceptance using core's verified nested lifetime.
Run: flock /tmp/worldshell-nested.lock python3 dev/hud-concepts.py
No source changes or controls outside the nested compositor.
"""
import argparse, json, os, pathlib, signal, subprocess, sys, tempfile, time
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent)); import devenv  # noqa: E402
ROOT=pathlib.Path(__file__).resolve().parent.parent
CORE=pathlib.Path(os.environ.get('HYPRUNE_CORE_DIR',str(ROOT.parent/'core')))
sys.path.insert(0,str(CORE/'dev/nested'))
import session as s
import m3b
from ctl import verified
from m2 import wait, keys, pose
GALLERY=devenv.gallery_dir()
PROTOCOL=os.environ.get('HYPRUNE_FOLLOWUP_PROTOCOL','0.12' if os.environ.get('HYPRUNE_HUD_INTERACTION') else '0.13' if os.environ.get('HYPRUNE_HUD_AUTHORING') and not os.environ.get('HYPRUNE_HUD_INK_PERSISTENCE') else '0.14' if os.environ.get('HYPRUNE_HUD_INK_PERSISTENCE') else '0.15')
SHOTS=GALLERY/'screenshots/hud-concepts'
SHOTS.mkdir(parents=True,exist_ok=True)

def acceptance(client,children,args,shell_token,socketpath):
    # A real desktop inventory, including a deliberately long application title.
    s.ctl('eval','hl.dispatch(hl.dsp.focus({workspace="11"}))')
    children.append(s.envrun('kitty','--class','hyprune-polish-localisation','--title','Localisation workspace companion','bash','--noprofile','--norc',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
    time.sleep(.5)
    s.ctl('eval', 'hl.dispatch(hl.dsp.workspace.rename({workspace="11",name="Arbeitsplatzorganisation — research, collaboration and extended localisation review"}))')
    s.ctl('eval','hl.dispatch(hl.dsp.focus({workspace="10"}))')
    title='Engineering — quarterly planning, localisation review and distributed workspace observations — '+ 'long title ' * 12
    children.append(s.envrun('kitty','--class','hyprune-polish-terminal','--title',title,'bash','--noprofile','--norc',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
    time.sleep(1)
    client.call('world.load',{'worldId':'com.hyprune.lumen-reach'})
    client.call('workspace.bind',{'id':10,'worldId':'com.hyprune.lumen-reach','areaId':'sun-court'})
    sub=client.call('state.subscribe',{'topics':['state']})['subscriptionId']
    def state():return client.call('state.snapshot',{'subscriptionId':sub})['snapshot']['state']
    s.ctl('eval','hl.plugin.hyprune.toggle("HEADLESS-1")')
    wait(lambda:state()['runtime']['active'])
    if os.environ.get('HYPRUNE_HUD_PLACEMENT'):
        # Diagnose a moving core contract before starting the real shell.
        sys.path.insert(0,str(ROOT/'bridge'))
        from protocol import V15_VALIDATOR, validate_response
        validate_response({'jsonrpc':'2.0','id':'preflight','result':client.hello},'session.hello',V15_VALIDATOR)
        V15_VALIDATOR.evolve(schema={'$ref':V15_VALIDATOR.schema['$id']+'#/$defs/state'}).validate(state())
    # Install original sample assets into this harness's private package only.
    import shutil
    package=s.STATE/'worlds/com.hyprune.lumen-reach/world.json'
    manifest=json.loads(package.read_text());manifest.setdefault('extensions',{})['com.hyprune.hud-style']={'theme':'hud/theme.json'}
    package.write_text(json.dumps(manifest))
    shutil.copytree(ROOT/'dev/styles/signal-amber/hud',package.parent/'hud',dirs_exist_ok=True)
    r,w=os.pipe();os.write(w,(shell_token+'\n').encode());os.close(w)
    if os.environ.get('HYPRUNE_HUD_PLACEMENT'):
        # Test the first-launch default with preferences scoped to this fixture.
        (s.STATE/'hud-preferences.json').unlink(missing_ok=True)
    _,env=verified();env.update(HYPRUNE_TOKEN_FD=str(r),HYPRUNE_PROTOCOL=PROTOCOL,HYPRUNE_SOCKET=str(socketpath),HYPRUNE_OUTPUT_SCREEN='HEADLESS-1',HYPRUNE_DEV_AUTOMATION='1',HYPRUNE_SHELL_PREFERENCES=str(s.STATE/'hud-preferences.json'))
    log=open(s.STATE/'shell.log','w')
    world_args=['--world-package',str(s.STATE/'worlds/org.hyprune.visibility/world.json')] if os.environ.get('HYPRUNE_HUD_AUTHORING') else []
    shell=subprocess.Popen(['python3',str(ROOT/'bridge/launch.py'),'--protocol',PROTOCOL,'--world-package',str(package),*world_args],env=env,pass_fds=(r,),stdout=log,stderr=subprocess.STDOUT)
    os.close(r);children.append(shell)
    def child():
        assert shell.poll() is None
        return next((int(p) for p in pathlib.Path(f'/proc/{shell.pid}/task/{shell.pid}/children').read_text().split() if pathlib.Path(f'/proc/{p}/comm').read_text().strip() in ['qs','quickshell']),None)
    qpid=wait(child)
    def ui(*args):
        verified()
        return subprocess.check_output([str(s.HERE/'ctl.py'),'env','qs','ipc','--pid',str(qpid),'call','preview',*map(str,args)],text=True).strip()
    def status():
        try:return json.loads(ui('status'))
        except (subprocess.CalledProcessError,json.JSONDecodeError):return {}
    wait(lambda:status().get('lease'))
    wait(lambda:not status().get('warp'))
    wait(lambda:any('Arbeitsplatzorganisation' in w['title'] for w in status().get('workspaces',[])))
    client.call('movement.set',{'modeId':'com.hyprune.fly'})
    pose(client,[-8,2,12])
    def shot(name):
        time.sleep(.4)
        audit=json.loads(ui('layoutAudit'))
        assert audit['labels'] > 0 and not audit['failures'], (name,audit)
        subprocess.run([str(s.HERE/'ctl.py'),'shot',str(SHOTS/(name+'.png'))],check=True)
    def opened():
        if not status().get('director'):
            keys('-P','Tab','-s','2300','-p','Tab')
            wait(lambda:status().get('director'))
    def closed():
        if status().get('director'):
            keys('-k','Escape');wait(lambda:not status().get('director'))
    def resolution(w,h,scale):
        s.ctl('eval',f'hl.monitor({{output="HEADLESS-1",mode="{w}x{h}@60",position="1600x0",scale={scale}}})');time.sleep(1)
    evidence = {'protocol':PROTOCOL, 'captures':[]}
    homes={'sun-court':[-8,2,12],'array-hall':[8,2,-34],'rime-vault':[38,-4.3,-79],'signal-rise':[54,2,-125]}
    if os.environ.get('HYPRUNE_HUD_PLACEMENT'):
        from hud_placement_check import check
        check(client,children,ui,status,state,shot,resolution,opened,closed)
        return
    if os.environ.get('HYPRUNE_HUD_GRAPHICS_COMPAT'):
        from hud_authoring_check import check_compat
        check_compat(client,ui,status,shot,opened)
        return
    if os.environ.get('HYPRUNE_HUD_AUTHORING'):
        from hud_authoring_check import check
        check(client,children,ui,status,state,shot,resolution,opened,closed)
        return
    if os.environ.get('HYPRUNE_HUD_INTERACTION'):
        from hud_interaction_check import check
        check(client,children,ui,status,state,shot,resolution)
        return
    if any(os.environ.get(k) for k in ['HYPRUNE_HUD_CONVEX','HYPRUNE_HUD_TEXT','HYPRUNE_HUD_CONTRAST']):
        contrast_review=bool(os.environ.get('HYPRUNE_HUD_CONTRAST'))
        if contrast_review:
            import hud_contrast
        contrast_results=[]
        def raw_shot(path):
            subprocess.run([str(s.HERE/'ctl.py'),'shot',str(path)],check=True)
        text_review=contrast_review or bool(os.environ.get('HYPRUNE_HUD_TEXT'))
        version='v5' if contrast_review else ('v4' if text_review else 'v3')
        ui('curvature',.8);ui('worldStyles','false');keys('-k','2')
        for width,height,scale in [(1920,1080,1),(2560,1440,1),(3840,2160,1),(1920,1080,2),(2560,1440,2),(3840,2160,2)]:
            resolution(width,height,scale)
            for concept in ['Adventure','Instrument','Minimal']:
                ui('concept',concept)
                for home in ['sun-court','rime-vault']:
                    pose(client,homes[home]);time.sleep(.5)
                    name=f'{concept.lower()}-{home}-{height}p-s{scale}-{version}'
                    shot(name);evidence['captures'].append(name)
                    if contrast_review and concept=='Adventure':
                        contrast_results.append(hud_contrast.capture(ui,raw_shot,SHOTS/(name+'.png')))
                if contrast_review and concept=='Adventure':
                    ui('contrastProbe','white')
                    name=f'adventure-white-{height}p-s{scale}-{version}'
                    shot(name);evidence['captures'].append(name)
                    contrast_results.append(hud_contrast.capture(ui,raw_shot,SHOTS/(name+'.png'),white=True))
                    (SHOTS/'contrast-v5-measurements.json').write_text(json.dumps(contrast_results,indent=2)+'\n')
                    hud_contrast.verify(contrast_results)
            print('PASS convex resolution',height,scale,flush=True)
            if os.environ.get('HYPRUNE_HUD_QUICK'): break
        resolution(1920,1080,1);pose(client,homes['sun-court'])
        for concept in ['Adventure','Instrument','Minimal']:
            ui('concept',concept);time.sleep(2)
            comparisons=[(0,'flat'),(.8,'curved')] + ([] if text_review else [(1,'maximum')])
            for strength,suffix in comparisons:
                ui('curvature',strength);name=f'{concept.lower()}-sun-court-{suffix}-{version}'
                shot(name);evidence['captures'].append(name)
        if text_review:
            ui('concept','Adventure');ui('worldStyles','true');time.sleep(1)
            assert status()['worldStyle']=='com.hyprune.lumen-reach'
            shot(f'adventure-world-outline-{version}');evidence['captures'].append(f'adventure-world-outline-{version}')
            ui('worldStyles','false');time.sleep(1)
            shot(f'adventure-world-outline-optout-{version}');evidence['captures'].append(f'adventure-world-outline-optout-{version}')
        errors=(s.STATE/'shell.log').read_text()
        assert not any(x in errors for x in ['ERROR','ReferenceError','TypeError','Binding loop','Unable to assign','Presentation:']),errors[-6000:]
        evidence.update(defaultStrength=.8,quick=bool(os.environ.get('HYPRUNE_HUD_QUICK')),validation='All layout audits passed; no QML errors')
        (SHOTS/f'{"text" if text_review else "convex"}-{version}-verification.json').write_text(json.dumps(evidence,indent=2)+'\n')
        if contrast_review:
            hud_contrast.verify(contrast_results)
        print('PASS HUD',version,flush=True)
        return
    if os.environ.get('HYPRUNE_HUD_REVIEW'):
        # Preserve the owner's original shots for direct before/after review.
        ui('curvature',.8);ui('worldStyles','false');keys('-k','2')
        for width,height,scale in [(1920,1080,1),(2560,1440,1),(3840,2160,1),(1920,1080,2),(2560,1440,2),(3840,2160,2)]:
            resolution(width,height,scale)
            for concept in ['Adventure','Instrument','Minimal']:
                ui('concept',concept)
                for home in ['sun-court','rime-vault']:
                    pose(client,homes[home]);time.sleep(.5)
                    shot(f'{concept.lower()}-{home}-{height}p-s{scale}-v2')
            opened();ui('tab',8);ui('scrollPage',0);shot(f'performance-{height}p-s{scale}-v2')
            ui('scrollPage',1);shot(f'performance-effects-{height}p-s{scale}-v2');closed()
            print('PASS review resolution',height,scale,flush=True)
            if os.environ.get('HYPRUNE_HUD_QUICK'): break
        resolution(1920,1080,1);pose(client,homes['sun-court']);ui('concept','Adventure')
        ui('curvature',0);shot('adventure-sun-court-flat-v2');ui('curvature',.8);shot('adventure-sun-court-curved-v2')
        # Auto exercises the blocked USB-C policy without requesting offload On.
        client.call('graphics.set',{'patch':{'offload':'auto'}})
        opened();ui('tab',8);ui('scrollPage',0);time.sleep(1);shot('performance-renderer-auto-policy-v2')
        client.call('graphics.set',{'patch':{'offload':'off'}})
        errors=(s.STATE/'shell.log').read_text()
        assert not any(x in errors for x in ['ERROR','ReferenceError','TypeError','Binding loop','Unable to assign','Presentation:']),errors[-6000:]
        (SHOTS/'review-v2-verification.json').write_text(json.dumps({'protocol':PROTOCOL,'graphics':client.call('graphics.get',{}),'log':'No QML errors; layout audits passed','quick':bool(os.environ.get('HYPRUNE_HUD_QUICK'))},indent=2)+'\n')
        print('PASS HUD review v2',flush=True)
        return
    if os.environ.get('HYPRUNE_HUD_EVENTS_ONLY'):
        ui('concept','Adventure');ui('worldStyles','true')
        ui('select',1);wait(lambda:status()['banner']=='WAYPOINT SET');shot('waypoint-set-banner')
        client.call('workspace.bind',{'id':11,'worldId':'com.hyprune.lumen-reach','areaId':'array-hall'})
        ui('workspace',11);wait(lambda:state()['workspaces']['currentId']==11);wait(lambda:not status()['warp'],timeout=20)
        shot('workspace-focused-banner')
        assert status()['banner']=='WORKSPACE FOCUSED',status()['banner']
        client.call('waypoint.clear',{})
        print('PASS waypoint and workspace event banners',flush=True)
        return
    if os.environ.get('HYPRUNE_PERFORMANCE_ONLY'):
        opened();ui('tab',7);ui('settingsSection',1);wait(lambda:status()['tab']==8);ui('scrollPage',0);wait(lambda:status().get('graphics',{}).get('performance'))
        def select_value(key,position):
            assert ui('graphicsFocus',key)=='true'
            keys('-k','space','-k',position,'-k','Return');time.sleep(.3)
        before=client.call('graphics.get',{})
        select_value('offload','End')
        def settled():
            p=client.call('graphics.get',{})['performance']
            return p if p['activeRenderer']=='offload' or (p['mode']=='on' and p['reason'] not in ['off','warming','admitted','inactive']) else None
        changed=wait(settled,timeout=22)
        shot('performance-renderer-on')
        time.sleep(1);after=client.call('graphics.get',{})
        assert ui('graphicsFocus','offload')=='true'
        keys('-k','space','-k','Home','-k','Down','-k','Return')
        wait(lambda:client.call('graphics.get',{})['config']['offload']=='auto');time.sleep(1)
        automatic=client.call('graphics.get',{});shot('performance-renderer-auto-policy')
        select_value('offload','Home');wait(lambda:client.call('graphics.get',{})['performance']['activeRenderer']=='in-process')
        shot('performance-renderer-off')
        (SHOTS/'performance-renderer-verification.json').write_text(json.dumps({'before':before,'settled':changed,'after':after,'auto':automatic,'off':client.call('graphics.get',{}),'via':'Director Choice actual nested keyboard events'},indent=2)+'\n')
        for width,height,scale in [(1920,1080,1),(2560,1440,1),(3840,2160,1),(1920,1080,2),(2560,1440,2),(3840,2160,2)]:
            resolution(width,height,scale);ui('scrollPage',0);shot(f'performance-{height}p-s{scale}')
        resolution(1920,1080,1)
        closed();ui('worldStyles','true');ui('concept','Adventure')
        client.call('travel.start',{'to':{'position':[54,2,-125]},'durationMs':1600});wait(lambda:status()['warp']);shot('world-style-warp-ribbons');wait(lambda:not status()['warp'])
        assert state()['runtime']['active']
        print('PASS Performance renderer live control',changed['status'],changed['reason'],flush=True)
        return
    # IPC 0.8+ monotonic hold timing still animates through newer negotiations.
    config=state()['keymap']['config'];config['longHoldMs']=2000;client.call('input.set',{'config':config})
    held=s.envrun('wtype','-P','Tab','-s','1200','-p','Tab');children.append(held)
    wait(lambda:status().get('menuHold'));first=status()['holdProgress'];time.sleep(.3);second=status()['holdProgress']
    assert 0<=first<second<1,(first,second)
    shot('hold-progress');held.wait(timeout=5);wait(lambda:status()['holdProgress']==0)
    config['longHoldMs']=1000;client.call('input.set',{'config':config})
    evidence['hold']={'first':first,'second':second,'cancelled':True}
    ui('curvature',.8);ui('worldStyles','false')
    keys('-k','2')
    if tuple(map(int,PROTOCOL.split('.'))) >= (0,9):
        ui('concept','Adventure');wait(lambda:status()['concept']=='Adventure');time.sleep(.5)
        keys('-P','5','-s','900','-p','5');time.sleep(.3)
        assert status()['concept']=='Adventure'
        evidence['key5']='Physical 5 leaves the Settings concept unchanged'
    for width,height,scale in [(1920,1080,1),(2560,1440,1),(3840,2160,1),(1920,1080,2),(2560,1440,2),(3840,2160,2)]:
        resolution(width,height,scale)
        for concept in ['Adventure','Instrument','Minimal']:
            ui('concept',concept);wait(lambda:status()['concept']==concept)
            for home,position in homes.items():
                pose(client,position);time.sleep(.5)
                name=f'{concept.lower()}-{home}-{height}p-s{scale}'
                shot(name);evidence['captures'].append(name)
        opened();ui('tab',8);ui('scrollPage',0);shot(f'performance-{height}p-s{scale}')
        ui('scrollPage',1);shot(f'performance-effects-{height}p-s{scale}')
        ui('tab',7);ui('settingsSection',0);shot(f'appearance-{height}p-s{scale}');closed()
        print('PASS resolution',height,scale,flush=True)
        if os.environ.get('HYPRUNE_HUD_QUICK'): break
    resolution(1920,1080,1);pose(client,homes['sun-court']);ui('concept','Adventure')
    ui('curvature',0);shot('adventure-sun-court-flat');ui('curvature',.8);shot('adventure-sun-court-curved')
    from m2 import pointer
    for slot in [2,3,4]:
        keys('-k',str(slot));time.sleep(.2)
        before=status()['subtype'];pointer('scroll',1);wait(lambda:status()['subtype']!=before)
        shot('tool-'+str(slot)+'-wheel');evidence['tool'+str(slot)]={'before':before,'after':status()['subtype']}
    # Real Settings keyboard controls, independently verified against core.
    opened();ui('tab',8);ui('scrollPage',0)
    assert ui('graphicsFocus','quality')=='true'
    keys('-k','space','-k','End','-k','Return');wait(lambda:client.call('graphics.get',{})['config']['quality']=='ultra')
    ui('scrollPage',1);assert ui('graphicsFocus','bloom')=='true'
    keys('-k','space','-k','Home','-k','Down','-k','Return');wait(lambda:client.call('graphics.get',{})['config']['bloom']=='off')
    evidence['graphics']=client.call('graphics.get',{});shot('performance-custom');closed()
    keys('-k','F3');shot('performance-f3-verification');keys('-k','F3')
    client.call('graphics.set',{'patch':{'quality':'auto','bloom':None}})
    keys('-k','2');ui('concept','Instrument');wait(lambda:status()['concept']=='Instrument')
    saved=json.loads((s.STATE/'hud-preferences.json').read_text());assert saved['concept']=='Instrument'
    evidence['persisted']=saved
    ui('concept','Adventure')
    if not os.environ.get('HYPRUNE_HUD_QUICK'):
        with tempfile.TemporaryDirectory(prefix='hyprune-hud-') as temp:
            raw=pathlib.Path(temp)/'raw.mkv';encoded=pathlib.Path(temp)/'hud-concepts.mp4'
            rec=s.envrun('wf-recorder','-o','HEADLESS-1','-r','30','-D','--no-dmabuf','-c','libx264','-p','preset=ultrafast','-p','crf=19','-x','yuv420p','-f',str(raw),stdout=open(s.STATE/'hud-recorder.log','w'),stderr=subprocess.STDOUT)
            children.append(rec);start=time.monotonic()
            try:
                time.sleep(3);ui('curvature',0);time.sleep(2);ui('curvature',.8);time.sleep(3)
                for slot in [2,3,4]:
                    keys('-k',str(slot));time.sleep(1)
                    for i in range(2):pointer('scroll',1);time.sleep(1.1)
                ui('concept','Instrument');time.sleep(3);pose(client,homes['rime-vault']);time.sleep(4)
                ui('concept','Minimal');time.sleep(3);keys('-k','3');pointer('scroll',1);time.sleep(3)
                opened();ui('tab',7);ui('settingsSection',0);time.sleep(3)
                ui('tab',8);ui('scrollPage',0);time.sleep(3);ui('scrollPage',1);time.sleep(3)
                closed();pose(client,homes['sun-court']);keys('-k','5');time.sleep(max(1,53-(time.monotonic()-start)))
            finally:rec.send_signal(signal.SIGINT);rec.wait(timeout=20)
            subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(raw),'-an','-vf','scale=1920:1080:in_range=pc:out_range=tv,fps=30','-c:v','libx264','-crf','21','-preset','medium','-pix_fmt','yuv420p','-color_range','tv','-movflags','+faststart',str(encoded)],check=True)
            probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(encoded)]))
            assert 45<=float(probe['format']['duration'])<=60
            import shutil
            destination=devenv.video_dir()/'hud-concepts.mp4';shutil.move(str(encoded),destination)
            destination.with_suffix('.json').write_text(json.dumps({'title':'Hyprune · three HUD concepts','tag':'shell','notes':'Adventure, Instrument and Minimal. Real core tools and wheel subtypes, HUD-only perspective, Sun Court and Rime Vault, Appearance and Performance. Concept selection is Settings/config only; key 5 never changes it. Native Quickshell rendering inside the locked isolated nested compositor. Original geometric icons; no private reference asset included.','duration':probe['format']['duration']},indent=2)+'\n')
            evidence['videoSeconds']=probe['format']['duration']
    pose(client,homes['signal-rise'])
    for concept in ['Adventure','Instrument','Minimal']:
        ui('concept',concept);ui('worldStyles','false');shot('style-'+concept.lower()+'-base')
        ui('worldStyles','true');wait(lambda:status()['worldStyle']=='com.hyprune.lumen-reach');shot('style-'+concept.lower()+'-signal-amber')
    client.call('world.load',{'worldId':'com.hyprune.switchyard'});wait(lambda:status()['world']=='com.hyprune.switchyard');wait(lambda:status()['worldStyle'] is None)
    evidence['worldStyle']='Sample applied; all concepts preserve layout; opt-out and leaving restore defaults'
    errors=(s.STATE/'shell.log').read_text()
    assert not any(x in errors for x in ['ERROR','ReferenceError','TypeError','Binding loop','Unable to assign','Presentation:']),errors[-6000:]
    (SHOTS/'verification.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print('PASS HUD concepts',flush=True)

if __name__=='__main__':
    os.environ.setdefault('HYPRUNE_NESTED_PROTOCOL',PROTOCOL)
    if os.environ.get('HYPRUNE_HUD_INTERACTION'):
        subprocess.run([sys.executable,str(CORE/'tests/fixtures/climbing.py')],check=True)
        os.environ['HYPRUNE_M2_PACKAGE']=str(CORE/'tests/fixtures/climbing')
    m3b.acceptance=acceptance
    if os.environ.get('HYPRUNE_HUD_AUTHORING'):
        import authoring
        authoring.acceptance=acceptance
    if os.environ.get('HYPRUNE_HUD_INK_PERSISTENCE'):
        import ink
        ink.acceptance=acceptance
    if os.environ.get('HYPRUNE_HUD_PLACEMENT'):
        # Like core's Placement acceptance, start with no saved fixture placements.
        (s.HERE/'.m3b-state/layout.json').unlink(missing_ok=True)
    s.run(argparse.Namespace(ink=bool(os.environ.get('HYPRUNE_HUD_INK_PERSISTENCE')),authoring=bool(os.environ.get("HYPRUNE_HUD_AUTHORING")),m3b=True,m3a=False,m2=False,m1=False,integration=False,live=False,serve=False,record=False,visible=False))
