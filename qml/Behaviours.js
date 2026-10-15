// Director > Objects > Placed > Behaviours (RFC-0014 amendment: data-driven behaviours, IPC 0.31):
// a placed object's display follows a value from a data source. Each behaviour reads one
// value (by default key `value` of this object's own source, com.hyprune.sources.<id>, 0..100,
// as a gauge does) and moves one property between A and B: grow or shrink about a face, move,
// turn, colour, glow, show or hide, or the texture's offset or scroll. Display only: collision
// stays where the object stands. Core keeps them in the placement (objects.configure patch
// behaviours) and reports each with its live value (instance.behaviours). A and B of a move,
// turn or size can be captured from the gizmo: the editor remembers the rest pose, you move the
// object, Capture A or B takes the difference, and Save puts it back at rest.
// Pure helpers, tested with node in tests/test_behaviours.py.

var CLIENT = 'com.hyprune.sources';
var PROPERTIES = [
    {id: 'scale', label: 'Grow', hint: 'Size per axis about a face: a bar that grows upward', base: 'grow', defaults: {from: [1, 0.05, 1], to: [1, 1, 1], anchor: 'bottom'}},
    {id: 'move', label: 'Move', hint: 'Metres along the object\'s own axes', base: 'move', defaults: {from: [0, 0, 0], to: [0, 1, 0]}},
    {id: 'rotate', label: 'Turn', hint: 'Degrees about the object\'s own axes, around a face or its centre', base: 'turn', defaults: {from: [0, 0, 0], to: [0, 90, 0], anchor: 'centre'}},
    {id: 'colour', label: 'Colour', hint: 'From one colour to another (tints a texture)', base: 'colour', defaults: {from: '#2471a3', to: '#b03a2e'}},
    {id: 'glow', label: 'Glow', hint: 'Glow strength (0 to 16) in a colour', base: 'glow', defaults: {from: 0, to: 6, colour: '#30e0ff'}},
    {id: 'visible', label: 'Show / hide', hint: 'Shown while the value is above and below the limits you give', base: 'show', defaults: {above: 50}},
    {id: 'texture', label: 'Texture', hint: 'Slide or scroll the texture (repeats, or repeats per second)', base: 'texture', defaults: {mode: 'scroll', from: [0, 0], to: [1, 0]}}];
var ANCHORS = ['bottom', 'top', 'left', 'right', 'front', 'back', 'centre'];
var EASINGS = ['linear', 'ease-in', 'ease-out', 'ease-in-out', 'step'];
var AXES = ['x', 'y', 'z'];

