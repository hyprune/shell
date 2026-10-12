// RFC-0011 P1 (IPC 0.22): the object catalog, user placements, the configure panel and
// object items in the pocket. Pure helpers: tested with node in tests/test_ipc22.py.

// Catalog sources as the Director names them (wire value -> badge).
var SOURCES = [{id: 'all', label: 'All'}, {id: 'package', label: 'World'}, {id: 'library', label: 'Library'}, {id: 'user', label: 'Mine'}];
var CATEGORIES = ['furniture', 'lighting', 'plants', 'signage', 'machines', 'decor', 'characters', 'vehicles', 'other'];
// Trait chips: decorative only (core decides what a trait does).
var TRAITS = {
    decorative: {label: 'Decorative', glyph: '✦'}, collidable: {label: 'Collidable', glyph: '▣'},
    movable: {label: 'Movable', glyph: '✥'}, seat: {label: 'Seat', glyph: '⊓'}, machine: {label: 'Machine', glyph: '⚙'},
    character: {label: 'Character', glyph: '☺'}, mover: {label: 'Mover', glyph: '⇄'}, mount: {label: 'Mount', glyph: '⊞'},
    interactive: {label: 'Interactive', glyph: '☛'}};
var TRAIT_ORDER = ['movable', 'collidable', 'decorative', 'seat', 'machine', 'interactive', 'mount', 'character', 'mover'];
var STATES = {active: 'Active', hidden: 'Hidden', missing: 'Missing', blocked: 'Blocked', loading: 'Loading', suspended: 'Suspended'};
// Placement rules (error.data.rule, instance.rule) in plain words.
var RULES = {
    playable: 'outside the playable area', walls: 'inside a wall', support: 'nothing to rest on',
    window: 'covers a window', approach: 'blocks the space in front of a screen', zone: 'outside the placement zones',
    'keep-clear': 'blocks a spawn or a climb', player: 'overlaps you', reach: 'out of reach',
    budget: 'over the object budget', 'library.conflict': 'another copy of that library is installed'};
// The configure panel's sections, in this order. 'data' is reserved for RFC-0013 data
// bindings: it is always listed and renders nothing in IPC 0.22.
var SECTIONS = ['transform', 'lock', 'remove', 'data'];
var POCKET_ITEM = /^pocket-[0-9]+$/;
var SCALE_MIN = 0.25, SCALE_MAX = 4, POSITION_MAX = 100000;
var TOAST_MS = 4000;

function sourceLabel(source) {
    var s = SOURCES.find(function (x) { return x.id === source; });
    return source === 'authored' ? 'World' : s && source !== 'all' ? s.label : '';
}

function categoryLabel(category) { return category ? category.charAt(0).toUpperCase() + category.slice(1) : ''; }

// Categories present in the catalog, in the schema's order.
function categories(entries) {
    var seen = {};
    (entries || []).forEach(function (e) { seen[e.category] = true; });
    return CATEGORIES.filter(function (c) { return seen[c]; });
}

function words(text) { return String(text || '').toLowerCase().split(/\s+/).filter(function (w) { return w; }); }

// filter: {source: 'all'|'package'|'library'|'user', category: ''|<category>, trait: ''|<trait>,
// query: text}. Every query word must appear in the name or a tag. Core's order is kept.
function filterCatalog(entries, filter) {
    var f = filter || {}, query = words(f.query);
    return (entries || []).filter(function (e) {
        if (f.source && f.source !== 'all' && e.source !== f.source) return false;
        if (f.category && e.category !== f.category) return false;
        if (f.trait && (e.traits || []).indexOf(f.trait) < 0) return false;
        if (!query.length) return true;
        var hay = [e.name].concat(e.tags || []).map(function (s) { return String(s).toLowerCase(); });
        return query.every(function (w) { return hay.some(function (h) { return h.indexOf(w) >= 0; }); });
    });
}

function metres(v) {
    var r = Math.abs(v) < 1 ? Math.round(v * 100) / 100 : Math.round(v * 10) / 10;
    return String(r);
}

// Bounds extents in metres: "1.2 × 2.2 × 1.3 m" (x × y × z); '' without bounds.
function sizeText(bounds, scale) {
    if (!bounds || !bounds.min || !bounds.max) return '';
    var s = typeof scale === 'number' ? scale : 1;
    return [0, 1, 2].map(function (i) { return metres(Math.max(0, bounds.max[i] - bounds.min[i]) * s); }).join(' × ') + ' m';
}

