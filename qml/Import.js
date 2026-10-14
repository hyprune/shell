// RFC-0014 imports (as amended): Director > Objects > Import… runs the hyprune CLI's
// `object import` (no core IPC): --inspect first, a review form, then the import with JSON
// lines. Pure helpers: tested with node in tests/test_import.py.

var FORMATS = ['glb', 'gltf', 'obj', 'fbx', 'dae', '3ds', 'ply', 'stl'];
var CATEGORIES = ['furniture', 'lighting', 'plants', 'signage', 'machines', 'decor', 'characters', 'vehicles', 'other'];
var SURFACES = [{id: 'floor', label: 'Floor'}, {id: 'wall', label: 'Wall'}, {id: 'ceiling', label: 'Ceiling'}, {id: 'any', label: 'Floats'}];
var UNITS = [{id: 'auto', label: 'Auto'}, {id: 'm', label: 'Metres'}, {id: 'cm', label: 'Centimetres'}, {id: 'mm', label: 'Millimetres'},
             {id: 'in', label: 'Inches'}, {id: 'ft', label: 'Feet'}];
var SCALE = {m: 1, cm: 0.01, mm: 0.001, in: 0.0254, ft: 0.3048};
var UP = [{id: 'y', label: 'Y up'}, {id: 'z', label: 'Z up'}];
var YAW = [{id: '0', label: '0°'}, {id: '90', label: '90°'}, {id: '180', label: '180°'}, {id: '270', label: '270°'}];
var TEXTURES = [{id: '1024', label: '1024 px'}, {id: '2048', label: '2048 px'}, {id: '4096', label: '4096 px'}];
var COLLISION = [{id: 'convex', label: 'Convex hull'}, {id: 'box', label: 'Box'}, {id: 'none', label: 'None'}];
var LIGHTING = [{id: 'lit', label: 'Lit'}, {id: 'unlit', label: 'Baked into textures'}];
// RFC-0014 "Licence and provenance": a short list, any other SPDX expression, or unknown. A licence never blocks an import.
var LICENCES = [{id: 'unknown', label: 'I don\'t know'}, {id: 'CC0-1.0', label: 'CC0 1.0 (public domain)'}, {id: 'CC-BY-4.0', label: 'CC BY 4.0'},
                {id: 'CC-BY-3.0', label: 'CC BY 3.0'}, {id: 'CC-BY-SA-4.0', label: 'CC BY-SA 4.0'}, {id: 'CC-BY-NC-4.0', label: 'CC BY-NC 4.0'},
                {id: 'other', label: 'Other SPDX expression…'}];
var STAGES = [{id: 'read', label: 'Read'}, {id: 'clean', label: 'Clean'}, {id: 'fit', label: 'Fit'}, {id: 'simplify', label: 'Simplify'},
              {id: 'textures', label: 'Textures'}, {id: 'collision', label: 'Collision'}, {id: 'thumbnail', label: 'Thumbnail'},
              {id: 'ktx2', label: 'KTX2'}, {id: 'compress', label: 'Compress'}, {id: 'check', label: 'Check'}];
var RULES = {
    'import.unsupported': 'That file type can\'t be imported: use glTF, GLB, OBJ, FBX, DAE, 3DS, PLY or STL (Blender can export glTF).',
    'import.remote': 'The model loads files from the internet: download them next to it first.',
    'import.draco': 'The glTF is Draco-compressed: export it again without Draco.',
    'import.invalid': 'The file could not be read as a model.', 'import.empty': 'The model has nothing to draw.',
    'import.limit': 'The file is larger than 2 GiB.', 'import.source': 'That is not a regular file.',
    'cli.missing': 'The hyprune command didn\'t run: set HYPRUNE_CLI or put hyprune on PATH.'};
var TRIANGLES_MIN = 100, TRIANGLES_MAX = 2000000, TRIANGLES_DEFAULT = 50000, NAME_MAX = 64;

function extension(path) { var m = /\.([a-z0-9]+)$/i.exec(String(path || '')); return m ? m[1].toLowerCase() : ''; }
function importable(path) { return FORMATS.indexOf(extension(path)) >= 0; }

