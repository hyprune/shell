#!/usr/bin/env python3
"""IPC 0.7/0.8 graphics, hold and workspace acceptance using core's verified nested lifetime.
Run: flock /tmp/worldshell-nested.lock python3 dev/followup-core.py
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
PROTOCOL=os.environ.get('HYPRUNE_FOLLOWUP_PROTOCOL','0.8')
SHOTS=GALLERY/'screenshots/hyprune-shell-followup'
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
    _,env=verified();env.update(HYPRUNE_TOKEN_FD=str(r),HYPRUNE_PROTOCOL=PROTOCOL,HYPRUNE_SOCKET=str(socketpath),HYPRUNE_OUTPUT_SCREEN='HEADLESS-1',HYPRUNE_DEV_AUTOMATION='1',HYPRUNE_SHELL_PREFERENCES=str(s.STATE/'followup-shell-preferences.json'))
    log=open(s.STATE/'shell.log','w')
    shell=subprocess.Popen(['python3',str(ROOT/'bridge/launch.py'),'--protocol',PROTOCOL],env=env,pass_fds=(r,),stdout=log,stderr=subprocess.STDOUT)
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
            keys('-P','Tab','-s','2300','-p','Tab')
            wait(lambda:status().get('director'))
    def closed():
        if status().get('director'):
            keys('-k','Escape');wait(lambda:not status().get('director'))
    def resolution(w,h,scale):
        s.ctl('eval',f'hl.monitor({{output="HEADLESS-1",mode="{w}x{h}@60",position="1600x0",scale={scale}}})');time.sleep(1)
    evidence = {'protocol':PROTOCOL}
    assert status()['protocol'] == PROTOCOL
    if PROTOCOL == '0.8':
        config = state()['keymap']['config'];config['longHoldMs'] = 2000
        client.call('input.set',{'config':config})
        # Keep the virtual keyboard alive through press/release. Observe actual
        # rendered ring progress while core owns the hold and seat.
        held = s.envrun('wtype','-P','Tab','-s','1400','-p','Tab')
        children.append(held)
        wait(lambda:status().get('menuHold'))
        first = status()['holdProgress'];time.sleep(.3);second = status()['holdProgress']
        assert 0 <= first < second < 1, (first,second)
        shot('hold-08-progress')
        held.wait(timeout=5)
        wait(lambda:status().get('menuHold') is None and status()['holdProgress'] == 0)
        assert not status()['director']
        evidence['hold'] = {'first':first,'second':second,'cancelled':True}
        config['longHoldMs'] = 1000;client.call('input.set',{'config':config})
        wait(lambda:state()['keymap']['config']['longHoldMs']==1000);time.sleep(.2)
        (SHOTS/('verification-'+PROTOCOL+'.json')).write_text(json.dumps(evidence,indent=2)+'\n')
        try:
            opened()
        except AssertionError:
            evidence['coreBlocker'] = 'Core Plugin.cpp shell.overlay exclusiveInput version gate omits IPC 0.8 (-32007)'
            evidence['shellLog'] = (s.STATE/'shell.log').read_text()
            (SHOTS/('verification-'+PROTOCOL+'.json')).write_text(json.dumps(evidence,indent=2)+'\n')
            raise
        assert status()['menuHold'] is None
        evidence['hold']['fired'] = True
        closed()
    # Render F3 before/after, and observe independent core graphics.get results.
    keys('-k','F3');wait(lambda:s.camera()['debug'])
    before = client.call('graphics.get',{})
    shot('graphics-'+PROTOCOL+'-before-f3')
    opened();ui('tabNamed', 'settings');ui('settingsSection',1)
    wait(lambda:status().get('graphics'))
    def choose(key, moves):
        assert ui('graphicsFocus',key) == 'true'
        keys('-k','space');time.sleep(.15)
        for move in moves:keys('-k',move)
        keys('-k','Return');time.sleep(.35)
    choose('quality',['End'])
    wait(lambda:client.call('graphics.get',{})['config']['quality']=='ultra')
    choose('bloom',['Home','Down'])
    changed = wait(lambda:(g if (g:=client.call('graphics.get',{}))['effective']['quality']=='ultra' and g['effective']['bloom']=='off' else None))
    shot('graphics-'+PROTOCOL+'-settings-ultra-bloom-off')
    closed();shot('graphics-'+PROTOCOL+'-after-f3')
    assert s.camera()['debug']
    assert s.camera()['config']['graphics']['quality']=='ultra'
    assert s.camera()['config']['graphics']['bloom']=='off'
    persisted = json.loads(pathlib.Path(changed['path']).read_text())
    assert persisted['quality']=='ultra' and persisted['bloom']=='off'
    evidence['graphics']={'before':before,'after':changed,'renderer':s.camera()['config']['graphics'],'persisted':persisted,'via':'Settings ComboBox real nested keyboard events'}
    opened();ui('tabNamed', 'workspaces')
    for width,height,scale in [(1920,1080,2),(2560,1440,1),(3840,2160,2)]:
        resolution(width,height,scale)
        audit=json.loads(ui('layoutAudit'));assert audit['apps'] >= 2 and not audit['failures'],audit
        ui('scrollPage',0);shot(f'workspaces-{PROTOCOL}-{height}p-s{scale}')
        ui('scrollPage',1);shot(f'workspaces-{PROTOCOL}-{height}p-s{scale}-detail')
    log.flush()
    errors=(s.STATE/'shell.log').read_text()
    assert not any(x in errors for x in ['ERROR','ReferenceError','TypeError','Binding loop','Unable to assign','Presentation:']),errors[-4000:]
    (SHOTS/('verification-'+PROTOCOL+'.json')).write_text(json.dumps(evidence,indent=2)+'\n')
    print('PASS shell follow-up',PROTOCOL,flush=True)

if __name__=='__main__':
    m3b.acceptance=acceptance
    s.run(argparse.Namespace(m3b=True,m3a=False,m2=False,m1=False,integration=False,live=False,serve=False,record=False,visible=False))
