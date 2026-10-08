"""SDK mock visual smoke; launched only by dev/run's validated nested lifetime."""
import json,os,subprocess,time,pathlib
pid=os.environ['HYPRUNE_SHELL_PID']
root=pathlib.Path(__file__).resolve().parent
shots=root/'.run/hud';shots.mkdir(exist_ok=True)
def ui(*args):return subprocess.check_output(['qs','ipc','--pid',pid,'call','preview',*map(str,args)],text=True).strip()
time.sleep(2)
ui('worldStyles','false')
for concept in ['Vanguard','Instrument','Minimal']:
    ui('concept',concept);time.sleep(.6)
    audit=json.loads(ui('layoutAudit'));assert audit['labels'] and not audit['failures'],audit
    subprocess.run(['grim','-o','HYPRUNE-PREVIEW',str(shots/(concept+'.png'))],check=True)
ui('worldStyles','true');time.sleep(.7)
assert json.loads(ui('status'))['worldStyle']=='com.hyprune.observatory'
subprocess.run(['grim','-o','HYPRUNE-PREVIEW',str(shots/'world-style.png')],check=True)
ui('worldStyles','false');time.sleep(.7);assert json.loads(ui('status'))['worldStyle'] is None
ui('open');time.sleep(.6);ui('tab',6);ui('settingsSection',0);time.sleep(.3)
audit=json.loads(ui('layoutAudit'));assert not audit['failures'],audit
errors=(root/'.run/shell.log').read_text()
assert not any(x in errors for x in ['ERROR','ReferenceError','TypeError','Binding loop','Unable to assign','Error decoding','Cannot load font']),errors
print('PASS SDK mock concepts and Appearance',flush=True)
