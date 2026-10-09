#!/usr/bin/env python3
"""Regenerate qml/components/brand/BrandMarks.js from the vendored logo masters.

The SVGs in qml/components/brand/ are byte-for-byte copies from the meta repo
(see BRAND.md). This copies each element's geometry verbatim into a JS table so
BrandMark.qml can draw it with QtQuick.Shapes in the theme colour.

    python3 dev/sync-brand.py          # rewrite BrandMarks.js
    python3 dev/sync-brand.py --check  # exit 1 if BrandMarks.js is stale
"""
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

BRAND = pathlib.Path(__file__).resolve().parent.parent / 'qml/components/brand'
OUT = BRAND / 'BrandMarks.js'
NS = '{http://www.w3.org/2000/svg}'
# Variant id -> vendored master. Thresholds live in variantFor() below.
MASTERS = {
    'h16': 'monogram-16-mono.svg',
    'h32': 'monogram-32-mono.svg',
    'optical': 'primary-optical-mono.svg',
    'primary': 'primary-mono.svg',
}

SELECTOR = '''
// Brand size rule (hyprune/brand/README.md), by rendered physical pixels:
// 16 px -> H 16-unit drawing, 17-47 px -> H 32-unit drawing,
// 48-95 px -> optical room, 96 px and up -> primary room.
// Below 16 px is under the H minimum; the 16-unit drawing is the closest.
function variantFor(physicalPx) {
    var px = Math.round(physicalPx);
    if (px <= 16) return 'h16';
    if (px < 48) return 'h32';
    if (px < 96) return 'optical';
    return 'primary';
}

function num(v) { return +v.toFixed(4); }

// Shapes has no ellipse/rect/circle element that fills in one PathSvg, so
// the master's attributes are expressed as equivalent SVG arc path data.
function fillPath(variant) {
    var m = masters[variant], d = [];
    m.ellipses.concat(m.circles.map(function(c) { return {cx:c.cx, cy:c.cy, rx:c.r, ry:c.r}; })).forEach(function(e) {
        d.push('M' + num(e.cx - e.rx) + ' ' + e.cy + 'A' + e.rx + ' ' + e.ry + ' 0 1 0 ' + num(e.cx + e.rx) + ' ' + e.cy
            + 'A' + e.rx + ' ' + e.ry + ' 0 1 0 ' + num(e.cx - e.rx) + ' ' + e.cy + 'Z');
    });
    m.rects.forEach(function(r) {
        var rx = Math.min(r.rx, r.width / 2), ry = Math.min(r.rx, r.height / 2), x2 = r.x + r.width, y2 = r.y + r.height;
        d.push('M' + num(r.x + rx) + ' ' + r.y + 'H' + num(x2 - rx) + 'A' + rx + ' ' + ry + ' 0 0 1 ' + x2 + ' ' + num(r.y + ry)
            + 'V' + num(y2 - ry) + 'A' + rx + ' ' + ry + ' 0 0 1 ' + num(x2 - rx) + ' ' + y2 + 'H' + num(r.x + rx)
            + 'A' + rx + ' ' + ry + ' 0 0 1 ' + r.x + ' ' + num(y2 - ry) + 'V' + num(r.y + ry)
            + 'A' + rx + ' ' + ry + ' 0 0 1 ' + num(r.x + rx) + ' ' + r.y + 'Z');
    });
    return d.join('');
}

// Strokes grouped by width (at most two per master); each master path keeps
// its own data and is only joined to others of the same width.
function strokeGroups(variant) {
    var groups = [];
    masters[variant].strokes.forEach(function(s) {
        var g = groups.find(function(x) { return x.width === s.width; });
        if (!g) groups.push(g = {width: s.width, paths: []});
        g.paths.push(s.d);
    });
    return groups.map(function(g) { return {width: g.width, d: g.paths.join('')}; });
}
'''


def number(value):
    f = float(value)
    return int(f) if f.is_integer() else f