function newJob(phase, path) { return {phase: phase, path: path || '', inspection: null, form: null, stage: '', stages: [], result: null, error: null, cancelled: false}; }

function inspectArgs(path) { return ['object', 'import', path, '--inspect', '--json']; }

// 12544 -> "12,544" (no locale dependence).
function count(n) { return typeof n === 'number' ? String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ',') : ''; }

// The review form's starting values: the guessed units, the recommended targets, nothing recorded.
function defaultForm(inspection) {
    var i = inspection || {};
    return {name: (i.name || 'Imported object').slice(0, NAME_MAX), category: 'other', surface: 'floor', units: 'auto', up: i.up || 'y', yaw: '0',
            maxTriangles: String(TRIANGLES_DEFAULT), maxTexture: '2048', collision: 'convex', lighting: 'lit',
            licence: 'unknown', licenceOther: '', author: '', source: ''};
}

function unitsOf(inspection, form) { return form && form.units && form.units !== 'auto' ? form.units : inspection && inspection.unitsGuess || 'm'; }
function unitsLabel(id) { var u = UNITS.find(function (x) { return x.id === id; }); return u ? u.label.toLowerCase() : id; }

// Width x height x depth in metres after units, up axis and turn.
function sizeMetres(inspection, form) {
    if (!inspection || !inspection.extent) return null;
    var s = SCALE[unitsOf(inspection, form)] || 1, e = inspection.extent;
    var w = e[0], h = form && form.up === 'z' ? e[2] : e[1], d = form && form.up === 'z' ? e[1] : e[2];
    if (form && (form.yaw === '90' || form.yaw === '270')) { var t = w; w = d; d = t; }
    return [w * s, h * s, d * s];
}
function metres(v) { return v >= 10 ? String(Math.round(v * 10) / 10) : String(Math.round(v * 100) / 100); }
function sizeText(dims) { return dims ? dims.map(metres).join(' × ') + ' m  (width × height × depth)' : ''; }
// "Auto: centimetres (182 units across)" for the units choice.
function unitsNote(inspection, form) {
    if (!inspection) return '';
    var across = Math.max.apply(null, inspection.extent || [0]);
    var guessed = form.units === 'auto' ? 'Auto: ' + unitsLabel(inspection.unitsGuess) : unitsLabel(form.units);
    return guessed + '  ·  ' + metres(across) + ' units across in the file';
}
// A size that looks wrong: confirm before importing.
function sizeWarning(dims) {
    if (!dims) return '';
    var m = Math.max(dims[0], dims[1], dims[2]);
    if (m < 0.05) return 'Very small: check the units.';
    if (m > 32) return 'Larger than 32 m: check the units (objects this big are better as a world map).';
    return '';
}

function trianglesNote(inspection, form) {
    if (!inspection) return '';
    var target = parseInt(form.maxTriangles, 10), n = inspection.triangles;
    if (!(target > 0)) return '';
    return n > target ? count(n) + ' triangles: simplified to about ' + count(target) + '.' : count(n) + ' triangles: under the target, kept as they are.';
}

function licenceValue(form) {
    if (!form || form.licence === 'unknown') return '';
    return form.licence === 'other' ? String(form.licenceOther || '').trim() : form.licence;
}

// Problems that stop Import (none of them about the licence: it never blocks).
function formErrors(form) {
    var errors = [];
    if (!form) return ['Nothing to import.'];
    var name = String(form.name || '').trim();
    if (!name || name.length > NAME_MAX) errors.push('Give it a name of 1 to 64 characters.');
    var t = Number(form.maxTriangles);
    if (!(Math.floor(t) === t && t >= TRIANGLES_MIN && t <= TRIANGLES_MAX)) errors.push('The triangle target is a whole number from 100 to 2,000,000.');
    if (form.licence === 'other' && !licenceValue(form)) errors.push('Type the SPDX expression, or choose "I don\'t know".');
    return errors;
}

