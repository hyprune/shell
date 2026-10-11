"""Persistent ink controls via real nested menu input; parent owns the flock."""
import json,time
import session as s
from m2 import keys,wait

def persistent_controls(client,ui,status,focus,choose,opened,closed,shot):
    def graphics():return client.call('graphics.get',{})
    def ink():return client.call('atmosphere.get',{})['profile']['outline']
    authored=ink()
    def reset():
        focus('outline_defaults');keys('-k','space')
        wait(lambda:all(graphics()['config'][k] is None for k in ['outline','outline_quality','outline_width_px','outline_colour']))
        wait(lambda:ink()==authored)
    choose('outline_quality','Home');wait(lambda:graphics()['config']['outline_quality'] is None)
    focus('outline_quality');keys('-k','space','-k','Home','-k','Down','-k','Return')
    wait(lambda:graphics()['effective']['outline_quality']=='fast')
    wait(lambda:ui('graphicsFocus','outline_width')=='false')
    assert graphics()['effective']['outline_width_px']==1
    shot('performance-ink-fast-ipc014')
    choose('outline_quality','End');wait(lambda:graphics()['config']['outline_quality']=='smooth')
    wait(lambda:ui('graphicsFocus','outline_width')=='true')
    keys(*(['-k','Right']*12))
    wait(lambda:graphics()['config']['outline_width_px']==4 and ink()['widthPx']==4)
    focus('outline_colour');keys('-M','ctrl','-k','a','-m','ctrl','#336699','-k','Return')
    wait(lambda:graphics()['config']['outline_colour']==[.2,.4,.6] and ink()['colour']==[.2,.4,.6])
    saved=json.loads((s.STATE/'graphics.json').read_text())
    assert all(saved[k]==v for k,v in {'outline_quality':'smooth','outline_width_px':4,'outline_colour':[.2,.4,.6]}.items()),saved
    shot('performance-ink-overrides-ipc014')
    print('PASS Fast/Smooth, disabled Fast width, persistent width/colour via keyboard',flush=True)
    # The real world loader must not bake user values into package reset defaults.
    closed()
    for world in ['com.hyprune.lumen-reach','org.hyprune.visibility']:
        client.call('world.load',{'worldId':world})
        wait(lambda:status()['world']==world and not status()['warp'])
    wait(lambda:ink()['widthPx']==4 and ink()['colour']==[.2,.4,.6])
    opened();ui('tab',8);ui('scrollPage',1);time.sleep(1)
    reset()
    saved=json.loads((s.STATE/'graphics.json').read_text())
    assert all(saved[k] is None for k in ['outline','outline_quality','outline_width_px','outline_colour'])
    # Reset does not touch independent authored visibility policy.
    assert graphics()['config']['visibility_culling'] is True
    shot('performance-ink-world-default-ipc014')
    # Global preset selection also clears the newly introduced overrides.
    choose('outline_quality','End')
    wait(lambda:graphics()['config']['outline_quality']=='smooth')
    ui('scrollPage',0);choose('quality','Home')
    wait(lambda:all(graphics()['config'][k] is None for k in ['outline_quality','outline_width_px','outline_colour']))
    ui('scrollPage',1)
    print('PASS graphics.json persistence, reload precedence, reset to immutable world defaults and preset reset',flush=True)
