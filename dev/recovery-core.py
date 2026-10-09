#!/usr/bin/env python3
"""Run under flock /tmp/worldshell-nested.lock; package path is local env only.
By default a generic core fixture (format 0.5, HUD style, visibility regions) is
generated. HYPRUNE_RECOVERY_WORLD may supply a local test package instead. No asset,
identifier, frame dump, or screenshot is saved to this repository or the public gallery.
"""
import argparse,json,os,pathlib,shutil,subprocess,sys,tempfile,time
ROOT=pathlib.Path(__file__).resolve().parents[1];CORE=ROOT.parent/'core'
sys.path.insert(0,str(CORE/'dev/nested'))
import session as s
import live_check
from ctl import verified
from m2 import wait,keys
LUMEN='com.hyprune.lumen-reach'

def generic(tmp):
    subprocess.run([sys.executable,str(CORE/'tests/fixtures/visibility.py')],check=True,stdout=subprocess.DEVNULL)
    package=tmp/'package';shutil.copytree(CORE/'tests/fixtures/visibility',package)
    manifest=json.loads((package/'world.json').read_text())
    manifest.setdefault('extensions',{})['com.hyprune.hud-style']={'theme':'hud/test.json'}
    (package/'hud').mkdir(exist_ok=True);(package/'hud/test.json').write_text(json.dumps({'version':1,'colors':{'accent':'#88ddff'}}))
    (package/'world.json').write_text(json.dumps(manifest));return package

