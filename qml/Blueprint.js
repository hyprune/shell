// IPC 0.20 blueprint map levels (com.hyprune.blueprint 0.1): theme colours per SVG
// `class`, level auto-pick and map zoom. Pure helpers: tested with node in
// tests/test_ipc20.py.

var ROLES = ['grid', 'floor', 'wall', 'stair', 'opening', 'screen', 'mount', 'area', 'label', 'route',
             'waypoint', 'void', 'outline'];
var EYE_HEIGHT = 1.7;    // state.movement.position is the eye; levels are feet-height bands
var ZOOM_RANGE = [1, 8];
var TAGS = /<(svg|g|rect|path|circle|ellipse|line|polyline|polygon|text|tspan)\b([^<>]*?)(\/?)>/g;
// Defence in depth: core validates level SVGs, but nothing that could reach outside the
// data URL is ever passed on (references, declarations, styles, scripts, embedded media).
var REFUSED = /<!|<\?|href|url\s*\(|<\s*(script|style|image|foreignobject|use)\b|@import|javascript:/i;

function hex(value) {
    var s = String(value);
    if (/^#[0-9a-fA-F]{8}$/.test(s)) s = '#' + s.slice(3);  // QML colours print #aarrggbb
    return /^#[0-9a-fA-F]{6}$/.test(s) ? s.toLowerCase() : '#888888';
}

// Theme roles from shell tokens (#rrggbb strings or QML colours). Each role lists the
// presentation attributes given to class-carrying elements that don't set them.
function palette(t) {
    var text = hex(t.text), muted = hex(t.muted), accent = hex(t.accent), gold = hex(t.gold), line = hex(t.line),
        ink = hex(t.ink), positive = hex(t.positive), warning = hex(t.warning);
    return {
        grid: {fill: 'none', stroke: line, 'stroke-opacity': '0.45'},
        outline: {fill: 'none', stroke: line},
        floor: {fill: accent, 'fill-opacity': '0.10', stroke: 'none'},
        wall: {fill: text, stroke: text},
        stair: {fill: accent, 'fill-opacity': '0.16', stroke: accent, 'stroke-opacity': '0.7'},
        opening: {fill: ink, stroke: gold},
        screen: {fill: gold, stroke: gold},
        mount: {fill: accent, stroke: accent},
        area: {fill: 'none', stroke: muted, 'stroke-opacity': '0.7'},
        label: {fill: muted, stroke: 'none'},
        route: {fill: 'none', stroke: positive, 'stroke-opacity': '0.7'},
        waypoint: {fill: gold, stroke: ink},
        void: {fill: warning, 'fill-opacity': '0.12', stroke: warning}
    };
}

function attribute(attrs, name) {
    var m = new RegExp('(?:^|\\s)' + name + '\\s*=\\s*("([^"]*)"|\'([^\']*)\')').exec(attrs);
    return m ? (m[2] !== undefined ? m[2] : m[3]) : null;
}

// The level SVG with theme colours injected, or '' when it can't be shown safely.
// Elements with a known class get each missing role attribute; their own fill/stroke win.
// Elements without a class (or with an unknown one) keep their own colours.
function themed(svg, roles) {
    if (typeof svg !== 'string' || !svg.length || svg.length > 65536 || REFUSED.test(svg)) return '';
    if (!/^\s*<svg\b/.test(svg)) return '';
    return svg.replace(TAGS, function(all, tag, attrs, close) {
        var role = attribute(attrs, 'class');
        var style = role !== null ? roles[role.trim()] : null;
        if (!style) return all;
        var extra = '';
        Object.keys(style).forEach(function(name) {
            if (attribute(attrs, name) === null) extra += ' ' + name + '="' + style[name] + '"';
        });
        return '<' + tag + attrs.replace(/\s+$/, '') + extra + (close ? ' />' : '>');
    });
}

function dataUrl(svg, roles) {
    var out = themed(svg, roles);
    return out ? 'data:image/svg+xml,' + encodeURIComponent(out) : '';
}

// Index of the level holding the player's feet (eye height above them). Between or
// beyond the bands: the nearest one. -1 without levels.
function levelFor(levels, eyeY) {
    if (!levels || !levels.length || typeof eyeY !== 'number' || !isFinite(eyeY)) return levels && levels.length ? 0 : -1;
    var feet = eyeY - EYE_HEIGHT, best = 0, distance = Infinity;
    for (var i = 0; i < levels.length; i++) {
        var l = levels[i];
        if (feet >= l.minY && feet < l.maxY) return i;
        var d = feet < l.minY ? l.minY - feet : feet - l.maxY;
        if (d < distance) { distance = d; best = i; }
    }
    return best;
}

// The level shown: the user's pick while it still exists, otherwise the automatic one.
function shownLevel(levels, pickedId, eyeY) {
    if (!levels || !levels.length) return -1;
    if (pickedId) for (var i = 0; i < levels.length; i++) if (levels[i].id === pickedId) return i;
    return levelFor(levels, eyeY);
}

// Content key for the map data (overview + level hashes): unchanged keeps cached images.
function mapKey(map) {
    if (!map) return '';
    return map.sha256 + (map.levels ? '|' + map.levels.map(function(l) { return l.id + ':' + l.sha256; }).join(',') : '');
}

function clampZoom(zoom) {
    return Math.max(ZOOM_RANGE[0], Math.min(ZOOM_RANGE[1], isFinite(zoom) ? zoom : 1));
}

// Pan offset (pixels, map centre relative to the view centre) kept so the map can't leave the view.
function clampPan(pan, zoom, width, height) {
    var x = Math.max(0, width * (zoom - 1) / 2), y = Math.max(0, height * (zoom - 1) / 2);
    return [Math.max(-x, Math.min(x, pan[0] || 0)), Math.max(-y, Math.min(y, pan[1] || 0))];
}

// Zoom about a view point (pixels from the view centre) so that point stays put.
function zoomAt(pan, zoom, next, point) {
    var z = clampZoom(next), k = z / zoom;
    return {zoom: z, pan: [point[0] - (point[0] - pan[0]) * k, point[1] - (point[1] - pan[1]) * k]};
}

// Width / height of an SVG's viewBox (all levels share the overview's frame).
function viewBoxRatio(svg, fallback) {
    var m = /<svg\b[^>]*?\sviewBox\s*=\s*["']\s*([-\d.eE+]+)[\s,]+([-\d.eE+]+)[\s,]+([-\d.eE+]+)[\s,]+([-\d.eE+]+)/.exec(String(svg || ''));
    var w = m ? Number(m[3]) : NaN, h = m ? Number(m[4]) : NaN;
    if (!m) {
        var tag = /<svg\b[^>]*>/.exec(String(svg || ''));
        w = tag ? parseFloat(attribute(tag[0].slice(4, -1), 'width')) : NaN;
        h = tag ? parseFloat(attribute(tag[0].slice(4, -1), 'height')) : NaN;
    }
    return w > 0 && h > 0 && isFinite(w / h) ? w / h : (fallback || 0.9);
}

// A round scale bar length (1/2/5 x 10^n m) about 120 px long at this many pixels per metre.
function scaleBar(pxPerMeter) {
    if (!(pxPerMeter > 0) || !isFinite(pxPerMeter)) return {meters: 10, pixels: 0};
    var target = 120 / pxPerMeter, base = Math.pow(10, Math.floor(Math.log(target) / Math.LN10)), best = base;
    [1, 2, 5, 10].forEach(function(k) { if (Math.abs(k * base - target) < Math.abs(best - target)) best = k * base; });
    return {meters: best, pixels: best * pxPerMeter};
}

function meters(value) {
    return value >= 1 ? String(Math.round(value)) + ' m' : String(Math.round(value * 100)) + ' cm';
}