function property(id) { return PROPERTIES.filter(function (p) { return p.id === id; })[0] || null; }
function hex(text) {
    var t = String(text || '').trim().toLowerCase(), m = /^#?([0-9a-f])([0-9a-f])([0-9a-f])$/.exec(t);
    if (m) return '#' + m[1] + m[1] + m[2] + m[2] + m[3] + m[3];
    if (t && t[0] !== '#') t = '#' + t;
    return /^#[0-9a-f]{6}$/.test(t) ? t : '';
}
function listOf(instance) { return (instance && instance.behaviours || []).map(function (s) { return s.behaviour; }); }
function stateOf(instance, key) { return (instance && instance.behaviours || []).filter(function (s) { return s.key === key; })[0] || null; }
function freeKey(prop, list) {
    var base = (property(prop) || {base: prop}).base, keys = (list || []).map(function (b) { return b.key; });
    if (keys.indexOf(base) < 0) return base;
    for (var n = 2; n < 100; n++) if (keys.indexOf(base + '-' + n) < 0) return base + '-' + n;
    return base + '-' + Date.now();
}
function newBehaviour(prop, list) {
    var p = property(prop);
    if (!p) return null;
    return Object.assign({key: freeKey(prop, list), property: prop}, JSON.parse(JSON.stringify(p.defaults)));
}
// The editor's form: every field as text (numbers too), the input's defaults shown blank.
function draftFrom(b) {
    var d = {key: b.key, property: b.property, anchor: b.anchor || (b.property === 'rotate' ? 'centre' : 'bottom'), easing: b.easing || 'linear',
             smoothing: b.smoothing === undefined ? '' : String(b.smoothing), mode: b.mode || 'offset',
             source: b.input && b.input.source || '', inputKey: b.input && b.input.key || '', min: b.input && b.input.min !== undefined ? String(b.input.min) : '',
             max: b.input && b.input.max !== undefined ? String(b.input.max) : '',
             above: b.above === undefined ? '' : String(b.above), below: b.below === undefined ? '' : String(b.below), colour: b.colour || '#30e0ff'};
    if (Array.isArray(b.from)) { d.from = b.from.map(String); d.to = b.to.map(String); }
    else if (b.from !== undefined) { d.from = [String(b.from)]; d.to = [String(b.to)]; }
    else { d.from = []; d.to = []; }
    return d;
}
function num(t) { return String(t).trim() === '' ? NaN : Number(t); }
function draftErrors(d) {
    var e = [], p = property(d && d.property);
    if (!p) return ['Choose what it changes.'];
    if (!/^[a-z][a-z0-9-]{0,47}$/.test(d.key)) e.push('A name is lower case letters, digits and -, a letter first.');
    var ranges = {scale: [0.01, 100], move: [-100, 100], rotate: [-3600, 3600], texture: [-1000, 1000], glow: [0, 16]};
    if (d.property === 'colour') { if (!hex(d.from[0]) || !hex(d.to[0])) e.push('A and B are colours, #rrggbb.'); }
    else if (d.property === 'visible') {
        if (String(d.above).trim() === '' && String(d.below).trim() === '') e.push('Give a lower limit, an upper limit or both.');
        [d.above, d.below].forEach(function (v) { if (String(v).trim() !== '' && !isFinite(num(v))) e.push('Limits are numbers.'); });
    } else {
        var r = ranges[d.property], bad = d.from.concat(d.to).some(function (v) { return !(num(v) >= r[0] && num(v) <= r[1]); });
        if (bad) e.push('A and B are numbers from ' + r[0] + ' to ' + r[1] + '.');
        if (d.property === 'glow' && !hex(d.colour)) e.push('The glow colour is #rrggbb.');
    }
    if (d.source && !/^[a-z][a-z0-9-]*(\.[a-z0-9][a-z0-9-]*)+$/.test(d.source)) e.push('A source looks like com.hyprune.sources.cpu.');
    if (d.inputKey && !/^[A-Za-z_][A-Za-z0-9_.-]{0,63}$/.test(d.inputKey)) e.push('A key is a name like value or cpu.');
    var lo = String(d.min).trim() === '' ? 0 : num(d.min), hi = String(d.max).trim() === '' ? 100 : num(d.max);
    if (!isFinite(lo) || !isFinite(hi) || lo === hi) e.push('The value range needs two different numbers.');
    if (String(d.smoothing).trim() !== '' && !(num(d.smoothing) >= 0 && num(d.smoothing) <= 10)) e.push('Smoothing is 0 to 10 seconds.');
    return e;
}
// The behaviour as core takes it (defaults left out).
function fromDraft(d) {
    var b = {key: d.key, property: d.property}, input = {};
    if (d.source) input.source = d.source;
    if (d.inputKey && d.inputKey !== 'value') input.key = d.inputKey;
    if (String(d.min).trim() !== '' && num(d.min) !== 0) input.min = num(d.min);
    if (String(d.max).trim() !== '' && num(d.max) !== 100) input.max = num(d.max);
    if (Object.keys(input).length) b.input = input;
    if (d.property === 'visible') {
        if (String(d.above).trim() !== '') b.above = num(d.above);
        if (String(d.below).trim() !== '') b.below = num(d.below);
        return b;
    }
    if (d.property === 'colour') { b.from = hex(d.from[0]); b.to = hex(d.to[0]); }
    else if (d.property === 'glow') { b.from = num(d.from[0]); b.to = num(d.to[0]); b.colour = hex(d.colour); }
    else { b.from = d.from.map(num); b.to = d.to.map(num); }
    if (d.property === 'scale' || d.property === 'rotate') b.anchor = d.anchor;
    if (d.property === 'texture' && d.mode === 'scroll') b.mode = 'scroll';
    if (d.easing && d.easing !== 'linear') b.easing = d.easing;
    if (String(d.smoothing).trim() !== '') b.smoothing = num(d.smoothing);
    return b;
}
function withBehaviour(list, b, replacing) {
    var out = (list || []).filter(function (x) { return x.key !== (replacing || b.key); });
    var at = (list || []).findIndex(function (x) { return x.key === (replacing || b.key); });
    if (at < 0 || at > out.length) out.push(b); else out.splice(at, 0, b);
    return out;
}
function without(list, key) { return (list || []).filter(function (b) { return b.key !== key; }); }
function configureParams(id, list) { return {id: id, patch: {behaviours: list}}; }

