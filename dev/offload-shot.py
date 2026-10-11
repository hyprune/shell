#!/usr/bin/env python3
"""Real IPC 0.18 check of the Graphics settings offload cap and GPU rows (core's nested lifetime).
Run from anywhere: flock /tmp/worldshell-nested.lock python3 dev/offload-shot.py
HYPRUNE_CORE_DIR selects the core checkout (needs IPC 0.18). Offload stays off: no dGPU use.
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
SHOTS=devenv.gallery_dir('screenshots/offload-0.18-2026-10-10')
SHOTS.mkdir(parents=True,exist_ok=True)

def acceptance(client,children,args,shell_token,socketpath):
    client.call('world.load',{'worldId':'com.hyprune.lumen-reach'})
    s.ctl('eval','hl.plugin.hyprune.toggle("HEADLESS-1")');wait(lambda:s.camera()['active'])
    r,w=os.pipe();os.write(w,(shell_token+'\n').encode());os.close(w)
    _,env=verified();env.update(HYPRUNE_TOKEN_FD=str(r),HYPRUNE_PROTOCOL='0.18',HYPRUNE_SOCKET=str(socketpath),HYPRUNE_OUTPUT_SCREEN='HEADLESS-1',HYPRUNE_DEV_AUTOMATION='1')
    log=open(s.STATE/'shell.log','w')
    shell=subprocess.Popen(['python3',str(ROOT/'bridge/launch.py'),'--protocol','0.18'],env=env,pass_fds=(r,),stdout=log,stderr=subprocess.STDOUT)
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
    assert status()['protocol']=='0.18',status().get('protocol')
    def shot(name):
        time.sleep(.6);subprocess.run([str(s.HERE/'ctl.py'),'shot',str(SHOTS/(name+'.png'))],check=True)
    def graphics():return status()['graphics']
    keys('-P','Tab','-s','1150','-p','Tab');wait(lambda:status().get('director'))
    ui('tab',7);ui('settingsSection',1);ui('settingsScroll',1)
    assert graphics()['config'].get('offload_power_cap_w',0) is None and graphics()['config'].get('offload_device')=='auto',graphics()['config']
    perf=graphics()['performance'];assert perf.get('capSource') and 'device' in perf,perf
    shot('shell-offload-cap-automatic')
    ui('graphicsPatch',json.dumps({'offload_power_cap_w':100}));wait(lambda:graphics()['config'].get('offload_power_cap_w')==100)
    shot('shell-offload-cap-custom-100w')
    # The device is resolved once offload is engaged. "auto" is refused on battery/USB-C
    # (no dGPU work) and only reports the selected GPU; it is switched off again below.
    ui('graphicsPatch',json.dumps({'offload':'auto'}));wait(lambda:graphics()['performance'].get('device'),10)
    device=graphics()['performance'].get('device');shot('shell-offload-gpu-automatic')
    if device:
        ui('graphicsPatch',json.dumps({'offload_device':device['pci']}));wait(lambda:graphics()['config'].get('offload_device')==device['pci'])
        shot('shell-offload-gpu-pinned')
    ui('graphicsPatch',json.dumps({'offload_power_cap_w':None,'offload_device':'auto','offload':'off'}))
    wait(lambda:graphics()['config'].get('offload_power_cap_w',0) is None and graphics()['config'].get('offload_device')=='auto')
    keys('-k','Escape')
    errors=(s.STATE/'shell.log').read_text()
    assert not any(x in errors for x in ['ReferenceError','TypeError','Binding loop','Unable to assign']),errors[-3000:]
    print('PASS shell offload rows: 0.18 negotiated, automatic/custom cap and GPU pin set and restored',flush=True)

if __name__=='__main__':
    os.environ['HYPRUNE_GRAPHICS_FILE']=str(CORE/'dev/nested/.m3b-state/offload-graphics.json')
    pathlib.Path(os.environ['HYPRUNE_GRAPHICS_FILE']).unlink(missing_ok=True)
    m3b.acceptance=acceptance
    s.run(argparse.Namespace(m3b=True,m3a=False,m2=False,m1=False,integration=False,live=False,serve=False,record=False,visible=False))