function countText(n) {
    if (typeof n !== 'number') return '';
    if (n >= 1000000) return (Math.round(n / 100000) / 10) + 'M';
    if (n >= 10000) return Math.round(n / 1000) + 'k';
    if (n >= 1000) return (Math.round(n / 100) / 10) + 'k';
    return String(n);
}

function mib(bytes) {
    var v = (bytes || 0) / 1048576;
    return String(v >= 10 ? Math.round(v) : Math.round(v * 10) / 10);
}

function trianglesText(n) { return typeof n === 'number' ? countText(n) + ' triangles' : ''; }

// What an asset costs to draw: triangles and GPU memory ('' when core has not measured it).
function costText(entry) {
    if (!entry) return '';
    return [trianglesText(entry.triangles), typeof entry.gpuBytes === 'number' ? mib(entry.gpuBytes) + ' MiB GPU' : ''].filter(function (v) { return v; }).join('  ·  ');
}

// Trait chips in a stable order (unknown names last, as given).
function traitChips(traits) {
    var list = (traits || []).slice().sort(function (a, b) {
        var i = TRAIT_ORDER.indexOf(a), j = TRAIT_ORDER.indexOf(b);
        return (i < 0 ? 99 : i) - (j < 0 ? 99 : j);
    });
    return list.map(function (t) { var d = TRAITS[t]; return {id: t, label: d ? d.label : t, glyph: d ? d.glyph : '•'}; });
}

// What a card says under its facts: invalid entries their errors, others why they can't be placed.
function entryNote(entry) {
    if (!entry) return {level: '', lines: []};
    if (entry.state === 'invalid') {
        var errors = (entry.errors || []).slice(0, 8);
        return {level: 'error', lines: errors.length ? errors : [entry.reason || 'Invalid object']};
    }
    if (!entry.placeable) return {level: 'muted', lines: [entry.reason || 'Not placeable']};
    return {level: '', lines: []};
}

function canAdd(entry) { return !!entry && entry.state === 'ready' && entry.placeable === true; }

function entryFor(entries, ref) { return ref ? (entries || []).find(function (e) { return e.ref === ref; }) || null : null; }

// Grid cursor: Up/Down step one card in reading order, PageUp/PageDown one row, Home/End.
function gridMove(index, count, columns, key) {
    if (count <= 0) return -1;
    var c = Math.max(1, columns), i = index < 0 ? -1 : index;
    var next = key === 'next' ? i + 1 : key === 'previous' ? i - 1 : key === 'rowDown' ? i + c : key === 'rowUp' ? i - c
             : key === 'home' ? 0 : key === 'end' ? count - 1 : i;
    if (i < 0) next = key === 'end' ? count - 1 : 0;
    return Math.max(0, Math.min(count - 1, next));
}

function stateText(instance) {
    if (!instance) return '';
    var text = STATES[instance.state] || instance.state;
    if (instance.state === 'blocked' && instance.rule) text += ' · ' + (RULES[instance.rule] || instance.rule);
    return text;
}

function stateLevel(instance) {
    if (!instance) return 'muted';
    return instance.state === 'active' ? 'ok' : instance.state === 'missing' || instance.state === 'blocked' ? 'warning'
         : instance.state === 'loading' ? 'busy' : 'muted';
}

function selectedInstance(instances, id) { return id ? (instances || []).find(function (i) { return i.id === id; }) || null : null; }

// Quaternions are [x, y, z, w]; yaw is the heading of the object's +Z axis about world +Y
// (degrees, -180..180], so a turn about world Y changes it by exactly that angle.
function yawDegrees(q) {
    if (!q || q.length !== 4) return 0;
    var x = q[0], y = q[1], z = q[2], w = q[3];
    var fx = 2 * (x * z + w * y), fz = 1 - 2 * (x * x + y * y);
    if (Math.abs(fx) < 1e-9 && Math.abs(fz) < 1e-9) { fx = -2 * (x * z - w * y); fz = 1 - 2 * (y * y + z * z); } // +Z vertical: +X turned back 90°
    return Math.atan2(fx, fz) * 180 / Math.PI;
}

function normalize(q) {
    var n = Math.sqrt(q.reduce(function (s, v) { return s + v * v; }, 0));
    return n > 0 ? q.map(function (v) { return v / n; }) : [0, 0, 0, 1];
}

