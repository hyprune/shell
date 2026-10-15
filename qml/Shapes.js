// Director > Objects > Shapes (RFC-0014 amendment: primitives and materials, IPC 0.31): make a
// cube, box, cylinder, sphere, plane, ramp or stairs at exact sizes in a material, and place it
// with tool 5. The hyprune CLI generates the object folder (`builder primitive` in a world
// folder, `object primitive` elsewhere) and core places it like any object. A material is a
// library entry (`builder material` / `object material`), a built-in texture (copied in on
// first use) or a plain colour. Changing a placed primitive's size or material makes another
// folder and swaps the placement to it (objects.configure {ref}), keeping its id and key.
// Pure helpers, tested with node in tests/test_shapes.py.

var SHAPES = [
    {id: 'cube', label: 'Cube', size: [1, 1, 1], hint: 'Equal sides'},
    {id: 'box', label: 'Box', size: [2, 1, 1], hint: 'Walls, floors, tables'},
    {id: 'cylinder', label: 'Cylinder', size: [1, 2, 1], hint: 'Columns, towers'},
    {id: 'sphere', label: 'Sphere', size: [1, 1, 1], hint: 'Balls, domes'},
    {id: 'plane', label: 'Plane', size: [4, 0.02, 4], hint: 'A thin slab: rugs, paths'},
    {id: 'ramp', label: 'Ramp', size: [2, 1, 4], hint: 'Rises towards the back'},
    {id: 'stairs', label: 'Stairs', size: [1.2, 1.8, 3], hint: 'Steps rise towards the back'}];
var AXES = ['Width', 'Height', 'Depth'];
var SIZE_MIN = 0.01, SIZE_MAX = 100, STEP_RISE = 0.18;
// The built-in textures (the floor presets), usable as materials anywhere.
var BUILTIN = [{key: 'grid', label: 'Grid'}, {key: 'grass', label: 'Grass'}, {key: 'sand', label: 'Sand'}, {key: 'paving', label: 'Stone paving'}, {key: 'concrete', label: 'Concrete'}];
var SWATCHES = ['#d8d8d8', '#f4f1ea', '#2b2b2b', '#b03a2e', '#e67e22', '#f1c40f', '#27ae60', '#2471a3', '#7d3c98', '#7f5539'];
var CODES = {
    'primitive.invalid': 'That shape can\'t be made.',
    'material.invalid': 'That material can\'t be saved.',
    'material.unknown': 'There is no such material.',
    'project.unknown': 'That world folder is gone.',
    'cli.missing': 'The hyprune command didn\'t run: set HYPRUNE_CLI or put hyprune on PATH.'};

function shape(id) { return SHAPES.filter(function (s) { return s.id === id; })[0] || null; }
function hex(text) {
    var t = String(text || '').trim().toLowerCase(), m = /^#?([0-9a-f])([0-9a-f])([0-9a-f])$/.exec(t);
    if (m) return '#' + m[1] + m[1] + m[2] + m[2] + m[3] + m[3];
    if (t && t[0] !== '#') t = '#' + t;
    return /^#[0-9a-f]{6}$/.test(t) ? t : '';
}
function newForm(id) {
    var s = shape(id) || SHAPES[1];
    return {shape: s.id, size: s.size.slice(), steps: null, material: {kind: 'colour', colour: '#d8d8d8', key: '', glow: null}};
}
function withShape(form, id) {
    var s = shape(id);
    if (!s) return form;
    return Object.assign({}, form, {shape: id, size: s.size.slice(), steps: null});
}
function stepsFor(form) { return form.steps ? Number(form.steps) : Math.max(1, Math.round(Number(form.size[1]) / STEP_RISE)); }
function sizeErrors(form) {
    var e = [];
    if (!form || !shape(form.shape)) return ['Choose a shape.'];
    var size = form.size.map(Number);
    for (var i = 0; i < 3; i++)
        if (!(String(form.size[i]).trim() !== '' && isFinite(size[i]) && size[i] >= SIZE_MIN && size[i] <= SIZE_MAX)) e.push(AXES[i] + ' is ' + SIZE_MIN + ' to ' + SIZE_MAX + ' m.');
    if (form.shape === 'cube' && !e.length && (size[0] !== size[1] || size[1] !== size[2])) e.push('A cube has three equal sides (use a box).');
    if (form.shape === 'stairs' && form.steps !== null && form.steps !== '' && !(Number(form.steps) >= 1 && Number(form.steps) <= 64 && Math.round(Number(form.steps)) === Number(form.steps)))
        e.push('Stairs have 1 to 64 steps.');
    var m = form.material || {};
    if (m.kind === 'colour' && !hex(m.colour)) e.push('A colour is #rrggbb.');
    if (m.kind === 'key' && !m.key) e.push('Choose a material.');
    if (m.glow && (!hex(m.glow.colour) || !(Number(m.glow.strength) >= 0 && Number(m.glow.strength) <= 16))) e.push('A glow is a colour and a strength of 0 to 16.');
    return e;
}
// Typing a cube's side sets all three.
function setSize(form, axis, text) {
    var size = form.size.slice();
    if (form.shape === 'cube') size = [text, text, text]; else size[axis] = text;
    return Object.assign({}, form, {size: size});
}
function sizeText(size) { return size.map(function (v) { return String(Math.round(Number(v) * 10000) / 10000); }).join(','); }

