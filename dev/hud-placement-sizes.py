"""Placement (tool 5) sizing captures across outputs and scales.
Launched only by dev/run's validated nested lifetime: dev/run placement-sizes
HYPRUNE_CAPTURE_LABEL names the output folder (e.g. before/after).
"""
import json,os,subprocess,time,pathlib
pid=os.environ['HYPRUNE_SHELL_PID'];signature=os.environ['HYPRLAND_INSTANCE_SIGNATURE']
root=pathlib.Path(__file__).resolve().parent
# dev/run already refused the parent session; confirm we still target its nested one.
assert json.loads((root/'.run/session.json').read_text())['HYPRLAND_INSTANCE_SIGNATURE']==signature
shots=root/'.run/placement-sizes'/os.environ.get('HYPRUNE_CAPTURE_LABEL','current');shots.mkdir(parents=True,exist_ok=True)
def ui(*args):return subprocess.check_output(['qs','ipc','--pid',pid,'call','preview',*map(str,args)],text=True).strip()
def resolution(w,h,scale):
    subprocess.run(['hyprctl','-i',signature,'eval',f'hl.monitor({{output="HYPRUNE-PREVIEW",mode="{w}x{h}@60",position="1280x0",scale={scale}}})'],check=True,stdout=subprocess.DEVNULL);time.sleep(1.2)
time.sleep(2)
ui('worldStyles','false')
placement={'available':True,'active':True,'count':12,'index':3,'app':{'title':'Pocket 1 — engineering notes, localisation review and extended workspace planning across several screens','appClass':'org.example.WindowWithAnExceptionallyLongApplicationClassName','icon':'utilities-terminal'},'size':[1536,864],'ghost':True}
fixtures={
    # Configured Alternate remapped to a chord, as a user keymap may do.
    'tool':{'context':'','actions':[{'slot':'primary','label':'Place ahead','bindings':['LMB']},{'slot':'secondary','label':'Place on surface','bindings':['RMB']},{'slot':'alternate','label':'Pocket window','bindings':['Ctrl+Alt+F8','MMB']},{'slot':'cycle','label':'Choose pocketed window','bindings':['Wheel']}]},
    'gestures':{'context':'GLOBAL GESTURES','actions':[{'slot':'carry','label':'Carry window','bindings':['Super+LMB']},{'slot':'orient','label':'Toggle facing / keep angle','bindings':['Super+R']},{'slot':'scale','label':'Scale window content','bindings':['Super+Shift+Wheel']},{'slot':'reset','label':'Reset content scale','bindings':['Super+Shift+MMB']},{'slot':'resize','label':'Resize window frame','bindings':['Super+RMB']},{'slot':'pocket','label':'Pocket window','bindings':['Super+MMB']}]},
}
report=[]
for w,h,scale in [(1920,1080,1),(2560,1440,1),(3840,2160,1),(1920,1080,2),(2560,1440,2),(3840,2160,2)]:
    resolution(w,h,scale)
    for concept in ['Adventure','Instrument','Minimal']:
        ui('concept',concept)
        for name,hints in fixtures.items():
            if name=='gestures' and concept!='Adventure':continue
            ui('manipulation',json.dumps({'placement':placement,'hints':hints,'carry':{'active':False,'label':'','toggle':''},'content':None}));time.sleep(.6)
            audit=json.loads(ui('layoutAudit'));hud=json.loads(ui('interactionHud'))
            view,deck=hud['view'],hud['hudToolDeck']
            entry={'output':f'{w}x{h}','scale':scale,'concept':concept,'hints':name,'view':view,'deck':{k:round(deck[k]) for k in ['x','y','width','height']},
                   'deckShare':[round(deck['width']/view['width'],3),round(deck['height']/view['height'],3)],
                   'titleElided':hud['hudPlacementTitle']['truncated'],'classElided':hud['hudPlacementClass']['truncated'],'failures':audit['failures']}
            report.append(entry);print(json.dumps(entry),flush=True)
            subprocess.run(['grim','-o','HYPRUNE-PREVIEW',str(shots/f'{concept.lower()}-{name}-{h}p-s{scale}.png')],check=True)
ui('manipulation','null')
(shots/'report.json').write_text(json.dumps(report,indent=1)+'\n')
errors=(root/'.run/shell.log').read_text()
assert not any(x in errors for x in ['ERROR','ReferenceError','TypeError','Binding loop','Unable to assign']),errors[-4000:]
print('DONE',shots,flush=True)