function multiply(a, b) {
    return [a[3] * b[0] + a[0] * b[3] + a[1] * b[2] - a[2] * b[1],
            a[3] * b[1] - a[0] * b[2] + a[1] * b[3] + a[2] * b[0],
            a[3] * b[2] + a[0] * b[1] - a[1] * b[0] + a[2] * b[3],
            a[3] * b[3] - a[0] * b[0] - a[1] * b[1] - a[2] * b[2]];
}

// The rotation turned about world +Y to the given yaw; any tilt is kept.
function withYaw(q, degrees) {
    var base = q && q.length === 4 ? normalize(q) : [0, 0, 0, 1];
    var delta = (degrees - yawDegrees(base)) * Math.PI / 360;
    return normalize(multiply([0, Math.sin(delta), 0, Math.cos(delta)], base));
}

function round(v, places) { var f = Math.pow(10, places); return Math.round(v * f) / f; }

// The Transform section's field values for an instance.
function transformDraft(instance) {
    if (!instance) return null;
    var p = instance.pose.position;
    return {x: round(p[0], 3), y: round(p[1], 3), z: round(p[2], 3), yaw: round(yawDegrees(instance.pose.rotation), 1), scale: round(instance.scale, 3)};
}

function parseNumber(text) {
    if (typeof text === 'number') return isFinite(text) ? text : NaN;
    var t = String(text || '').trim().replace(',', '.');
    return /^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$/.test(t) ? Number(t) : NaN;
}

// objects.transform params from edited fields ({x, y, z, yaw, scale} as numbers or text).
// Unchanged yaw keeps core's rotation exactly; scale is sent only when it changed (clamped to
// 0.25..4 and the asset's movable.scale range). Returns {params} or {error}, or {params: null}
// when nothing changed.
function transformParams(instance, draft, scaleRange) {
    if (!instance || !draft) return {error: 'Nothing selected.'};
    var before = transformDraft(instance), v = {};
    var keys = ['x', 'y', 'z', 'yaw', 'scale'];
    for (var i = 0; i < keys.length; i++) {
        v[keys[i]] = parseNumber(draft[keys[i]]);
        if (!isFinite(v[keys[i]])) return {error: 'Enter a number for ' + (keys[i] === 'yaw' ? 'yaw' : keys[i] === 'scale' ? 'scale' : keys[i].toUpperCase()) + '.'};
    }
    if ([v.x, v.y, v.z].some(function (n) { return Math.abs(n) > POSITION_MAX; })) return {error: 'Positions stay within ±100000 m.'};
    var moved = ['x', 'y', 'z'].some(function (k) { return Math.abs(v[k] - before[k]) > 1e-6; });
    var turned = Math.abs(v.yaw - before.yaw) > 1e-6;
    var lo = Math.max(SCALE_MIN, scaleRange && scaleRange.length === 2 ? scaleRange[0] : SCALE_MIN);
    var hi = Math.min(SCALE_MAX, scaleRange && scaleRange.length === 2 ? scaleRange[1] : SCALE_MAX);
    var scaled = Math.abs(v.scale - before.scale) > 1e-6;
    if (!moved && !turned && !scaled) return {params: null};
    var position = moved ? [v.x, v.y, v.z] : instance.pose.position.slice();
    var params = {id: instance.id, pose: {position: position, rotation: turned ? withYaw(instance.pose.rotation, v.yaw) : instance.pose.rotation.slice()}};
    if (scaled) params.scale = Math.max(lo, Math.min(hi, v.scale));
    return {params: params};
}

// The configure panel for an instance: every section in SECTIONS order, each with
// visibility, whether it can be edited now and its actions.
function panelSections(instance) {
    if (!instance) return [];
    var user = instance.source === 'user', locked = !!instance.locked, hidden = instance.state === 'hidden';
    var hideable = !user && (instance.movable || hidden);
    return SECTIONS.map(function (id) {
        if (id === 'transform') return {id: id, title: 'Transform', visible: true, editable: !!instance.movable && !locked,
                                        note: locked ? 'Locked: unlock it to move it.' : !instance.movable ? (user ? 'It can\'t be moved right now.' : 'Part of the world: it stays where the world put it.') : ''};
        if (id === 'lock') return {id: id, title: 'Lock', visible: user || !!instance.movable || locked, editable: true, locked: locked};
        if (id === 'remove') return {id: id, title: user ? 'Remove / Reset' : 'Hide / Reset', visible: true, editable: true,
                                     actions: user ? [{id: 'remove', label: 'Remove', enabled: !locked}, {id: 'reset', label: 'Reset', enabled: !locked}]
                                                   : (hideable ? [{id: 'hide', label: hidden ? 'Show' : 'Hide', hidden: !hidden, enabled: !locked}] : [])
                                                     .concat([{id: 'reset', label: 'Reset', enabled: true}])};
        return {id: id, title: 'Data', visible: false, editable: false}; // RFC-0013 data bindings
    });
}

