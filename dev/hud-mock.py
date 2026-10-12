"""SDK mock visual smoke; launched only by dev/run's validated nested lifetime."""
import json,os,subprocess,time,pathlib
pid=os.environ['HYPRUNE_SHELL_PID']
root=pathlib.Path(__file__).resolve().parent
shots=root/'.run/hud';shots.mkdir(exist_ok=True)
def ui(*args):return subprocess.check_output(['qs','ipc','--pid',pid,'call','preview',*map(str,args)],text=True).strip()
time.sleep(2)
ui('worldStyles','false')
for concept in ['Adventure','Instrument','Minimal']:
    ui('concept',concept);time.sleep(.6)
    audit=json.loads(ui('layoutAudit'));assert audit['labels'] and not audit['failures'],audit
    subprocess.run(['grim','-o','HYPRUNE-PREVIEW',str(shots/(concept+'.png'))],check=True)
ui('worldStyles','true');time.sleep(.7)
assert json.loads(ui('status'))['worldStyle']=='com.hyprune.observatory'
subprocess.run(['grim','-o','HYPRUNE-PREVIEW',str(shots/'world-style.png')],check=True)
ui('worldStyles','false');time.sleep(.7);assert json.loads(ui('status'))['worldStyle'] is None
ui('open');time.sleep(.6);ui('tabNamed', 'settings');ui('settingsSection',0);time.sleep(.3)
audit=json.loads(ui('layoutAudit'));assert not audit['failures'],audit
errors=(root/'.run/shell.log').read_text()
assert not any(x in errors for x in ['ERROR','ReferenceError','TypeError','Binding loop','Unable to assign','Error decoding','Cannot load font']),errors
print('PASS SDK mock concepts and Appearance',flush=True)
# Bounded presentation fixtures for the older SDK mock's protocol.
ui('close');time.sleep(.5)
preview={'placement':{'available':True,'active':True,'count':12,'index':3,'app':{'title':'An extremely long application title — localisation and workspace planning across several screens','appClass':'org.example.WindowWithAnExceptionallyLongClass','icon':'utilities-terminal'},'size':[1536,864],'ghost':True},'carry':{'active':False,'label':'','toggle':''},'content':None}
preview['hints']={'context':'','actions':[{'slot':'primary','label':'Place ahead','bindings':['LMB']},{'slot':'secondary','label':'On surface','bindings':['RMB']},{'slot':'alternate','label':'Pocket','bindings':['MMB']},{'slot':'cycle','label':'Cycle windows','bindings':['Wheel']}]}
for concept in ['Adventure','Instrument','Minimal']:
    ui('concept',concept);ui('manipulation',json.dumps(preview));time.sleep(.5)
    audit=json.loads(ui('layoutAudit'));assert not audit['failures'],audit
    result=json.loads(ui('interactionHud'));assert result['hudPlacementTile']['visible'] and result['hudPlacementTitle']['visible'],result
    subprocess.run(['grim','-o','HYPRUNE-PREVIEW',str(shots/(concept+'-placement-stub.png'))],check=True)
preview['placement']['active']=False;preview['carry']={'active':True,'label':'FACING YOU','toggle':'R · TOGGLE'}
preview['content']={'surfaceId':'stub','scale':1,'clientSize':[1920,1080],'serial':1,'reset':False}
ui('manipulation',json.dumps(preview));time.sleep(.2)
preview['content'].update(scale=1.25,clientSize=[1536,864],serial=2)
ui('manipulation',json.dumps(preview));time.sleep(.2)
result=json.loads(ui('interactionHud'));assert result['hudUnplacedBadge']['visible'] and '125%' in result['hudContentScale']['text'],result
subprocess.run(['grim','-o','HYPRUNE-PREVIEW',str(shots/'carry-scale-stub.png')],check=True)
preview['carry']['active']=False;preview['content']=None
ui('manipulation',json.dumps(preview));time.sleep(.2)
assert not json.loads(ui('interactionHud'))['hudContentScale']['visible']
preview['content']={'surfaceId':'stub','scale':1,'clientSize':[1920,1080],'serial':3,'reset':True}
ui('manipulation',json.dumps(preview));time.sleep(.2)
result=json.loads(ui('interactionHud'));assert result['hudContentScale']['visible'] and result['hudContentScale']['text'].startswith('RESET'),result
ui('manipulation','null')
errors=(root/'.run/shell.log').read_text()
assert not any(x in errors for x in ['ERROR','ReferenceError','TypeError','Binding loop','Unable to assign','Error decoding','Cannot load font']),errors
print('PASS placement presentation stubs, elision and carry/scale feedback',flush=True)