// The import command for a reviewed form.
function jobArgs(path, form) {
    var args = ['object', 'import', path, '--json', '--name', String(form.name).trim(), '--category', form.category, '--surface', form.surface,
                '--units', form.units, '--up', form.up, '--yaw', String(form.yaw), '--max-triangles', String(Number(form.maxTriangles)),
                '--max-texture', String(form.maxTexture), '--collision', form.collision, '--lighting', form.lighting];
    var licence = licenceValue(form), author = String(form.author || '').trim(), source = String(form.source || '').trim();
    if (licence) args.push('--license', licence);
    if (author) args.push('--author', author);
    if (source) args.push('--source', source);
    return args;
}

// One JSON line of the running import: {event: stage|done|error}.
function jobEvent(job, line) {
    var e = null;
    try { e = JSON.parse(line); } catch (x) { return job; }
    if (!e || typeof e !== 'object') return job;
    var next = Object.assign({}, job);
    if (e.event === 'stage') { next.stage = e.stage; next.stages = (job.stages || []).concat([e.stage]); if (e.message) next.message = e.message; }
    else if (e.event === 'done' && job.phase === 'inspecting') { next.phase = 'review'; next.inspection = e.result; next.form = defaultForm(e.result); }
    else if (e.event === 'done') { next.phase = 'done'; next.result = e.result; }
    else if (e.event === 'error') { next.phase = 'failed'; next.error = e.error || {message: 'The import failed.', rule: ''}; }
    return next;
}

// The process ended: a job still inspecting or running failed (with stderr's last line).
function jobFinished(job, code, errors) {
    if (!job || (job.phase !== 'inspecting' && job.phase !== 'running')) return job;
    var tail = String(errors || '').trim().split('\n').filter(function (l) { return l.trim(); }).pop() || '';
    var next = Object.assign({}, job, {phase: 'failed'});
    next.error = job.cancelled ? {message: 'Cancelled.', rule: ''} : code < 0 ? {message: RULES['cli.missing'], rule: 'cli.missing'}
               : {message: tail.replace(/^Error:\s*/, '') || 'The import stopped (exit code ' + code + ').', rule: ''};
    return next;
}

function errorText(error) {
    if (!error) return '';
    return error.rule && RULES[error.rule] ? RULES[error.rule] + (error.message && error.rule !== 'cli.missing' ? '  (' + error.message + ')' : '') : error.message || 'The import failed.';
}

function stageRows(job) {
    var seen = job ? job.stages || [] : [];
    return STAGES.map(function (s) {
        return {id: s.id, label: s.label, state: job && job.stage === s.id && job.phase === 'running' ? 'current' : seen.indexOf(s.id) >= 0 ? 'done' : 'waiting'};
    });
}

function mib(bytes) { var v = (bytes || 0) / 1048576; return (v >= 10 ? Math.round(v) : Math.round(v * 10) / 10) + ' MiB'; }
// A file size: bytes, KiB, MiB or GiB.
function fileSize(bytes) {
    var units = ['bytes', 'KiB', 'MiB', 'GiB'], v = Number(bytes) || 0, i = 0;
    while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
    return (i ? (v >= 10 ? Math.round(v) : Math.round(v * 10) / 10) : v) + ' ' + units[i];
}

// What the finished import did, line by line, and its warnings.
function resultLines(result) {
    if (!result) return [];
    var b = result.before || {}, a = result.after || {};
    var lines = ['Added to My objects as ' + result.ref];
    lines.push(count(a.triangles) + ' triangles' + (b.triangles !== a.triangles ? ' (from ' + count(b.triangles) + ')' : ''));
    if (a.maxTexture) lines.push('Largest texture ' + a.maxTexture + ' px' + (b.maxTexture !== a.maxTexture ? ' (from ' + b.maxTexture + ' px)' : '') + '  ·  about ' + mib(a.gpuBytes) + ' on the GPU');
    if (a.extent) lines.push('Size ' + a.extent.map(metres).join(' × ') + ' m');
    lines.push(a.collisionTriangles ? 'Collision proxy: ' + count(a.collisionTriangles) + ' triangles' : 'No collision');
    return lines;
}

// The Objects page feedback line for a finished import.
function resultText(result) { return result ? 'Imported ' + (result.manifest && result.manifest.name || result.id) + ': it appears in the catalog under Mine.' : null; }
