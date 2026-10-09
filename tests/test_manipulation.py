import json
from pathlib import Path
import subprocess
import unittest
SCRIPT=(Path(__file__).resolve().parents[1]/'qml/HudManipulation.js').read_text()
def run(expression):
    return json.loads(subprocess.check_output(['node','-e',SCRIPT+'\nconsole.log(JSON.stringify('+expression+'));'],text=True))
class Manipulation(unittest.TestCase):
    def test_missing_contract_never_invents_queue_or_orientation(self):
        for state in [None,{}, {'apps':[{'surfaceId':'a'}],'editor':{'tool':5}}]:
            result=run('presentation('+json.dumps(state)+')')
            self.assertFalse(result['placement']['available'])
            self.assertEqual(result['placement']['count'],0)
            self.assertFalse(result['carry']['active'])
    def test_queue_selection_joins_actual_app_and_surface(self):
        state={'editor':{'tool':5,'unplaced':{'count':2,'windows':[{'surfaceId':'a','title':'A'},{'surfaceId':'b','title':'B','appClass':'BClass'}],'selectedId':'b','preview':True},'carryFacing':False},'apps':[{'surfaceId':'b','title':'Old title','icon':'app-icon'}],'surfaces':[{'id':'b','logicalSize':[1536,864]}],'keymap':{'config':{'modes':{'world':{'carry.facing':['F7']}}}}}
        result=run('presentation('+json.dumps(state)+')')
        self.assertEqual(result['placement']['index'],1)
        self.assertEqual(result['placement']['app']['title'],'B')
        self.assertEqual(result['placement']['app']['icon'],'app-icon')
        self.assertEqual(result['placement']['size'],[1536,864])
        self.assertTrue(result['placement']['ghost'])
        self.assertEqual(result['carry'],{'active':True,'label':'KEEP ANGLE','toggle':'F7 · TOGGLE'})
    def test_explicit_unbound_never_replaced_with_default_key(self):
        self.assertEqual(run("binding({keymap:{config:{modes:{world:{'carry.facing':[]}}}}},'carry.facing','R')"),'Unbound')
    def test_first_edit_and_same_scale_reset_show_but_reconnect_does_not(self):
        base={'world':{'id':'a'},'editor':{'contentScale':None}}
        edited={'world':{'id':'a'},'editor':{'contentScale':{'surfaceId':'win','scale':1.25,'logicalSize':[1536,864],'sequence':1,'reset':False}}}
        call=lambda a,b:run('changedContent('+json.dumps(a)+','+json.dumps(b)+')')
        self.assertEqual(call(base,edited)['clientSize'],[1536,864])
        self.assertIsNone(call(None,edited))
        self.assertIsNone(call(edited,edited))
        reset=json.loads(json.dumps(edited));reset['editor']['contentScale'].update(sequence=2,reset=True)
        self.assertTrue(call(edited,reset)['reset'])
        reset['world']['id']='b'
        self.assertIsNone(call(edited,reset))

class Protocol015(unittest.TestCase):
    def test_editor_contract_does_not_widen_older_versions(self):
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bridge'))
        from protocol import V14_VALIDATOR,V15_VALIDATOR
        from client import Client
        self.assertIs(Client('/unused',lambda e:None,protocol='0.15').validator,V15_VALIDATOR)
        editor={'mode':'world','tool':5,'submode':'placement','selectedId':None,'selectedKind':'','paths':[],'objects':[],'locked':[],'debug':False,'unplaced':{'count':0,'windows':[],'selectedId':None,'preview':False},'carryFacing':None,'contentScale':None}
        slots=dict.fromkeys(['primary','secondary','alternate','cycle'])
        editor['toolSlots']=slots
        editor['toolDefinitions']=[{'slot':n,'name':'Tool '+str(n),'slots':slots} for n in range(1,6)]
        editor['toolInput']={'modifiers':0,'override':False,'gestures':[]}
        def check(validator,data):validator.evolve(schema={'$ref':validator.schema['$id']+'#/$defs/editor'}).validate(data)
        check(V15_VALIDATOR,editor)
        with self.assertRaises(Exception):check(V14_VALIDATOR,editor)
        editor['carryFacing']='yes'
        with self.assertRaises(Exception):check(V15_VALIDATOR,editor)
    def test_hud_events_accept_fifth_tool_only_in_new_protocol(self):
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bridge'))
        from protocol import V14_VALIDATOR,V15_VALIDATOR
        schema=V15_VALIDATOR.schema['$defs']
        # Validate the property contracts directly, independent of session IDs.
        for name in ['hud.pose.params','tool.changed.params']:
            definition=schema[name]
            key='tool' if name=='hud.pose.params' else 'slot'
            V15_VALIDATOR.evolve(schema=definition['properties'][key]).validate(5)
            with self.assertRaises(Exception):
                V14_VALIDATOR.evolve(schema=V14_VALIDATOR.schema['$defs'][name]['properties'][key]).validate(5)

class SlotHints(unittest.TestCase):
    def test_labels_and_remapped_keys_come_from_core(self):
        state={'editor':{'toolSlots':{'primary':{'action':'new.action','label':'Long translated primary label'},'secondary':None,'alternate':{'action':'custom','label':'Pocket window'},'cycle':None}},'keymap':{'config':{'modes':{'world':{'primary':['F8'],'alternate':[]}}}}}
        hints=run('slotHints('+json.dumps(state)+')')
        self.assertEqual(hints['actions'][0]['label'],'Long translated primary label')
        self.assertEqual(hints['actions'][0]['bindings'],['F8'])
        self.assertEqual(hints['actions'][1]['bindings'],[])
        self.assertEqual(len(hints['actions']),2)
        self.assertEqual(run('slotHints({})')['actions'],[])
    def test_super_replaces_tool_slots_with_core_gestures_and_chords(self):
        state={'editor':{'toolSlots':{'primary':{'action':'place','label':'Place ahead'}},'toolInput':{'modifiers':65,'override':True,'gestures':[{'action':'content.scale','label':'Translated content scale','bindings':['Super+Shift+Button8']}]}}}
        result=run('slotHints('+json.dumps(state)+')')
        self.assertEqual(result,{'context':'GLOBAL GESTURES','actions':[{'slot':'content.scale','label':'Translated content scale','bindings':['Super+Shift+Button8']}]})
        state['editor']['toolInput']['gestures']=[]
        self.assertEqual(run('slotHints('+json.dumps(state)+')')['actions'],[])
        state['editor']['toolInput']['override']=False
        self.assertEqual(run('slotHints('+json.dumps(state)+')')['actions'][0]['label'],'Place ahead')
    def test_carry_toggle_remains_visible_after_releasing_super(self):
        state={'editor':{'toolSlots':{},'toolInput':{'modifiers':0,'override':False,'gestures':[{'action':'carry.facing','label':'Keep angle','bindings':['F7']}]}}}
        self.assertEqual(run('slotHints('+json.dumps(state)+')')['actions'][0]['bindings'],['F7'])