def path_points(d):
    """Vertices of the absolute M/L/H/V/Z polylines used by the masters."""
    tokens = re.findall(r'[MLHVZ]|-?\d+(?:\.\d+)?', d)
    points, cmd, x, y, i = [], None, 0.0, 0.0, 0
    while i < len(tokens):
        if tokens[i] in 'MLHVZ':
            cmd = tokens[i]; i += 1
            if cmd == 'Z':
                continue
        if cmd == 'H':
            x = float(tokens[i]); i += 1
        elif cmd == 'V':
            y = float(tokens[i]); i += 1
        elif cmd in ('M', 'L'):
            x, y = float(tokens[i]), float(tokens[i + 1]); i += 2
        else:
            raise ValueError(f'unsupported path data {d!r}')
        points.append((x, y))
    return points


def ink_bounds(m):
    """Visible ink box [x0, y0, x1, y1] in source units (round caps/joins)."""
    boxes = []
    for s in m['strokes']:
        h = s['width'] / 2
        boxes += [(x - h, y - h, x + h, y + h) for x, y in path_points(s['d'])]
    boxes += [(e['cx'] - e['rx'], e['cy'] - e['ry'], e['cx'] + e['rx'], e['cy'] + e['ry']) for e in m['ellipses']]
    boxes += [(c['cx'] - c['r'], c['cy'] - c['r'], c['cx'] + c['r'], c['cy'] + c['r']) for c in m['circles']]
    boxes += [(r['x'], r['y'], r['x'] + r['width'], r['y'] + r['height']) for r in m['rects']]
    return [number(min(b[0] for b in boxes)), number(min(b[1] for b in boxes)),
            number(max(b[2] for b in boxes)), number(max(b[3] for b in boxes))]


def parse(name):
    root = ET.parse(BRAND / name).getroot()
    box = [number(v) for v in root.get('viewBox').split()]
    assert box[:2] == [0, 0] and box[2] == box[3], (name, box)
    out = {'file': name, 'viewBox': box[2], 'strokes': [], 'ellipses': [], 'rects': [], 'circles': []}
    for el in root.iter():
        tag = el.tag.removeprefix(NS)
        if tag in ('svg', 'title', 'desc'):
            continue
        if tag == 'path':
            assert el.get('fill') == 'none' and el.get('stroke') == 'currentColor', (name, el.attrib)
            assert el.get('stroke-linecap') == 'round' and el.get('stroke-linejoin') == 'round', (name, el.attrib)
            out['strokes'].append({'d': el.get('d'), 'width': number(el.get('stroke-width'))})
        elif tag == 'ellipse':
            assert el.get('fill') == 'currentColor', (name, el.attrib)
            out['ellipses'].append({k: number(el.get(k)) for k in ('cx', 'cy', 'rx', 'ry')})
        elif tag == 'rect':
            assert el.get('fill') == 'currentColor' and el.get('ry') is None, (name, el.attrib)
            out['rects'].append({k: number(el.get(k)) for k in ('x', 'y', 'width', 'height', 'rx')})
        elif tag == 'circle':
            assert el.get('fill') == 'currentColor', (name, el.attrib)
            out['circles'].append({k: number(el.get(k)) for k in ('cx', 'cy', 'r')})
        else:
            raise ValueError(f'{name}: unsupported element {tag}')
    assert len({s['width'] for s in out['strokes']}) <= 2, name
    out['ink'] = ink_bounds(out)
    return out


def render():
    masters = {key: parse(name) for key, name in MASTERS.items()}
    body = json.dumps(masters, indent=1)
    return ('// Generated by dev/sync-brand.py from the vendored masters in this folder.\n'
            '// Do not edit: geometry is copied verbatim; see BRAND.md for provenance.\n'
            f'var masters = {body};\n{SELECTOR}')


if __name__ == '__main__':
    text = render()
    if '--check' in sys.argv:
        if OUT.read_text() != text:
            sys.exit('BrandMarks.js is stale: run python3 dev/sync-brand.py')
        print('BrandMarks.js matches the vendored masters')
    else:
        OUT.write_text(text)
        print('wrote', OUT)