// ---- command lines ----
function scope(slug, verb) { return slug ? ['builder', verb, slug] : ['object', verb]; }
function primitiveArgs(slug, form) {
    var a = scope(slug, 'primitive').concat(['--shape', form.shape, '--size', sizeText(form.size)]);
    if (form.shape === 'stairs' && form.steps) a.push('--steps', String(Number(form.steps)));
    var m = form.material || {};
    if (m.kind === 'key') a.push('--material', m.key);
    else {
        a.push('--colour', hex(m.colour) || '#d8d8d8');
        if (m.glow) a.push('--emissive', hex(m.glow.colour), '--emissive-strength', String(Number(m.glow.strength)));
    }
    return a.concat(['--json']);
}
function materialsArgs(slug) { return scope(slug, 'materials').concat(['--json']); }
function rebuildArgs(slug, key) { return scope(slug, 'rebuild').concat(key ? ['--material', key] : [], ['--json']); }

// ---- the material editor ----
function newMaterial(key) {
    return {key: key || '', name: '', colour: '#ffffff', texture: {kind: 'keep'}, tile: '', glow: null, roughness: '', metallic: '', fresh: !key};
}
function materialFrom(summary) {
    if (!summary) return newMaterial('');
    return {key: summary.key, name: summary.name, colour: summary.colour, texture: {kind: 'keep'}, tile: summary.tile === null || summary.tile === undefined ? '' : String(summary.tile),
            glow: null, roughness: '', metallic: '', fresh: false, textured: !!summary.textured};
}
function materialErrors(m) {
    var e = [];
    if (!m) return ['No material.'];
    if (!/^[a-z][a-z0-9-]{0,47}$/.test(String(m.key || ''))) e.push('A key is a short name in lower case, like oak-planks.');
    if (m.name && String(m.name).length > 64) e.push('A name is at most 64 characters.');
    if (!hex(m.colour)) e.push('A colour is #rrggbb.');
    var t = m.texture || {kind: 'keep'};
    if (t.kind === 'image') {
        if (!t.path) e.push('Choose an image.');
        if (!String(t.license || '').trim()) e.push('Give the image\'s licence (an SPDX id like CC0-1.0).');
        if (!String(t.author || '').trim()) e.push('Give the image\'s author.');
        if (!String(t.source || '').trim()) e.push('Say where the image comes from.');
    }
    var textured = t.kind === 'image' || t.kind === 'preset' || (t.kind === 'keep' && m.textured);
    if (String(m.tile).trim() !== '' && !(Number(m.tile) >= 0.05 && Number(m.tile) <= 100)) e.push('A tile is 0.05 to 100 m.');
    if (String(m.tile).trim() !== '' && !textured) e.push('Only a textured material has a tile size.');
    if (String(m.roughness).trim() !== '' && !(Number(m.roughness) >= 0 && Number(m.roughness) <= 1)) e.push('Roughness is 0 to 1.');
    if (String(m.metallic).trim() !== '' && !(Number(m.metallic) >= 0 && Number(m.metallic) <= 1)) e.push('Metalness is 0 to 1.');
    if (m.glow && (!hex(m.glow.colour) || !(Number(m.glow.strength) >= 0 && Number(m.glow.strength) <= 16))) e.push('A glow is a colour and a strength of 0 to 16.');
    return e;
}
function materialArgs(slug, m) {
    var a = scope(slug, 'material').concat([m.key, '--colour', hex(m.colour)]);
    if (m.name) a.push('--name', String(m.name).trim());
    var t = m.texture || {kind: 'keep'};
    if (t.kind === 'none') a.push('--no-texture');
    else if (t.kind === 'preset') a.push('--texture-preset', t.preset);
    else if (t.kind === 'image') a.push('--texture', t.path, '--license', String(t.license).trim(), '--author', String(t.author).trim(), '--source', String(t.source).trim());
    if (String(m.tile).trim() !== '') a.push('--tile', String(Number(m.tile)));
    if (m.glow) a.push('--emissive', hex(m.glow.colour), '--emissive-strength', String(Number(m.glow.strength)));
    else if (m.glowOff) a.push('--no-emissive');
    if (String(m.roughness).trim() !== '') a.push('--roughness', String(Number(m.roughness)));
    if (String(m.metallic).trim() !== '') a.push('--metallic', String(Number(m.metallic)));
    return a.concat(['--json']);
}

