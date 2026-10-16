// RFC-0014 world folders (phase 1 and the world wizard as amended): Director > Builder runs the
// hyprune CLI's `builder` commands (create, list, status, save, release, sky, floor, spawn,
// remote, skies, floors) as JSON-lines jobs and
// opens a folder with world.load local.<slug>. Core loads it in editor mode and writes the
// placements; git runs only in the CLI. Pure helpers: tested with node in tests/test_builder.py.

var NAME_MAX = 64, MESSAGE_MAX = 500, NOTES_MAX = 4000;
var SKY_FORMATS = ['png', 'jpg', 'jpeg', 'exr', 'hdr'];
var FLOOR_FORMATS = ['png', 'jpg', 'jpeg'];
var TILE_MIN = 0.25, TILE_MAX = 100;
var STAGES = {check: 'Checking the world', version: 'Writing the version', build: 'Building the release files', push: 'Pushing to the remote', release: 'Creating the GitHub release'};
var CODES = {
    'release.check': 'Release waits for the checklist: fix the items marked ✗ above, or release anyway.',
    'git.missing': 'Building worlds needs git 2.30 or newer: install git, then try again.',
    'git.identity': 'git doesn\'t know who you are yet: give a name and an email for this world\'s saves.',
    'git.failed': 'git failed.',
    'project.unknown': 'That world folder is gone.',
    'project.invalid': 'The world folder\'s project file is damaged.',
    'save.nothing': 'Nothing to save: there are no changes since the last save.',
    'make.invalid': 'The world couldn\'t be made from this folder.',
    'release.unsaved': 'Save first: a release is made from the saved world.',
    'release.version': 'Pick a newer version (like 0.2.0).',
    'release.id': 'This remote needs a published world id.',
    'remote.invalid': 'That isn\'t a remote URL: use https://…, ssh://… or user@host:path.',
    'remote.auth': 'Set up access to this remote in a terminal (your git credentials or SSH key), then release again.',
    'remote.rejected': 'The remote has changes Hyprune won\'t merge: resolve them with git, then release again.',
    'sky.invalid': 'That image can\'t be a sky.',
    'floor.invalid': 'That can\'t be the floor.',
    'spawn.invalid': 'That spawn is outside the plain.',
    'starter.unknown': 'That starter isn\'t available.',
    'project.exists': 'A world with that name already exists.',
    'builder.busy': 'Another save or release is still running on this world.',
    'cli.missing': 'The hyprune command didn\'t run: set HYPRUNE_CLI or put hyprune on PATH.'};
var LABELS = {create: 'Creating the world', list: 'Listing your worlds', status: 'Checking for changes', save: 'Saving', release: 'Releasing', sky: 'Setting the sky',
              floor: 'Setting the floor', spawn: 'Moving the spawn', remote: 'Setting the remote'};
// Where the world starts, relative to the sun (or the moon): the wizard's spawn choices.
var FACINGS = [{id: 'away', label: 'Sun behind you'}, {id: 'sun', label: 'Facing the sun'}, {id: 'left', label: 'Sun on your left'}, {id: 'right', label: 'Sun on your right'}];
var WIZARD_STEPS = ['name', 'sky', 'floor', 'spawn'];
var STEP_TITLES = {name: 'Name and starter', sky: 'Sky', floor: 'Floor', spawn: 'Where you start'};

function extension(path) { var m = /\.([a-z0-9]+)$/i.exec(String(path || '')); return m ? m[1].toLowerCase() : ''; }
function skyImage(path) { return SKY_FORMATS.indexOf(extension(path)) >= 0; }
function floorImage(path) { return FLOOR_FORMATS.indexOf(extension(path)) >= 0; }
function tileError(tile) {
    var t = Number(tile);
    return String(tile).trim() !== '' && isFinite(t) && t >= TILE_MIN && t <= TILE_MAX ? '' : 'A tile is ' + TILE_MIN + ' to ' + TILE_MAX + ' metres.';
}
function worldId(slug) { return 'local.' + slug; }

