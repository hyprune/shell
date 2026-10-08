"""Pixel evidence for small HUD labels; capture only via the locked nested harness.

Use sRGB relative luminance, comparing rendered text with the same block's
text-free background. A white-on-black render identifies >=80% glyph coverage;
anti-aliased edge pixels are excluded, not mistaken for the foreground colour.
The nominal-colour test additionally checks the brightest background beneath
every glyph pixel with >2% coverage. Neither result is rounded before the 4.5 gate.
"""
import json
import math
from pathlib import Path
import tempfile
import time

import numpy as np
from PIL import Image


def luminance(rgb):
    c = np.asarray(rgb, dtype=float) / 255
    c = np.where(c <= .04045, c / 12.92, ((c + .055) / 1.055) ** 2.4)
    return c @ np.array([.2126, .7152, .0722])


def measure_pixels(normal, background, mask, foreground):
    coverage = np.asarray(mask, dtype=float).mean(axis=-1) / 255
    core = coverage >= .8
    ink = coverage > .02
    if not np.any(core):
        raise ValueError('No high-coverage glyph pixels in the capture')
    bg = luminance(background)
    actual = luminance(normal)
    nominal = float((luminance(foreground) + .05) / (np.max(bg[ink]) + .05))
    raster = float(np.min((actual[core] + .05) / (bg[core] + .05)))
    return dict(nominalMin=nominal, rasterCoreMin=raster, corePixels=int(core.sum()),
                backgroundMax=float(np.max(bg[ink])), passContrast=nominal >= 4.5 and raster >= 4.5)


def capture(ui, raw_shot, shot_path, white=False):
    """Normal image already captured; keep only tight diagnostic crops in gallery."""
    shot_path = Path(shot_path)
    name = shot_path.stem
    diagnostic = shot_path.parent / 'contrast-v5'
    diagnostic.mkdir(exist_ok=True)
    regions = json.loads(ui('contrastProbe', 'normal'))
    try:
        with tempfile.TemporaryDirectory(prefix='hyprune-contrast-') as tmp:
            bg_path, mask_path = Path(tmp)/'background.png', Path(tmp)/'mask.png'
            ui('contrastProbe', 'white-background' if white else 'background')
            time.sleep(.3); raw_shot(bg_path)
            ui('contrastProbe', 'mask')
            time.sleep(.3); raw_shot(mask_path)
            images = [Image.open(p).convert('RGB') for p in [shot_path, bg_path, mask_path]]
            (diagnostic/f'{name}-regions.json').write_text(json.dumps(regions,indent=2))
            result = []
            for r in regions:
                box = (max(0,math.floor(r['x'])), max(0,math.floor(r['y'])),
                       min(images[0].width,math.ceil(r['x']+r['width'])),
                       min(images[0].height,math.ceil(r['y']+r['height'])))
                crops = [im.crop(box) for im in images]
                for suffix,im in zip(['text','background','mask'],crops):
                    im.save(diagnostic/f'{name}-{r["name"]}-{suffix}.png')
                values = measure_pixels(*(np.asarray(im) for im in crops), r['foreground'])
                result.append(dict(region=r['name'],text=r['text'],box=box,**values))
            return dict(capture=name,whiteStress=white,regions=result)
    finally:
        ui('contrastProbe', 'normal')


def verify(results):
    failures = [(r['capture'],v) for r in results for v in r['regions']
                if not v['passContrast'] or v['corePixels'] < 10]
    assert not failures, json.dumps(failures, indent=2)
