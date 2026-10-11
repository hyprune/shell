#!/usr/bin/env python3
"""Real IPC 0.16 check of the Graphics settings Upscaler row (core's verified nested lifetime).
Run from anywhere: flock /tmp/worldshell-nested.lock python3 dev/upscaler-shot.py
HYPRUNE_CORE_DIR selects the core checkout (needs IPC 0.16). No owner-session control.
"""
import argparse, json, os, pathlib, subprocess, sys, time
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent)); import devenv  # noqa: E402
ROOT=pathlib.Path(__file__).resolve().parent.parent
CORE=pathlib.Path(os.environ.get('HYPRUNE_CORE_DIR',str(ROOT.parent/'core')))
sys.path.insert(0,str(CORE/'dev/nested'))
import session as s
import m3b
from ctl import verified
from m2 import wait, keys
SHOTS=devenv.gallery_dir()/'screenshots/optimise-2026-10'
SHOTS.mkdir(parents=True,exist_ok=True)

def acceptance(client,children,args,shell_token,socketpath):
    client.call('world.load',{'worldId':'com.hyprune.lumen-reach'})
    s.ctl('eval','hl.plugin.hyprune.toggle("HEADLESS-1")');wait(lambda:s.camera()['active'])
    r,w=os.pipe();os.write(w,(shell_token+'\n').encode());os.close(w)
    _,env=verified();env.update(HYPRUNE_TOKEN_FD=str(r),HYPRUNE_PROTOCOL='0.16',HYPRUNE_SOCKET=str(socketpath),HYPRUNE_OUTPUT_SCREEN='HEADLESS-1',HYPRUNE_DEV_AUTOMATION='1')
    log=open(s.STATE/'shell.log','w')
    shell=subprocess.Popen(['python3',str(ROOT/'bridge/launch.py'),'--protocol','0.16'],env=env,pass_fds=(r,),stdout=log,stderr=subprocess.STDOUT)
    os.close(r);children.append(shell)
    def child():
        assert shell.poll() is None,'shell exited; see shell.log'
        return next((int(p) for p in pathlib.Path(f'/proc/{shell.pid}/task/{shell.pid}/children').read_text().split() if pathlib.Path(f'/proc/{p}/comm').read_text().strip() in ['qs','quickshell']),None)
    qpid=wait(child)
    def ui(*a):
        verified();return subprocess.check_output([str(s.HERE/'ctl.py'),'env','qs','ipc','--pid',str(qpid),'call','preview',*map(str,a)],text=True).strip()
    def status():
        try:return json.loads(ui('status'))
        except (subprocess.CalledProcessError,json.JSONDecodeError):return {}
    wait(lambda:status().get('lease'));wait(lambda:status().get('graphics'))
    assert status()['protocol']=='0.16',status().get('protocol')
    def shot(name):
        time.sleep(.6);subprocess.run([str(s.HERE/'ctl.py'),'shot',str(SHOTS/(name+'.png'))],check=True)
    keys('-P','Tab','-s','1150','-p','Tab');wait(lambda:status().get('director'))
    ui('tab',7);ui('settingsSection',1);shot('shell-graphics-upscaler-preset')
    ui('settingsScroll',1);shot('shell-graphics-upscaler-preset-detail')  # native scale: Preset shows "Active: Bilinear (native scale)"
    ui('graphicsPatch',json.dumps({'upscaler':'bilinear'}))
    wait(lambda:status()['graphics']['config'].get('upscaler')=='bilinear')
    assert status()['graphics']['effective']['upscaler']=='bilinear'  # harness IPC is 0.8: core omits the key there
    shot('shell-graphics-upscaler-bilinear-detail')
    ui('graphicsPatch',json.dumps({'upscaler':None}))
    wait(lambda:status()['graphics']['config'].get('upscaler') is None)
    keys('-k','Escape')
    errors=(s.STATE/'shell.log').read_text()
    assert not any(x in errors for x in ['ReferenceError','TypeError','Binding loop','Unable to assign']),errors[-3000:]
    print('PASS shell upscaler row: 0.16 negotiated, bilinear set and restored through the shell',flush=True)

if __name__=='__main__':
    os.environ['HYPRUNE_GRAPHICS_FILE']=str(CORE/'dev/nested/.m3b-state/upscaler-graphics.json')
    pathlib.Path(os.environ['HYPRUNE_GRAPHICS_FILE']).unlink(missing_ok=True)
    m3b.acceptance=acceptance
    s.run(argparse.Namespace(m3b=True,m3a=False,m2=False,m1=False,integration=False,live=False,serve=False,record=False,visible=False))