function nameError(name) {
    var n = String(name || '').trim();
    if (!n) return 'Give the world a name.';
    if (n.length > NAME_MAX) return 'A name is at most ' + NAME_MAX + ' characters.';
    if (/[\u0000-\u001f\u007f]/.test(n)) return 'A name has no control characters.';
    return '';
}
function versionError(v) {
    var s = String(v || '').trim();
    if (!s) return '';
    return /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$/.test(s) ? '' : 'A version looks like 0.2.0.';
}
function remoteError(url) {
    var u = String(url || '').trim();
    if (!u) return '';
    return /^(https:\/\/|ssh:\/\/)[^\s]+$/.test(u) || /^[A-Za-z0-9._-]+@[^\s/:]+:[^\s]+$/.test(u) ? '' : CODES['remote.invalid'];
}
function identityErrors(identity) {
    var e = [];
    if (!identity) return e;
    if (!String(identity.name || '').trim()) e.push('Give a name for your saves.');
    if (!/^[^\s<>@]+@[^\s<>@]+$/.test(String(identity.email || '').trim())) e.push('Give an email address for your saves.');
    return e;
}
function skyErrors(form) {
    var e = [];
    if (form && form.preset) return e;
    if (!form || !form.path) e.push('Choose an image.');
    if (!String(form && form.license || '').trim()) e.push('Give the image\'s licence (an SPDX id like CC0-1.0).');
    if (!String(form && form.author || '').trim()) e.push('Give the image\'s author.');
    if (!String(form && form.source || '').trim()) e.push('Say where the image comes from.');
    return e;
}

// The floor form: a preset (with its tile) or an image with provenance and a tile.
function floorErrors(form) {
    var e = [];
    if (!form) return ['Choose a floor.'];
    if (form.tile !== undefined && form.tile !== null && tileError(form.tile)) e.push(tileError(form.tile));
    if (form.preset) return e;
    if (!form.path) e.push('Choose an image.');
    if (!String(form.license || '').trim()) e.push('Give the image\'s licence (an SPDX id like CC0-1.0).');
    if (!String(form.author || '').trim()) e.push('Give the image\'s author.');
    if (!String(form.source || '').trim()) e.push('Say where the image comes from.');
    return e;
}

// ---- the New world wizard: name (and starter), sky, floor, where you start ----
function newWizard() {
    return {step: 0, name: '', starter: 'open-plain', sky: {preset: 'clear-day'}, floor: {preset: 'grid', tile: null}, facing: 'away'};
}
function wizardStep(w) { return WIZARD_STEPS[Math.max(0, Math.min(WIZARD_STEPS.length - 1, w ? w.step : 0))]; }
function wizardErrors(w, identity) {
    if (!w) return ['No wizard.'];
    var step = wizardStep(w);
    if (step === 'name') return (nameError(w.name) ? [nameError(w.name)] : []).concat(identityErrors(identity));
    if (step === 'sky') return skyErrors(w.sky);
    if (step === 'floor') return floorErrors(w.floor);
    return FACINGS.some(function (f) { return f.id === w.facing; }) ? [] : ['Choose where you start.'];
}
function wizardMove(w, delta) {
    var next = Object.assign({}, w);
    next.step = Math.max(0, Math.min(WIZARD_STEPS.length - 1, w.step + delta));
    return next;
}
function wizardLast(w) { return !!w && w.step === WIZARD_STEPS.length - 1; }
function skyLabel(form, skies) {
    if (!form) return '';
    if (form.preset) { var p = (skies || []).filter(function (s) { return s.id === form.preset; })[0]; return p ? p.name : form.preset; }
    return String(form.path || '').split('/').pop();
}
function floorLabel(form, floors) {
    if (!form) return '';
    var name = form.preset ? (((floors || []).filter(function (f) { return f.id === form.preset; })[0] || {}).name || form.preset) : String(form.path || '').split('/').pop();
    return form.tile ? name + ', every ' + form.tile + ' m' : name;
}
function wizardSummary(w, skies, floors) {
    if (!w) return '';
    var facing = FACINGS.filter(function (f) { return f.id === w.facing; })[0];
    return 'Open Plain · ' + skyLabel(w.sky, skies) + ' sky · ' + floorLabel(w.floor, floors) + ' floor · ' + (facing ? facing.label.toLowerCase() : '');
}

