#!/usr/bin/env python3
"""Run under flock /tmp/worldshell-nested.lock; package path is local env only.
HYPRUNE_RECOVERY_WORLD supplies a private local test package. No asset, identifier,
frame dump, or screenshot is saved to this repository or the public gallery.
"""
import argparse,json,os,pathlib,subprocess,sys,tempfile,time
ROOT=pathlib.Path(__file__).resolve().parents[1];CORE=ROOT.parent/'core'
sys.path.insert(0,str(CORE/'dev/nested'))
import session as s
import live_check
from ctl import verified
from m2 import wait

def acceptance(identity,children):
    _,env=verified()
    package=pathlib.Path(os.environ['HYPRUNE_RECOVERY_WORLD']).resolve()
    manifest=json.loads((package/'world.json').read_text())
    assert manifest['formatVersion']=='0.5'
    assert manifest.get('extensions',{}).get('com.hyprune.hud-style')
    assert manifest.get('visibility'), 'Choose a package with visibility regions'
    with tempfile.TemporaryDirectory(prefix='hyprune-recovery-') as tmp:
        tmp=pathlib.Path(tmp);control=tmp/'control';control.mkdir()
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
            s.ctl('eval','hl.dispatch(hl.dsp.focus({monitor="HEADLESS-1"}))')
            s.ctl('eval','hl.dispatch(hl.dsp.focus({workspace="8"}))')
            for n in range(2):children.append(s.envrun('kitty','--class','recovery-fixture-'+str(n),'--title','Recovery fixture',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
            time.sleep(1)
            s.ctl('eval','hl.plugin.hyprune.toggle("HEADLESS-1")')
            wait(lambda:status()['lease'])
            wait(lambda:not status()['warp'])
            before=live_count()
            # The launcher's normal world.load request and core warp lifecycle.
            (control/'load-world').write_text(manifest['id'])
            wait(lambda:status()['world']==manifest['id'] and not status()['warp'],timeout=40)
            assert status()['worldStyle']==manifest['id']
            assert live_count()==before and not any(e.get('type')=='protocol.invalid' for e in events())
            print('PASS local styled world + visibility warp without invalid frames',flush=True)
            (control/'invalid').touch();wait(lambda:(control/'injected').exists())
            wait(lambda:any(e.get('type')=='protocol.invalid' for e in events()))
            revision=status()['revision'];wait(lambda:status()['revision']>revision)
            assert live_count()==before and status()['hudVisible']
            entry=next(e for e in events() if e.get('type')=='protocol.invalid')
            assert entry['path']=='/params/changes/world/id' and 'redaction-canary' not in json.dumps(entry)
            print('PASS invalid frame quarantined; redacted diagnostic and snapshot recovery',flush=True)
            for _ in range(2):
                (control/'disconnect').touch()
                wait(lambda:live_count()>before,timeout=20);before=live_count()
                wait(lambda:status()['lease'] and status()['hudVisible'],timeout=20)
                assert status()['world']==manifest['id']
            log=(state/'shell.log').read_text()
            assert 'FD exhausted' not in log and 'redaction-canary' not in log
            assert not any(x in log for x in ['ReferenceError','TypeError','Binding loop','Unable to assign'])
            print('PASS two forced bridge disconnects reauthenticate and reclaim HUD',flush=True)
            evidence={'protocol':'0.15','nestedOnly':True,'privatePackage':'local only; no identifiers or assets retained','checks':['styled world 0.5 with visibility regions','invalid delta discarded','redacted schema path and excerpt','snapshot recovery on same session','two forced socket disconnects','renewed one-shot credentials','HUD lease restored'],'invalidFrameDiagnostic':entry}
            (ROOT/'docs/evidence/bridge-recovery.json').write_text(json.dumps(evidence,indent=2)+'\n')
        finally:
            if (state/'shell.log').exists():pathlib.Path('/tmp/hyprune-recovery-shell.log').write_text((state/'shell.log').read_text())
            command('down')

if __name__=='__main__':
    live_check.acceptance=acceptance
    s.run(argparse.Namespace(live=True,m3b=False,m3a=False,m2=False,m1=False,integration=False,serve=False,record=False,visible=False))
