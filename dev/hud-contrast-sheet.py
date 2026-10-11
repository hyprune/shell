#!/usr/bin/env python3
"""Build the v4/v5 status crop comparison from locked nested capture evidence."""
from pathlib import Path
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent)); import devenv  # noqa: E402
from PIL import Image, ImageDraw, ImageFont, ImageOps
import json
import os
import re
import subprocess

P=devenv.gallery_dir()/'screenshots/hud-concepts'
font=subprocess.check_output(['fc-match','-f','%{file}','DejaVu Sans'],text=True)
def f(n):return ImageFont.truetype(font,n)
def crops(path):
    im=Image.open(path).convert('RGB');w,h=im.size
    scale=int(re.search(r'-s(\d)-',path.name)[1])
    factor=scale*max(1,min(w/scale/1920,h/scale/1080,1.5))
    rw,rh=w/factor,h/factor;compact=rw<1200 or rh<700
    i=26 if compact else 56;r=126 if compact else 178
    boxes=[(i-14,i+r,i+r+20,i+r+40),(rw-i-(230 if compact else 310)-14,i-14,rw-i+20,i+78)]
    return [im.crop(tuple(round(v*factor) for v in b)) for b in boxes]

for path in P.glob('adventure-*-*p-s*-v5.png'):
    if not re.search(r'(sun-court|rime-vault)-\d+p-s[12]-v5.png$',path.name):continue
    for suffix,im in zip(['radar-caption','status'],crops(path)):
        im.save(path.with_name(path.stem.replace('-v5','-'+suffix+'-v5')+'.png'))
measurements={r['capture']:r for r in json.loads((P/'contrast-v5-measurements.json').read_text())}
for scale in [1,2]:
    rows=[(home,res) for res in [1080,1440,2160] for home in ['sun-court','rime-vault']]
    sheet=Image.new('RGB',(1950,155+235*len(rows)),(10,18,28));d=ImageDraw.Draw(sheet)
    d.text((30,18),'HUD text / solid fill + feathered local contrast protection',font=f(28),fill='#edf3f5')
    d.text((30,65),'v4 / BEFORE',font=f(20),fill='#dfbd68')
    d.text((770,65),'v5 / AFTER',font=f(20),fill='#dfbd68')
    d.text((1510,65),'MEASURED CONTRAST',font=f(20),fill='#dfbd68')
    d.text((1510,92),'Glyph core / background · target 4.5:1',font=f(16),fill='#b9c8ce')
    for row,(home,res) in enumerate(rows):
        y=130+row*235
        d.text((30,y),f'{home.replace("-"," ").title()} / {res}p / scale {scale}',font=f(17),fill='#b9c8ce')
        for col,version in enumerate(['v4','v5']):
            caption,status=crops(P/f'adventure-{home}-{res}p-s{scale}-{version}.png');x=30+740*col
            status=ImageOps.contain(status,(660,130),Image.Resampling.LANCZOS)
            caption=ImageOps.contain(caption,(660,55),Image.Resampling.LANCZOS)
            sheet.paste(status,(x,y+32));sheet.paste(caption,(x,y+172))
        sample=measurements[f'adventure-{home}-{res}p-s{scale}-v5']
        white=measurements[f'adventure-white-{res}p-s{scale}-v5']
        for n,(label,v) in enumerate(zip(['Radar caption','Navigation','Input status'],sample['regions'])):
            d.text((1510,y+35+n*30),f'{label}: {v["rasterCoreMin"]:.2f}:1',font=f(19),fill='#edf3f5')
        nominal=min(v['nominalMin'] for v in sample['regions'])
        worst=min(min(v['nominalMin'],v['rasterCoreMin']) for v in white['regions'])
        d.text((1510,y+137),f'Nominal minimum: {nominal:.2f}:1',font=f(17),fill='#b9c8ce')
        d.text((1510,y+164),f'Pure-white minimum: {worst:.2f}:1',font=f(17),fill='#96d5b3')
        d.text((1510,y+193),'Minimum over >=80% coverage pixels',font=f(15),fill='#b9c8ce')
    dest=P/('hud-status-crops-v5.png' if scale==1 else 'hud-status-crops-s2-v5.png')
    sheet.save(dest);print(dest)