// ---- placed primitives ----
// The placements a rebuild's swaps move: every instance whose ref is a swap's `from`.
function swapsFor(instances, swaps) {
    var out = [];
    (swaps || []).forEach(function (s) {
        (instances || []).forEach(function (i) { if (i.source === 'user' && i.ref === s.from) out.push({id: i.id, ref: s.to}); });
    });
    return out;
}
// A placed primitive's form, from its catalog entry's primitive (IPC 0.31).
function formFromEntry(entry) {
    var p = entry && entry.primitive;
    if (!p) return null;
    return {shape: p.shape, size: p.size.map(function (v) { return String(v); }), steps: null,
            material: p.material.key ? {kind: 'key', key: p.material.key, colour: p.material.colour, glow: null} : {kind: 'colour', colour: p.material.colour, key: '', glow: null}};
}
function sameShape(form, entry) {
    var p = entry && entry.primitive;
    if (!p || !form) return false;
    var m = form.material || {};
    return p.shape === form.shape && sizeText(p.size) === sizeText(form.size) && !form.steps &&
           (m.kind === 'key' ? p.material.key === m.key : !p.material.key && p.material.colour === hex(m.colour) && !m.glow);
}
function keyError(key) {
    var k = String(key || '').trim();
    return !k || /^[a-z][a-z0-9-]{0,47}$/.test(k) ? '' : 'A name here is lower case letters, digits and -, a letter first (like cpu-tower).';
}
function summary(form, materials) {
    if (!form) return '';
    var s = shape(form.shape), m = form.material || {}, label;
    if (m.kind === 'key') {
        var found = (materials || []).concat(BUILTIN.map(function (b) { return {key: b.key, name: b.label}; })).filter(function (x) { return x.key === m.key; })[0];
        label = found ? found.name : m.key;
    } else label = hex(m.colour) + (m.glow ? ' glowing' : '');
    var size = form.shape === 'cube' ? form.size[0] + ' m' : form.size.join(' × ') + ' m';
    return (s ? s.label : form.shape) + ' ' + size + (form.shape === 'stairs' ? ', ' + stepsFor(form) + ' steps' : '') + ' · ' + label;
}
function errorText(error) {
    if (!error) return '';
    var known = error.code && CODES[error.code];
    return (error.message || known || 'That didn\'t work.') + (error.hint ? '. ' + error.hint + '.' : '');
}
