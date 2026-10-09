"""Performance and photo holds on real 0.13/0.14, inside the parent nested flock."""
import json,math,subprocess,time
from pathlib import Path
import session as s
from m2 import keys,wait

def check(client,children,ui,status,state,shot,resolution,opened,closed):
    protocol=client.hello['protocol'];tag='ipc'+protocol.replace('.','')
    assert protocol==status()['protocol'] and protocol in ['0.13','0.14']
    assert 'camera.author' in client.hello['capabilities']
    assert 'camera.author' not in status()['capabilities']
    client.call('world.load',{'worldId':'org.hyprune.visibility'})
    wait(lambda:status()['world']=='org.hyprune.visibility' and not status()['warp'])
    wait(lambda:status()['hudVisible'])
    opened();ui('tab',7);ui('scrollPage',1);time.sleep(1)
    def focus(key):assert ui('graphicsFocus',key)=='true',key
    def choose(key,end):focus(key);keys('-k','space','-k',end,'-k','Return');time.sleep(.3)
    choose('outline','Home');wait(lambda:client.call('graphics.get',{})['config']['outline'] is None)
    choose('outline','End');wait(lambda:client.call('graphics.get',{})['config']['outline'] is True)
    wait(lambda:status().get('outline') and status()['outline'].get('style'))
    if protocol=='0.14':
        from hud_ink_check import persistent_controls
        persistent_controls(client,ui,status,focus,choose,opened,closed,shot)
    else:
        focus('outline_width');keys(*(['-k','Right']*12));wait(lambda:client.call('atmosphere.get',{})['profile']['outline']['widthPx']==4)
        print('PASS ink toggle and width via keyboard',flush=True)
        original=client.call('atmosphere.get',{})['profile']['outline']['colour']
        focus('outline_colour');keys('-M','ctrl','-k','a','-m','ctrl','#336699','-k','Return')
        wait(lambda:client.call('atmosphere.get',{})['profile']['outline']['colour']==[.2,.4,.6])
        focus('outline_reset');keys('-k','space');wait(lambda:client.call('atmosphere.get',{})['profile']['outline']['colour']==original)
        print('PASS ink colour and reset via keyboard',flush=True)
    ink=wait(lambda:client.call('graphics.get',{})['performance']['controls']['outline']['gpuMs'])
    choose('outline','Home');focus('outline');keys('-k','space','-k','Home','-k','Down','-k','Return')
    wait(lambda:client.call('graphics.get',{})['config']['outline'] is False)
    choose('outline','End')
    choose('visibility_culling','Home');wait(lambda:client.call('graphics.get',{})['config']['visibility_culling'] is False)
    choose('visibility_culling','End');wait(lambda:client.call('graphics.get',{})['config']['visibility_culling'] is True)
    for w,h,scale in [(1920,1080,1),(2560,1440,1),(3840,2160,1),(1920,1080,2)]:
        resolution(w,h,scale);ui('scrollPage',1);shot(f'performance-ink-{h}p-s{scale}-{tag}')
    resolution(1920,1080,1);closed()
    before=client.call('camera.get',{})
    lens={'position':[0,2,4],'orientation':[0,0,math.sqrt(.5),math.sqrt(.5)],'fov':15,'lensShift':[.25,-.15],'renderScale':.5}
    client.call('camera.photo',lens)
    wait(lambda:status()['camera'] and status()['camera']['held'] and not status()['hudVisible'])
    lease=status()['lease'];assert lease
    keys('-P','w','-s','200','-p','w')
    assert client.call('camera.get',{})['position']==lens['position']
    # shot() requires visible labels; photo holds intentionally have none.
    dest=Path.home()/f'hyprune-gallery/screenshots/hud-concepts/photo-held-{tag}.png'
    subprocess.run([str(s.HERE/'ctl.py'),'shot',str(dest)],check=True)
    client.call('camera.release',{})
    wait(lambda:status()['camera'] and not status()['camera']['held'] and status()['hudVisible'])
    assert status()['lease']==lease
    assert client.call('camera.get',{})['orientation']==before['orientation']
    shot('photo-released-'+tag)
    # A fresh author lifetime must also restore HUD automatically on disconnect.
    client.call('camera.photo',lens);wait(lambda:not status()['hudVisible']);client.close()
    wait(lambda:status()['camera'] and not status()['camera']['held'] and status()['hudVisible'])
    log=(s.STATE/'shell.log').read_text()
    assert not any(x in log for x in ['ERROR','ReferenceError','TypeError','Binding loop','Unable to assign','Invalid core frame','Presentation:']),log[-6000:]
    evidence={'protocol':protocol,'coreCommit':subprocess.check_output(['git','-C',str(s.ROOT),'rev-parse','HEAD'],text=True).strip(),'outlineGpuMs':ink,'controls':'Actual nested keyboard: preset/off/on, Fast/Smooth, width 4px, #336699, reset to world default, visibility off/on; saved graphics.json and world reload verified' if protocol=='0.14' else 'Actual nested keyboard: preset/off/on, width 4px, #336699, reset colour, visibility off/on','photo':'Roll 90°, FOV 15°, shifted lens and fixed scale: HUD hidden; release/disconnect restore same lease; no author grant in shell','world':'Visibility laboratory 0.5 accepted by shell catalog','quality':'Fast/Smooth live; persistent graphics width/colour and reset verified' if protocol=='0.14' else 'One native quality in core; no quality override in contract','validation':'All screenshot layout audits and QML/schema logs passed'}
    (Path(__file__).resolve().parents[1]/('docs/evidence/hud-authoring-'+protocol.replace('.','')+'.json')).write_text(json.dumps(evidence,indent=2)+'\n')
    print('PASS IPC',protocol,'Performance and authored-camera HUD',flush=True)


def check_compat(client,ui,status,shot,opened):
    assert client.hello['protocol']==status()['protocol']=='0.12'
    opened();ui('tab',7);ui('scrollPage',0);time.sleep(1)
    assert ui('graphicsFocus','quality')=='true'
    keys('-k','space','-k','Home','-k','Down','-k','Return')
    wait(lambda:client.call('graphics.get',{})['config']['quality']=='low')
    assert 'outline' not in client.call('graphics.get',{})['config']
    ui('scrollPage',1);shot('performance-ink-unavailable-ipc012')
    log=(s.STATE/'shell.log').read_text()
    assert not any(x in log for x in ['ERROR','ReferenceError','TypeError','Binding loop','Unable to assign','Invalid core frame','shell.action','Presentation:']),log[-5000:]
    print('PASS IPC 0.12 graphics compatibility; preset writes contain no new keys',flush=True)