// The request a configure-panel action sends.
function sectionAction(instance, actionId) {
    if (!instance) return null;
    if (actionId === 'remove') return {method: 'objects.remove', params: {id: instance.id}};
    if (actionId === 'reset') return {method: 'objects.reset', params: {id: instance.id}};
    if (actionId === 'hide') return {method: 'objects.hide', params: {id: instance.id, hidden: instance.state !== 'hidden'}};
    if (actionId === 'lock') return {method: 'objects.configure', params: {id: instance.id, patch: {locked: !instance.locked}}};
    return null;
}

// User placements usage against core's limits (Placed view header).
function usageRows(usage, limits) {
    if (!usage || !limits) return [];
    function row(id, label, used, limit, text) { return {id: id, label: label, used: used, limit: limit, fraction: limit > 0 ? Math.min(1, used / limit) : 0, text: text}; }
    return [row('placements', 'placements', usage.placements, limits.placements, usage.placements + ' / ' + limits.placements),
            row('triangles', 'triangles', usage.triangles, limits.triangles, countText(usage.triangles) + ' / ' + countText(limits.triangles)),
            row('gpu', 'MiB GPU', usage.gpuBytes, limits.gpuBytes, mib(usage.gpuBytes) + ' / ' + mib(limits.gpuBytes))];
}

function usageText(usage, limits) {
    return usageRows(usage, limits).map(function (r) { return r.text + ' ' + r.label; }).join('  ·  ');
}

function ruleText(rule) { return rule ? RULES[rule] || rule : ''; }

// A short HUD toast for a refused object or library request. error: {code, message, rule?}
// from the bridge; message: the notice text ("<code>: <message>") when error is absent.
function errorToast(method, error, message) {
    var text = error && error.message ? error.message : String(message || '').replace(/^-?\d+:\s*/, '');
    var rule = error && error.rule ? error.rule : '';
    return {key: 'objects:error:' + method + ':' + rule, kind: 'toast', category: 'objects', tone: 'warning',
            title: /^libraries\./.test(method) ? 'Library' : 'Object', line: text || 'Core refused the request.',
            detail: rule && rule !== 'budget' ? 'Rule: ' + ruleText(rule) : '', durationMs: TOAST_MS, count: 1};
}

function pocketToast(name) {
    return {key: 'objects:pocket', kind: 'toast', category: 'objects', tone: 'info', title: name || 'Object',
            line: 'In your pocket — place it with tool 5', detail: '', durationMs: TOAST_MS, count: 1};
}

// Feedback line on the Objects page for a finished request (null: none).
function resultText(method, params) {
    var all = params && params.all === true;
    if (method === 'objects.pocket') return 'In your pocket — place it with tool 5.';
    if (method === 'objects.remove') return all ? 'Your objects in this world are removed.' : 'Removed.';
    if (method === 'objects.reset') return all ? 'Authored objects are shown and reset.' : 'Reset.';
    if (method === 'objects.hide') return params && params.hidden ? 'Hidden.' : 'Shown again.';
    if (method === 'objects.configure') return params && params.patch && params.patch.locked ? 'Locked.' : 'Unlocked.';
    if (method === 'objects.transform') return 'Moved.';
    if (method === 'objects.place') return 'Placed.';
    if (method === 'libraries.install') return 'Library installed.';
    if (method === 'libraries.remove') return 'Library removed.';
    return null;
}

function isObjectItem(id) { return typeof id === 'string' && POCKET_ITEM.test(id); }

// Pocketed objects for the tool 5 HUD (editor.unplaced.objects), the selected one flagged.
function pocketObjects(unplaced) {
    var list = unplaced && Array.isArray(unplaced.objects) ? unplaced.objects : [];
    return list.map(function (o) { return {itemId: o.itemId, ref: o.ref, name: o.name, selected: !!unplaced && unplaced.selectedId === o.itemId}; });
}
