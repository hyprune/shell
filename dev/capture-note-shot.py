#!/usr/bin/env python3
"""Real IPC 0.17 check of the capture note prompt (core's verified nested lifetime).
Run from anywhere: flock /tmp/worldshell-nested.lock python3 dev/capture-note-shot.py
HYPRUNE_CORE_DIR selects the core checkout (needs IPC 0.17). No owner-session control.

U -> type -> Enter writes the note into the capture JSON, index.jsonl and notes.md;
Esc writes none; Enter on an empty field writes ""; U, then Super+U while the prompt is
open, keeps both notes in order; navigation resumes right after (W moves). Stills of the
prompt in the Night and Day themes go to the gallery.
"""
import argparse, json, math, os, pathlib, shutil, subprocess, sys, time
ROOT=pathlib.Path(__file__).resolve().parent.parent
CORE=pathlib.Path(os.environ.get('HYPRUNE_CORE_DIR',str(ROOT.parent/'core')))
sys.path.insert(0,str(CORE/'dev/nested'))
import session as s
import m3b
from ctl import verified
from m2 import wait, keys, pose
SHOTS=pathlib.Path.home()/'hyprune-gallery/screenshots/capture-notes'
SHOTS.mkdir(parents=True,exist_ok=True)

def acceptance(client,children,args,shell_token,socketpath):
    passed=[]
    def check(name,ok,data=None):
        assert ok,(name,data);passed.append(name);print('PASS capture notes:',name,flush=True)
    client.call('world.load',{'worldId':'com.hyprune.lumen-reach'})
    s.ctl('eval','hl.plugin.hyprune.toggle("HEADLESS-1")');wait(lambda:s.camera()['active'])
    r,w=os.pipe();os.write(w,(shell_token+'\n').encode());os.close(w)
    _,env=verified();env.update(HYPRUNE_TOKEN_FD=str(r),HYPRUNE_PROTOCOL='0.17',HYPRUNE_SOCKET=str(socketpath),HYPRUNE_OUTPUT_SCREEN='HEADLESS-1',HYPRUNE_DEV_AUTOMATION='1')
    log=open(s.STATE/'shell.log','w')
    shell=subprocess.Popen(['python3',str(ROOT/'bridge/launch.py'),'--protocol','0.17'],env=env,pass_fds=(r,),stdout=log,stderr=subprocess.STDOUT)
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
    wait(lambda:status().get('lease'))
    check('shell negotiated 0.17',status().get('protocol')=='0.17',status().get('protocol'))
    captures=pathlib.Path(s.camera()['captureDirectory']);captures.mkdir(parents=True,exist_ok=True)
    for f in captures.glob('*'):f.unlink()
    client.call('movement.set',{'modeId':'com.hyprune.walk'});pose(client,[-8,1.7,12]);time.sleep(.8)
    def position():return s.camera()['position']
    def prompt():return status().get('notePrompt','')
    def capture(id):
        p=captures/(id+'.json');return json.loads(p.read_text()) if p.exists() else {}  # the write may still be queued
    def index():
        p=captures/'index.jsonl';return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []
    def press_u():
        before=prompt();keys('-k','u');return wait(lambda:prompt() not in ('',before) and prompt())
    def shot(name):
        time.sleep(.6);subprocess.run([str(s.HERE/'ctl.py'),'shot',str(SHOTS/(name+'.png'))],check=True)

    # 1. U -> type -> Enter: note in JSON, index and notes.md; world frozen while typing; W moves after.
    ui('theme','false');time.sleep(.3)
    first=press_u()
    check('U opens the note prompt',prompt()==first,first)
    standing=position();text='Brücke rail clips the stair, walk west'
    keys(text);wait(lambda:status().get('noteText')==text);check('the prompt has the keyboard (typed text arrives)',True)
    check('typing (incl. w/a/s/d) does not move the world',math.dist(position(),standing)<1e-3,{'before':standing,'after':position()})
    shot('capture-note-night')
    keys('-k','Return');keys('-P','w','-s','700','-p','w')  # no lost keys: walk straight away
    wait(lambda:prompt()=='');time.sleep(.3)
    check('navigation resumes after Enter (W walks)',math.dist(position(),standing)>.5,{'before':standing,'after':position()})
    wait(lambda:capture(first).get('note')==text)
    data=capture(first)
    check('note and noteTime in the capture JSON',data['note']==text and data['noteTimeMs']>=data['timestampMs'],{k:data.get(k) for k in ['note','noteTimeMs','timestampMs']})
    check('index.jsonl line',index()[-1]=={'timestampMs':data['timestampMs'],'noteTimeMs':data['noteTimeMs'],'capture':first+'.json','screenshot':first+'.png','note':text},index()[-1])
    check('notes.md line',text in (captures/'notes.md').read_text() and first+'.png' in (captures/'notes.md').read_text())

    # 2. Esc: nothing written, prompt gone, navigation back.
    second=press_u();keys('discard me');time.sleep(.3);keys('-k','Escape');wait(lambda:prompt()=='');time.sleep(1)
    check('Esc writes no note',(captures/(second+'.json')).exists() and 'note' not in capture(second) and len(index())==1,capture(second).get('note'))
    here=position();keys('-P','w','-s','500','-p','w');time.sleep(.2)
    check('navigation resumes after Esc',math.dist(position(),here)>.3)

    # 3. Empty Enter writes "".
    third=press_u();keys('-k','Return');wait(lambda:prompt()=='');wait(lambda:'note' in capture(third))
    check('empty Enter writes an empty note',capture(third)['note']=='' and index()[-1]['note']=='')

    # 4. U, then Super+U while the prompt is open: the pending note is saved as-is, next capture taken.
    a=press_u();keys('first of two');wait(lambda:status().get('noteText')=='first of two')
    keys('-M','logo','-P','Super_L','-s','40','-k','u','-p','Super_L','-m','logo')
    b=wait(lambda:prompt() not in ('',a) and prompt())
    check('Super+U in the prompt takes the next capture and keeps the prompt',b!=a and status().get('noteText')=='',{'a':a,'b':b})
    keys('second of two');keys('-k','Return');wait(lambda:prompt()=='')
    wait(lambda:capture(b).get('note')=='second of two')
    check('both notes kept, in capture order',capture(a)['note']=='first of two' and [l['capture'] for l in index()[-2:]]==[a+'.json',b+'.json'],[l['note'] for l in index()])

    # 5. Day theme still.
    ui('theme','true');time.sleep(.4);press_u();keys('missing handrail on the court stair');time.sleep(.3);shot('capture-note-day')
    keys('-k','Escape');wait(lambda:prompt()=='');ui('theme','false')

    errors=(s.STATE/'shell.log').read_text()
    check('shell log clean',not any(x in errors for x in ['ReferenceError','TypeError','Binding loop','Unable to assign','Traceback']),errors[-3000:])
    shutil.copy(captures/'notes.md',SHOTS/'notes-example.md')
    (SHOTS/'capture-notes-evidence.json').write_text(json.dumps({'nestedOnly':True,'checks':passed,'index':index()},indent=2,ensure_ascii=False)+'\n')
    print('PASS capture notes:',len(passed),'checks',flush=True)

if __name__=='__main__':
    os.environ['HYPRUNE_NESTED_PROTOCOL']='0.8'
    m3b.acceptance=acceptance
    s.run(argparse.Namespace(m3b=True,m3a=False,m2=False,m1=False,integration=False,live=False,serve=False,record=False,visible=False))