// ---- command lines (the CLI's JSON lines) ----
function skyOptions(prefix, form) {
    if (!form) return [];
    if (form.preset) return ['--' + prefix, form.preset];
    return ['--' + prefix + '-image', form.path, '--' + prefix + '-license', String(form.license).trim(), '--' + prefix + '-author', String(form.author).trim(),
            '--' + prefix + '-source', String(form.source).trim()];
}
function tileOptions(form) { return form && form.tile !== undefined && form.tile !== null && String(form.tile).trim() !== '' ? ['--tile', String(Number(form.tile))] : []; }
function createArgs(name, identity, wizard) {
    var a = ['builder', 'create', String(name).trim(), '--json'];
    if (identity) a.push('--git-name', String(identity.name).trim(), '--git-email', String(identity.email).trim());
    if (wizard) a = a.concat(['--starter', wizard.starter || 'open-plain'], skyOptions('sky', wizard.sky), skyOptions('floor', wizard.floor), tileOptions(wizard.floor),
                             wizard.facing ? ['--facing', wizard.facing] : []);
    return a;
}
function skiesArgs() { return ['builder', 'skies', '--json']; }
function floorsArgs() { return ['builder', 'floors', '--json']; }
function floorArgs(slug, form) {
    if (form.preset) return ['builder', 'floor', slug, '--preset', form.preset].concat(tileOptions(form), ['--json']);
    if (!form.path) return ['builder', 'floor', slug].concat(tileOptions(form), ['--json']);
    return ['builder', 'floor', slug, form.path, '--license', String(form.license).trim(), '--author', String(form.author).trim(), '--source', String(form.source).trim()]
        .concat(tileOptions(form), ['--json']);
}
function listArgs() { return ['builder', 'list', '--json']; }
function statusArgs(slug) { return ['builder', 'status', slug, '--json']; }
function saveArgs(slug, message) {
    var a = ['builder', 'save', slug, '--json'], m = String(message || '').trim().slice(0, MESSAGE_MAX);
    if (m) a.push('-m', m);
    return a;
}
function releaseArgs(slug, version, notes, skipCheck) {
    var a = ['builder', 'release', slug], v = String(version || '').trim(), n = String(notes || '').trim().slice(0, NOTES_MAX);
    if (v) a.push(v);
    a.push('--json');
    if (n) a.push('--notes', n);
    if (skipCheck) a.push('--skip-check');
    return a;
}
// ---- the checklist (`builder check`): items with done, blocks, level, message, hint, show ----
function checkArgs(slug) { return ['builder', 'check', slug, '--json']; }
function checkMark(item) { return !item ? '' : item.done ? (item.level === 'warning' ? '!' : '✓') : item.blocks ? '✗' : '!'; }
function checkOpen(result) { return result && result.items ? result.items.filter(function (i) { return !i.done || i.level === 'warning'; }) : []; }
function checkBlocking(result) { return result && result.items ? result.items.filter(function (i) { return i.blocks && !i.done; }) : []; }
function checkSummary(result) {
    if (!result || !result.items) return 'Checking…';
    var done = result.items.filter(function (i) { return i.done; }).length, blocking = checkBlocking(result).length;
    return done + ' of ' + result.items.length + ' done' + (blocking ? ' · ' + blocking + ' to fix before Release' : ' · ready to release');
}
// The release refused by the checklist: its items, for "Release anyway".
function releaseRefused(job) { return !!job && job.kind === 'release' && job.phase === 'failed' && !!job.error && job.error.code === 'release.check'; }
function publishingText(result) {
    if (!result || !result.publishing) return '';
    if (result.publishing.officialEligible) return 'Every part meets the official bar (CC0-1.0 or CC-BY-4.0 with an author and a source).';
    var n = result.publishing.notOfficial ? result.publishing.notOfficial.length : 0;
    return n + ' part' + (n === 1 ? '' : 's') + ' would need another licence, author or source for the official hyprune org; a release of your own is fine.';
}
function skyArgs(slug, form) {
    if (form.preset) return ['builder', 'sky', slug, '--preset', form.preset, '--json'];
    return ['builder', 'sky', slug, form.path, '--license', String(form.license).trim(), '--author', String(form.author).trim(),
            '--source', String(form.source).trim(), '--json'];
}
function remoteArgs(slug, url) { return url ? ['builder', 'remote', slug, String(url).trim(), '--json'] : ['builder', 'remote', slug, '--clear', '--json']; }