// ---- capturing A and B from the gizmo ----
function yawOf(q) { return 2 * Math.atan2(q[1], q[3]) * 180 / Math.PI; } // counter-clockwise about +Y, degrees
function restOf(instance) { return instance ? {position: instance.pose.position.slice(), rotation: instance.pose.rotation.slice(), scale: instance.scale} : null; }
function round(v, places) { var f = Math.pow(10, places); return Math.round(v * f) / f; }
// The current pose against the rest pose, as one end of a behaviour: a move in the object's
// own axes (metres), a turn about +Y (degrees), or a uniform size.
function capture(rest, instance, prop) {
    if (!rest || !instance) return null;
    if (prop === 'move') {
        var a = yawOf(rest.rotation) * Math.PI / 180, dx = instance.pose.position[0] - rest.position[0],
            dy = instance.pose.position[1] - rest.position[1], dz = instance.pose.position[2] - rest.position[2];
        // Into the object's axes: turn the world difference back by the rest yaw.
        return [round(Math.cos(a) * dx - Math.sin(a) * dz, 3), round(dy, 3), round(Math.sin(a) * dx + Math.cos(a) * dz, 3)];
    }
    if (prop === 'rotate') {
        var d = yawOf(instance.pose.rotation) - yawOf(rest.rotation);
        d = ((d % 360) + 540) % 360 - 180;
        return [0, round(d, 1), 0];
    }
    if (prop === 'scale') { var r = round(instance.scale / rest.scale, 3); return [r, r, r]; }
    return null;
}
function moved(rest, instance) {
    if (!rest || !instance) return false;
    var p = instance.pose;
    return p.position.some(function (v, i) { return Math.abs(v - rest.position[i]) > 1e-4; }) ||
           p.rotation.some(function (v, i) { return Math.abs(v - rest.rotation[i]) > 1e-5; }) || Math.abs(instance.scale - rest.scale) > 1e-4;
}
function restParams(id, rest) { return {id: id, pose: {position: rest.position, rotation: rest.rotation}, scale: rest.scale}; }

// ---- what the panel says ----
function sourceOf(instanceId, b) { return b && b.input && b.input.source || CLIENT + '.' + instanceId; }
// The sources.json entry a source id names (the helper publishes com.hyprune.sources.<id>).
function entryOf(sourceId) { return String(sourceId || '').indexOf(CLIENT + '.') === 0 ? sourceId.slice(CLIENT.length + 1) : ''; }
function fmt(v) { return Array.isArray(v) ? v.map(function (x) { return String(round(x, 3)); }).join(', ') : String(v); }
function summaryText(b) {
    var p = property(b.property), label = p ? p.label : b.property;
    if (b.property === 'visible') return label + ': shown' + (b.above !== undefined ? ' from ' + b.above : '') + (b.below !== undefined ? ' below ' + b.below : '');
    var range = fmt(b.from) + ' → ' + fmt(b.to);
    if (b.property === 'scale' || b.property === 'rotate') range += ' (' + (b.anchor || (b.property === 'rotate' ? 'centre' : 'bottom')) + ')';
    if (b.property === 'texture' && b.mode === 'scroll') range += ' per second';
    if (b.property === 'glow') range += ' in ' + (b.colour || '#ffffff');
    return label + ': ' + range;
}
function inputText(instanceId, b) {
    var lo = b.input && b.input.min !== undefined ? b.input.min : 0, hi = b.input && b.input.max !== undefined ? b.input.max : 100;
    var source = sourceOf(instanceId, b);
    return (source === CLIENT + '.' + instanceId ? 'this object\'s data source' : source) + ' · ' + (b.input && b.input.key || 'value') + ' ' + lo + '–' + hi;
}
function stateText(state) {
    if (!state) return 'not running';
    if (state.condition === 'missing') return 'no data yet';
    var v = state.value === null || state.value === undefined ? '–' : String(state.value);
    return (state.condition === 'fresh' ? '' : state.condition + ' · ') + 'value ' + v + ' → ' + Math.round(state.t * 100) + '%';
}
function stateLevel(state) { return !state || state.condition === 'missing' ? 'muted' : state.condition === 'fresh' ? 'ok' : 'warning'; }
