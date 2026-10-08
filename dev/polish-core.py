#!/usr/bin/env python3
"""Real IPC 0.7 visual/seat acceptance using core's verified nested lifetime.
Run: flock /tmp/worldshell-nested.lock python3 dev/polish-core.py
No source changes or controls outside the nested compositor.
"""
import argparse, json, os, pathlib, signal, subprocess, sys, tempfile, time
ROOT=pathlib.Path(__file__).resolve().parent.parent
CORE=pathlib.Path(os.environ.get('HYPRUNE_CORE_DIR',str(ROOT.parent/'core')))
sys.path.insert(0,str(CORE/'dev/nested'))
import session as s
import m3b
from ctl import verified
from m2 import wait, keys, pose
GALLERY=pathlib.Path.home()/'hyprune-gallery'
SHOTS=GALLERY/'screenshots/hyprune-shell-polish'
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
    r,w=os.pipe();os.write(w,(shell_token+'\n').encode());os.close(w)
    _,env=verified();env.update(HYPRUNE_TOKEN_FD=str(r),HYPRUNE_PROTOCOL='0.7',HYPRUNE_SOCKET=str(socketpath),HYPRUNE_OUTPUT_SCREEN='HEADLESS-1',HYPRUNE_DEV_AUTOMATION='1')
    log=open(s.STATE/'shell.log','w')
    shell=subprocess.Popen(['python3',str(ROOT/'bridge/launch.py'),'--protocol','0.7'],env=env,pass_fds=(r,),stdout=log,stderr=subprocess.STDOUT)
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
    assert any('Arbeitsplatzorganisation' in w['title'] for w in status()['workspaces'])
    client.call('movement.set',{'modeId':'com.hyprune.fly'})
    pose(client,[-8,2,12])
    def shot(name):
        time.sleep(.4)
        audit=json.loads(ui('layoutAudit'))
        assert audit['labels'] > 0 and not audit['failures'], (name,audit)
        subprocess.run([str(s.HERE/'ctl.py'),'shot',str(SHOTS/(name+'.png'))],check=True)
    def opened():
        if not status().get('director'):
            keys('-P','Tab','-s','1150','-p','Tab')
            wait(lambda:status().get('director'))
    def closed():
        if status().get('director'):
            keys('-k','Escape');wait(lambda:not status().get('director'))
    def resolution(w,h,scale):
        s.ctl('eval',f'hl.monitor({{output="HEADLESS-1",mode="{w}x{h}@60",position="1600x0",scale={scale}}})');time.sleep(1)
    ui('motion','true');ui('travel',0)
    wait(lambda:state()['location']['transition'] and 'position' in state()['location']['transition']['to'])
    wait(lambda:not status().get('warp'));ui('motion','false')
    evidence=[]
    for w,h in ([] if os.environ.get('HYPRUNE_POLISH_ONLY_NAMES') else [(1920,1080),(2560,1440),(3840,2160)]):
        for scale in [1,2]:
            resolution(w,h,scale);prefix=f'core-{h}p-s{scale}'
            closed();pose(client,[-8,2,12]);ui('curvature',0);shot(prefix+'-sun-court-flat')
            ui('curvature',.6);shot(prefix+'-sun-court-curved')
            pose(client,[38,-4.3,-79]);shot(prefix+'-rime-vault-curved')
            opened()
            for i,name in enumerate(['map','places','surfaces','workspaces','help','whats-new','settings']):
                ui('tab',i);shot(prefix+'-'+name)
            ui('settingsSection',1);shot(prefix+'-settings-graphics')
            ui('settingsScroll',1);shot(prefix+'-settings-graphics-detail')
            ui('settingsScroll',0)
            ui('settingsSection',2);shot(prefix+'-settings-input')
            ui('inputCapture','world','debug',2)
            wait(lambda:state()['keymap']['capture'] and state()['keymap']['capture']['status']=='waiting')
            shot(prefix+'-settings-capture')
            keys('-k','F8');wait(lambda:status().get('captured') and status()['captured']['binding']=='F8')
            ui('inputSave');wait(lambda:'F8' in state()['keymap']['config']['modes']['world']['debug'])
            shot(prefix+'-settings-captured')
            ui('theme','true');shot(prefix+'-settings-paper');ui('theme','false')
            ui('settingsSection',0)
            closed()
            client.call('travel.start',{'to':{'position':[-8,2,12]},'durationMs':1400})
            shot(prefix+'-warp')
            wait(lambda:not status().get('warp'))
            evidence.append({'width':w,'height':h,'scale':scale,'apps':status()['apps'],'capture':'F8'})
            print('PASS core visual/seat',prefix,flush=True)
    opened();ui('tab',6);ui('settingsSection',1)
    ui('graphicsPatch',json.dumps({'quality':'low','bloom':'off','fog':'linear','msaa':1,'normal_maps':False,'specular':False,'reflections':False,'ambient_occlusion':True,'alpha_haze':False,'anisotropy':1,'dynamic_resolution':False,'render_scale':.75,'target_fps':60,'fov':60,'sharpen':.5,'exposure':1,'bloom_strength':.15,'reduced_motion':True}))
    wait(lambda:status().get('graphics') and status()['graphics']['config']['quality']=='low')
    assert status()['graphics']['effective']['bloom']=='off'
    assert status()['graphics']['config']['sharpen']==.5
    shot('core-settings-graphics-low')
    ui('graphicsPatch',json.dumps({'quality':'auto',**{k:None for k in ['bloom','fog','msaa','normal_maps','specular','reflections','ambient_occlusion','alpha_haze','anisotropy']},'dynamic_resolution':True,'render_scale':'auto','reduced_motion':False}))
    wait(lambda:status()['graphics']['config']['quality']=='auto')
    ui('settingsSection',0);closed()
    # First load an unseen ID: readable fallback; subsequent visits use exact metadata.
    resolution(1920,1080,1)
    client.call('world.load',{'worldId':'com.hyprune.switchyard'})
    time.sleep(.15);shot('core-switchyard-arrival')
    wait(lambda:state()['world']['id']=='com.hyprune.switchyard');time.sleep(2)
    # Stress trusted world metadata in the harness's private installed copy only.
    package=s.STATE/'worlds/com.hyprune.lumen-reach/world.json'
    original=package.read_text();manifest=json.loads(original)
    manifest['name']='Lumen Reach — Institut für interplanetare Arbeitsplatzorganisation und langfristige Forschungskoordination'
    package.write_text(json.dumps(manifest))
    try:
        client.call('world.load',{'worldId':manifest['id']});wait(lambda:state()['world']['id']==manifest['id']);time.sleep(2)
        for w,h in [(1920,1080),(2560,1440),(3840,2160)]:
            for scale in [1,2]:
                resolution(w,h,scale);opened()
                for index,name in [(0,'map'),(1,'places'),(3,'workspaces')]:
                    ui('tab',index);ui('scrollPage',0);shot(f'core-{h}p-s{scale}-long-{name}')
                    if index in [1,3]:
                        ui('scrollPage',1);shot(f'core-{h}p-s{scale}-long-{name}-detail')
                        ui('scrollPage',0)
                closed()
    finally:package.write_text(original)
    if os.environ.get('HYPRUNE_POLISH_ONLY_NAMES'):
        print('PASS long app/workspace/world names at all six output configurations',flush=True)
        return
    client.call('world.load',{'worldId':'com.hyprune.lumen-reach'});time.sleep(2)
    resolution(1920,1080,1);pose(client,[-8,2,12]);closed();ui('curvature',.6)
    with tempfile.TemporaryDirectory(prefix='hyprune-polish-') as temp:
        raw=pathlib.Path(temp)/'raw.mkv';encoded=pathlib.Path(temp)/'hyprune-shell-polish.mp4'
        rec=s.envrun('wf-recorder','-o','HEADLESS-1','-r','30','-D','--no-dmabuf','-c','libx264','-p','preset=ultrafast','-p','crf=19','-x','yuv420p','-f',str(raw),stdout=open(s.STATE/'polish-recorder.log','w'),stderr=subprocess.STDOUT)
        children.append(rec);start=time.monotonic()
        try:
            time.sleep(3);ui('curvature',0);time.sleep(2);ui('curvature',.6);time.sleep(3)
            pose(client,[38,-4.3,-79]);time.sleep(4)
            opened()
            for i in range(7):ui('tab',i);time.sleep(2)
            closed();pose(client,[-8,2,12]);time.sleep(max(0,36-(time.monotonic()-start)))
        finally:rec.send_signal(signal.SIGINT);rec.wait(timeout=20)
        subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(raw),'-an','-vf','scale=1920:1080:in_range=pc:out_range=tv,fps=30','-c:v','libx264','-crf','21','-preset','medium','-pix_fmt','yuv420p','-color_range','tv','-movflags','+faststart',str(encoded)],check=True)
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(encoded)]))
        assert 30<=float(probe['format']['duration'])<=45
        assert probe['streams'][0]['width']==1920 and probe['streams'][0]['pix_fmt']=='yuv420p'
        destination=GALLERY/'videos/hyprune-shell-polish.mp4';destination.parent.mkdir(exist_ok=True)
        # Encode completely in /tmp; publish only a finished file to autocommit.
        import shutil
        shutil.move(str(encoded),destination)
        (destination.with_suffix('.json')).write_text(json.dumps({'title':'Hyprune shell polish — curved HUD','tag':'shell','notes':'Real core IPC 0.7 and Quickshell in isolated nested Hyprland. Sun Court and Rime Vault; flat/curved comparison followed by all seven Director pages. Passive scene-graph HUD transforms; flat menus. Automated seat capture and six output resolution/scale combinations. No owner-session controls. TAB ring is a static hint pending core hold-progress IPC.'},indent=2)+'\n')
    errors=(s.STATE/'shell.log').read_text()
    assert not any(x in errors for x in ['ERROR','ReferenceError','TypeError','Binding loop','Unable to assign']),errors
    (SHOTS/'core-verification.json').write_text(json.dumps({'matrix':evidence,'videoSeconds':probe['format']['duration'],'protocol':'0.7'},indent=2)+'\n')
    print('PASS real core polish, captures, video',flush=True)

if __name__=='__main__':
    # Core owns all lifetime validation/teardown. Replace only the acceptance
    # callback, leaving its sources untouched. Caller holds the global flock.
    os.environ['HYPRUNE_GRAPHICS_FILE']=str(CORE/'dev/nested/.m3b-state/polish-graphics.json')
    pathlib.Path(os.environ['HYPRUNE_GRAPHICS_FILE']).unlink(missing_ok=True)
    m3b.acceptance=acceptance
    s.run(argparse.Namespace(m3b=True,m3a=False,m2=False,m1=False,integration=False,live=False,serve=False,record=False,visible=False))