// ---- jobs ----
function newJob(kind, slug, extra) { return Object.assign({kind: kind, slug: slug || '', phase: 'running', stage: '', result: null, error: null}, extra || {}); }
function jobEvent(job, line) {
    var e = null;
    try { e = JSON.parse(line); } catch (x) { return job; }
    if (!job || !e || typeof e !== 'object') return job;
    var next = Object.assign({}, job);
    if (e.event === 'stage') next.stage = e.stage;
    else if (e.event === 'done') { next.phase = 'done'; next.result = e.result; }
    else if (e.event === 'error') { next.phase = 'failed'; next.error = e.error || {message: 'The builder failed.', code: ''}; }
    return next;
}
function jobFinished(job, code, errors) {
    if (!job || job.phase !== 'running') return job;
    var tail = String(errors || '').trim().split('\n').filter(function (l) { return l.trim(); }).pop() || '';
    return Object.assign({}, job, {phase: 'failed', error: code < 0 ? {message: CODES['cli.missing'], code: 'cli.missing'}
                                                        : {message: tail.replace(/^Error:\s*/, '') || 'The builder stopped (exit code ' + code + ').', code: ''}});
}
function errorText(error) {
    if (!error) return '';
    var known = error.code && CODES[error.code];
    if (!known) return (error.message || 'The builder failed.') + (error.hint ? ' ' + error.hint + '.' : '');
    // The CLI's own message is the more specific one for these.
    if (['save.nothing', 'release.unsaved', 'release.version', 'sky.invalid', 'floor.invalid', 'spawn.invalid', 'git.failed', 'make.invalid'].indexOf(error.code) >= 0)
        return (error.message || known) + (error.hint ? '. ' + error.hint + '.' : '');
    return known;
}
function busyText(job) { return job ? (job.stage && STAGES[job.stage] ? STAGES[job.stage] : LABELS[job.kind] || 'Working') + '…' : ''; }

// ---- what the page shows ----
// "Unsaved: placed 3 objects (12 files)": the change in words (the CLI reads it from the
// project files), with the file count git sees; files alone when only they changed.
function pendingText(status) {
    if (!status || !status.pending) return '';
    var n = status.pending.total, files = n + ' file' + (n === 1 ? '' : 's');
    if (!n) return 'Everything is saved';
    return status.changes ? 'Unsaved: ' + status.changes + ' (' + files + ')' : files + ' not saved';
}
function lastSaveText(status) {
    if (!status || !status.lastSave) return 'No saves yet';
    return 'Last save: ' + String(status.lastSave.message || '').split('\n')[0];
}
function versionText(status) {
    if (!status) return '';
    return status.lastVersion ? 'Latest version ' + status.lastVersion.tag + (status.remote ? '' : ' (local tag)') : 'Not released yet';
}
function remoteText(status) { return status && status.remote ? status.remote.url : 'No remote: releases stay on this computer as git tags.'; }
function resultText(job) {
    if (!job || job.phase !== 'done' || !job.result) return '';
    var r = job.result;
    if (job.kind === 'create') return 'Created ' + r.name + ' in ' + r.folder + '.';
    if (job.kind === 'save') return 'Saved: ' + r.message;
    if (job.kind === 'release') return 'Released ' + r.tag + (r.pushed ? ' and pushed' : ' as a local tag') + (r.release ? ': ' + r.release : '.');
    if (job.kind === 'sky') return (r.preset ? 'The sky is set' : 'The sky is set (' + r.width + ' × ' + r.height + ')') + '; the world reloads to show it.';
    if (job.kind === 'floor') return 'The floor is set (every ' + r.floor.tile + ' m); the world reloads to show it.';
    if (job.kind === 'spawn') return 'The spawn moved; the world reloads to show it.';
    if (job.kind === 'remote') return r.remote ? 'Remote set to ' + r.remote.url + '.' : 'Remote cleared.';
    return '';
}
function warningsOf(job) { return job && job.result && job.result.warnings ? job.result.warnings.filter(function (w) { return !/core runtime validation|core validation/.test(w); }) : []; }
