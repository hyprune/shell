#!/usr/bin/env python3
"""Apply core's explicit graphics contract handoff to a separate exact 0.7 pin."""
import hashlib,json,pathlib,sys
root=pathlib.Path(__file__).resolve().parent.parent
source=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else root.parent/'core/docs/graphics-ipc-amendment.json'
amendment=json.loads(source.read_text());assert amendment['protocol']=='0.7' and amendment['baseProtocol']=='0.6'
schema=json.loads((root/'protocol/v0.6/ipc.schema.json').read_text())
schema['$id']=schema['$id'].replace('v0.6','v0.7');schema['title']='Hyprune IPC 0.7'
def refs(value):
    if isinstance(value,dict):
        if '$ref' in value and value['$ref'].startswith('common.schema.json'):
            value['$ref']='https://hyprune.com/schema/v0.6/'+value['$ref']
        for child in value.values():refs(child)
    elif isinstance(value,list):
        for child in value:refs(child)
refs(schema)
d=schema['$defs'];d.update(amendment['$defs'])
d['session.hello.result']['properties']['protocol']={'const':'0.7'}
d['session.hello.result']['properties']['methods']['items']['enum']+=list(amendment['methods'])
for method in amendment['methods']:
    d['request']['oneOf'].append({'$ref':f'#/$defs/{method}.request'})
    d['response']['anyOf'].append({'$ref':f'#/$defs/{method}.response'})
out=root/'protocol/v0.7';out.mkdir(exist_ok=True)
(out/'ipc.schema.json').write_text(json.dumps(schema,indent=2)+'\n')
(out/'SOURCE.json').write_text(json.dumps({'protocol':'0.7','base':json.loads((root/'protocol/v0.6/SOURCE.json').read_text()),'amendment':'core/docs/graphics-ipc-amendment.json','amendmentSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'notes':'Applied exact core handoff. Canonical schema repository has not published 0.7 yet; existing 0.1–0.6 pins remain unchanged.'},indent=2)+'\n')
