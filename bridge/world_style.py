"""Declarative package skins. Never hand package-controlled URLs or SVGs to Qt."""
from pathlib import Path
import hashlib
import json
import os
import re
import xml.etree.ElementTree as ET
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parents[1]/'protocol/extensions'
STYLE=Draft202012Validator(json.loads((ROOT/'hud-style.schema.json').read_text()))
EXTENSION=Draft202012Validator(json.loads((ROOT/'hud-style-manifest.schema.json').read_text()))
TAGS={'svg','g','path','rect','circle','ellipse','line','polyline','polygon','defs','linearGradient','radialGradient','stop','clipPath'}
ATTRS={'id','viewBox','width','height','x','y','x1','y1','x2','y2','cx','cy','r','rx','ry','d','points','transform','fill','stroke','stroke-width','stroke-linecap','stroke-linejoin','fill-rule','clip-rule','opacity','fill-opacity','stroke-opacity','offset','stop-color','stop-opacity','gradientUnits','gradientTransform','clip-path'}

def read_asset(root, relative, limit):
    """Walk only regular files, rejecting symlinks at every path component."""
    if not re.fullmatch(r'hud/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\.[A-Za-z0-9]+',relative): raise ValueError('Invalid package asset path')
    fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        parts=relative.split('/')
        for part in parts[:-1]:
            next_fd=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=next_fd
        asset=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
        with os.fdopen(asset,'rb') as stream:
            import stat
            info=os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size>limit: raise ValueError('Asset must be a bounded regular file')
            data=stream.read(limit+1)
            if len(data)>limit: raise ValueError('Asset too large')
            return data
    finally:os.close(fd)

def svg(data):
    if len(data)>65536 or re.search(br'<!|<\?',data): raise ValueError('SVG declarations/entities are forbidden')
    node=ET.fromstring(data)
    ids=set();refs=[];count=0
    for element in node.iter():
        count+=1
        tag=element.tag.removeprefix('{http://www.w3.org/2000/svg}')
        if tag not in TAGS or count>256: raise ValueError('Unsupported SVG element/complexity')
        if element.text and element.text.strip(): raise ValueError('SVG text is not an icon path')
        for key,value in element.attrib.items():
            if key not in ATTRS or len(value)>16384: raise ValueError('Unsupported SVG attribute')
            if key=='id':
                if not re.fullmatch('[A-Za-z][A-Za-z0-9_-]{0,63}',value) or value in ids: raise ValueError('Invalid SVG ID')
                ids.add(value)
            elif key in ['fill','stroke','stop-color','clip-path']:
                if re.fullmatch(r'url\(#[A-Za-z][A-Za-z0-9_-]{0,63}\)',value):refs.append(value[5:-1])
                elif not re.fullmatch(r'(?:#[0-9A-Fa-f]{3,8}|none|currentColor|black|white|transparent)',value):raise ValueError('Unsupported SVG paint/reference')
            elif re.search(r'url|href|javascript|https?:|file:|data:|[<>;&]|nan|infinity',value,re.I): raise ValueError('Unsafe SVG value')
    if node.tag.removeprefix('{http://www.w3.org/2000/svg}')!='svg' or any(ref not in ids for ref in refs):raise ValueError('Invalid SVG root/reference')
    return ET.tostring(node,encoding='utf-8')

def luminance(color):
    c=[int(color[i:i+2],16)/255 for i in (1,3,5)]
    c=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c]
    return sum(a*b for a,b in zip(c,[.2126,.7152,.0722]))
def contrast(a,b):
    x,y=sorted([luminance(a),luminance(b)]);return (y+.05)/(x+.05)

def load(package, cache):
    package=Path(package);manifest=json.loads(package.read_text())
    extension=manifest.get('extensions',{}).get('com.hyprune.hud-style')
    if extension is None:return {}
    EXTENSION.validate(extension)
    value=json.loads(read_asset(package.parent,extension['theme'],32768));STYLE.validate(value)
    colors=value.setdefault('colors',{})
    # A dark opaque outline is the final contrast boundary on any world surface.
    outline=colors.get('outline','#081118')
    if luminance(outline)>.04:outline='#081118'
    colors['outline']=outline
    for key,default,minimum in [('foreground','#f6f5ea',4.5),('muted','#c5d2d2',4.5),('accent','#dfbd68',3)]:
        if key in colors and contrast(colors[key],outline)<minimum:colors[key]=default
    if 'tile' in colors and contrast(colors['tile'],'#f6f5ea')<4.5:colors['tile']='#175663'
    if 'scrim' in colors and luminance(colors['scrim'])>.08:colors['scrim']='#101820'
    cache=Path(cache);cache.mkdir(mode=0o700,parents=True,exist_ok=True)
    def saved(data,suffix):
        dest=cache/(hashlib.sha256(data).hexdigest()+suffix)
        if not dest.exists():
            with open(dest,'xb') as out:out.write(data)
            dest.chmod(0o400)
        return dest.as_uri()
    for key,path in value.get('icons',{}).items():value['icons'][key]=saved(svg(read_asset(package.parent,path,65536)),'.svg')
    if 'font' in value:
        data=read_asset(package.parent,value['font'],4*1024*1024)
        if data[:4] not in [b'OTTO',b'\x00\x01\x00\x00']:raise ValueError('Unsupported font container')
        value['font']=saved(data,'.otf' if data[:4]==b'OTTO' else '.ttf')
    value['worldId']=manifest['id']
    return value
