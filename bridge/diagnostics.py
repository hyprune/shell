"""Bounded diagnostics: schema paths and shapes, never package/app/auth values."""
def properties(schema):
    names=set()
    def visit(node):
        if isinstance(node,dict):
            names.update(node.get('properties',{}))
            for value in node.values():visit(value)
        elif isinstance(node,list):
            for value in node:visit(value)
    visit(schema)
    return names

def diagnostic(validator, value, error, method=None):
    names=properties(validator.schema)
    def leaf(e):
        return max((leaf(c) for c in e.context),key=lambda c:len(c.absolute_path)) if getattr(e,'context',None) else e
    error=leaf(error)
    path=list(getattr(error,'absolute_path',[]))
    safe_path=[p if isinstance(p,int) or p in names else '<field>' for p in path]
    excerpt=value
    for part in path[:-1]:
        try:excerpt=excerpt[part]
        except (KeyError,IndexError,TypeError):break
    def shape(v,depth=0):
        if isinstance(v,str):return '<string:'+str(len(v))+'>'
        if v is None:return None
        if isinstance(v,bool):return '<boolean>'
        if isinstance(v,(float,int)):return '<number>'
        if depth>=3:return '<'+type(v).__name__+'>'
        if isinstance(v,list):return [shape(x,depth+1) for x in v[:3]]+(['<more>'] if len(v)>3 else [])
        if isinstance(v,dict):return {k if k in names else '<field-'+str(i)+'>':shape(x,depth+1) for i,(k,x) in enumerate(list(v.items())[:8])}
        return '<value>'
    return {'type':'protocol.invalid','method':method or '<unknown>',
            'path':'/'+ '/'.join(str(p).replace('~','~0').replace('/','~1') for p in safe_path),
            'rule':getattr(error,'validator',None) or 'json','excerpt':shape(excerpt)}