def acceptance(identity,children):
    _,env=verified()
    with tempfile.TemporaryDirectory(prefix='hyprune-recovery-') as tmp:
        tmp=pathlib.Path(tmp);control=tmp/'control';control.mkdir()
        local='HYPRUNE_RECOVERY_WORLD' in os.environ
        package=pathlib.Path(os.environ['HYPRUNE_RECOVERY_WORLD']).resolve() if local else generic(tmp)
        manifest=json.loads((package/'world.json').read_text())
        assert manifest['formatVersion']=='0.5'
        assert manifest.get('extensions',{}).get('com.hyprune.hud-style')
        assert manifest.get('visibility'), 'Choose a package with visibility regions'
        wrapper=tmp/'shell';(wrapper/'bridge').mkdir(parents=True)
        (wrapper/'qml').symlink_to(ROOT/'qml')
        for source in (ROOT/'bridge').glob('*.py'):
            (wrapper/'bridge'/source.name).symlink_to(ROOT/'dev/recovery-launch.py' if source.name=='launch.py' else source)
        state=tmp/'state';state.mkdir()
        env.update(HYPRUNE_SHELL_DIR=str(wrapper),HYPRUNE_RECOVERY_SHELL=str(ROOT),HYPRUNE_RECOVERY_CONTROL=str(control),HYPRUNE_DEV_AUTOMATION='1',HYPRUNE_SHELL_PREFERENCES=str(tmp/'preferences.json'))
        def command(name):
            verified()
            args=[str(CORE/'dev/live'/name),'--instance',identity['signature'],'--state-dir',str(state)]
            if name=='up':
                for world in [ROOT.parent/'worlds/dist/com.hyprune.lumen-reach',package]:args+=['--world',str(world)]
            result=subprocess.run(args,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
            if result.returncode:
                # Output may contain private package names. Retain only in /tmp.
                pathlib.Path('/tmp/hyprune-recovery-launch-error.log').write_text(result.stdout)
                raise AssertionError('Nested launcher failed; private log is in /tmp')
        def events():
            out=[]
            for line in (state/'shell.log').read_text().splitlines():
                try:out.append(json.loads(line))
                except ValueError:pass
            return out
        def live_count():return sum(e.get('type')=='connection' and e.get('status')=='live' for e in events())
        try:
            command('up')
            record=json.loads((state/'state.json').read_text())
            # The verified launcher's process record owns its exact shell child.
            processes=json.loads((pathlib.Path(record['runroot'])/'processes.json').read_text())
            bridge=next(p['record']['pid'] for p in processes if p['group'])
            def qpid():
                for pid in pathlib.Path(f'/proc/{bridge}/task/{bridge}/children').read_text().split():
                    if pathlib.Path(f'/proc/{pid}/comm').read_text().strip() in ['qs','quickshell']:return pid
            pid=wait(qpid)
            def ui(*args):
                verified();return subprocess.check_output([str(s.HERE/'ctl.py'),'env','qs','ipc','--pid',pid,'call','preview',*map(str,args)],text=True).strip()
            def status():return json.loads(ui('status'))
            def observed():
                path=control/'observed.json'
                return json.loads(path.read_text()) if path.exists() else {}
            def mark(key='frames'):return observed().get(key,0)
            def check(label,v):
                assert v['instances']>0 and v['unzoned']>=1 and v['emptyArea']==0,label+': '+json.dumps(v)
                print('PASS',label+': nonempty unzoned instances, areaId omitted',json.dumps(v),flush=True)
            def unzoned(label,since):
                # Assert on state frames received after `since`, not a stale one.
                check(label,wait(lambda:observed() if mark()>since and observed().get('instances') else None,timeout=20))
            def snapshot(label,since):
                check(label,wait(lambda:observed()['lastSnapshot'] if mark('snapshots')>since else None,timeout=20))
            children.append(s.envrun('wtype','-s','300000'));time.sleep(.2)
            device=s.envrun(str(CORE/'build/nested-pointer'),'serve',stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True);children.append(device)
            def pointer(*args):
                device.stdin.write(' '.join(map(str,args))+'\n');device.stdin.flush();assert device.stdout.readline().strip()=='ok';time.sleep(.1)
            def place():
                # Tool 5 LMB mounts a pocketed client in free space; workspace 8 is unbound.
                keys('-k','5');wait(lambda:observed().get('tool')==5)
                before=observed()['queue']
                for turn in range(4):
                    if turn:pointer(400,0);time.sleep(.3)
                    pointer('button',272)
                    try:wait(lambda:observed().get('queue')==before-1,timeout=3);return
                    except AssertionError:print('placement retry',json.dumps(observed()),flush=True)
                raise AssertionError('tool-5 placement did not mount: '+json.dumps(observed()))
            s.ctl('eval','hl.dispatch(hl.dsp.focus({monitor="HEADLESS-1"}))')
            s.ctl('eval','hl.dispatch(hl.dsp.focus({workspace="8"}))')
            for n in range(2):children.append(s.envrun('kitty','--class','recovery-fixture-'+str(n),'--title','Recovery fixture '+str(n),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
            wait(lambda:sum(w['title'].startswith('Recovery fixture') for w in json.loads(s.ctl('clients','-j')))==2);time.sleep(.5)
            s.ctl('eval','hl.dispatch(hl.dsp.focus({workspace="91"}))')
            s.ctl('eval','hl.plugin.hyprune.toggle("HEADLESS-1")')
            wait(lambda:status()['lease'])
            wait(lambda:not status()['warp'])
            wait(lambda:observed().get('queue')==2)
            place()
            def load(world):
                since=mark();(control/'load-world').write_text(world)
                wait(lambda:status()['world']==world and not status()['warp'],timeout=40);return since
            load(manifest['id']);wait(lambda:observed().get('queue')==2);place()
            before=live_count()
            # Audited warps: each world now holds one saved free placement for an unbound client.
            for index,world in enumerate([LUMEN,manifest['id']]):
                unzoned('warp %d'%(index+1),load(world))
            assert status()['worldStyle']==manifest['id']
            assert live_count()==before and not any(e.get('type')=='protocol.invalid' for e in events())
            print('PASS styled world + visibility warps with unzoned instances, no invalid frames or reconnect',flush=True)
            since=mark('snapshots');(control/'invalid').touch();wait(lambda:(control/'injected').exists())
            wait(lambda:any(e.get('type')=='protocol.invalid' for e in events()))
            revision=status()['revision'];wait(lambda:status()['revision']>revision)
            assert live_count()==before and status()['hudVisible']
            entry=next(e for e in events() if e.get('type')=='protocol.invalid')
            assert entry['path']=='/params/changes/world/id' and 'redaction-canary' not in json.dumps(entry)
            print('PASS invalid frame quarantined; redacted diagnostic and snapshot recovery',flush=True)
            snapshot('invalid-frame recovery snapshot',since)
            for _ in range(2):
                since=mark('snapshots');(control/'disconnect').touch()
                wait(lambda:live_count()>before,timeout=20);before=live_count()
                wait(lambda:status()['lease'] and status()['hudVisible'],timeout=20)
                assert status()['world']==manifest['id']
                snapshot('reconnect snapshot',since)
            log=(state/'shell.log').read_text()
            assert 'FD exhausted' not in log and 'redaction-canary' not in log
            assert sum(e.get('type')=='protocol.invalid' for e in events())==1,'only the injected frame may be invalid'
            assert not any(x in log for x in ['ReferenceError','TypeError','Binding loop','Unable to assign'])
            print('PASS two forced bridge disconnects reauthenticate and reclaim HUD',flush=True)
            evidence={'protocol':'0.15','nestedOnly':True,'package':'local package; no identifiers or assets retained' if local else 'generic core visibility fixture with HUD style','checks':['styled world 0.5 with visibility regions','real clients mounted by tool-5 placement on unbound world workspace','nonempty unzoned mount instances with areaId omitted after each warp','no reconnect or invalid frame through warps','invalid delta discarded','redacted schema path and excerpt','snapshot recovery on same session','two forced socket disconnects','renewed one-shot credentials','HUD lease restored','unzoned instances valid after recovery and each reconnect','no invalid frame other than the injected one'],'invalidFrameDiagnostic':entry}
            (ROOT/'docs/evidence/bridge-recovery.json').write_text(json.dumps(evidence,indent=2)+'\n')
        finally:
            if (state/'shell.log').exists():pathlib.Path('/tmp/hyprune-recovery-shell.log').write_text((state/'shell.log').read_text())
            command('down')

if __name__=='__main__':
    live_check.acceptance=acceptance
    s.run(argparse.Namespace(live=True,m3b=False,m3a=False,m2=False,m1=False,integration=False,serve=False,record=False,visible=False))
