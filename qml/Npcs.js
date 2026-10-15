// RFC-0011 P2 (IPC 0.23): characters (spawn on a route or a standing spot, settings, stops on
// user routes), the Characters panel, the drawing hint and interaction prompts (aimed prompt,
// choice list, caption, panel, waypoint and guide). Pure helpers: tested with node in
// tests/test_ipc23.py.

var MOTIONS = [{id: 'auto', label: 'Auto'}, {id: 'always', label: 'Always'}, {id: 'still', label: 'Still'}, {id: 'off', label: 'Off'}];
var MOTION_NOTES = {
    auto: 'Animates whenever the world is shown. Pick Still or Off to pause them.',
    always: 'The same as Auto: animates whenever the world is shown.',
    still: 'Characters hold a standing pose.',
    off: 'Characters are not drawn.'};
var STATES = {none: 'No characters', animating: 'Animating', paused: 'Paused', still: 'Still', off: 'Off'};
// npcs.reason (core's words) as a short phrase. Core 0.7.2+ sends only inactive, focus and
// reduced motion; the rest are kept for older cores.
var REASONS = {
    inactive: 'the world is not shown', typing: 'you are typing in a window', focus: 'a window has focus',
    'free cursor': 'the cursor is free', idle: 'you are idle', battery: 'on battery', 'usb-c power': 'on USB-C power',
    'power unknown': 'the power supply is unknown', 'reduced motion': 'reduced motion is on'};
var ACTIVITIES = {
    idle: 'Idle', walking: 'Walking', running: 'Running', stopped: 'Stopped', sitting: 'Sitting', guiding: 'Guiding',
    interacting: 'Talking', suspended: 'Suspended'};
var CLIPS = [{id: 'look_around', label: 'Look around'}, {id: 'wave', label: 'Wave'}, {id: 'nod', label: 'Nod'}, {id: 'idle_fidget', label: 'Fidget'}];
// Accent swatches (sRGB hex); the wire value is linear RGB.
var ACCENTS = ['#d9573b', '#e2a33a', '#5aa469', '#3c8dbc', '#7a5fc4', '#d06a9e', '#e8e4d8', '#3b3f46'];
// Walkability and placement rules (error.data.rule) for characters and routes.
var RULES = {
    walkable: 'the route is not walkable', reach: 'out of reach', playable: 'outside the playable area', walls: 'inside a wall',
    support: 'nothing to stand on', 'keep-clear': 'blocks a spawn or a climb', player: 'overlaps you', approach: 'blocks the space in front of a screen',
    budget: 'over the character budget'};
// Director panel ids an interaction may open (shell tab keys), plus aliases.
var PANEL_ALIASES = {'whats-new': 'whatsnew', news: 'whatsnew', characters: 'objects', overview: 'map'};
var SPEED_MIN = 0.25, SPEED_MAX = 2, PHASE_MAX = 0.999;
var STOP_MIN = 0.5, STOP_MAX = 600, STOP_DEFAULT = 3, STOPS_MAX = 32, PER_PATH = 8;
var INTERACT_KEY = 'E';
var TOAST_MS = 4000;

function isCharacter(entry) { return !!entry && (entry.traits || []).indexOf('character') >= 0; }

// A character entry spawns with npcs.spawn (objects.place refuses characters), so core's
// placeable flag does not apply; the entry must be ready.
function canSpawn(entry) { return isCharacter(entry) && entry.state === 'ready'; }

function spawnNote(entry) {
    if (!isCharacter(entry) || canSpawn(entry)) return '';
    return (entry.errors && entry.errors.length ? entry.errors[0] : entry.reason) || 'Not ready';
}

function sourceLabel(source) { return source === 'user' ? 'Mine' : source === 'package' || source === 'authored' ? 'World' : ''; }

function pathLabel(record) { return record ? record.name || record.id : ''; }

function refId(ref) { var s = String(ref || ''); var i = s.indexOf('/'); return i >= 0 ? s.slice(i + 1) : s; }

// A qualified path ref ('package/<id>' or 'user/<id>'); a bare id means package/<id>.
function qualified(ref) { return !ref ? '' : /^(package|user)\//.test(ref) ? ref : 'package/' + ref; }

function pathFor(paths, ref) {
    var q = qualified(ref);
    return q ? (paths || []).find(function (p) { return p.ref === q; }) || null : null;
}

// The route column: package and user routes (use "route") from paths.list, each enabled only
// when core says it is walkable and has room for another character. Paths the user drew with
// tool 3 (user, "generic") are listed too: core makes one a route when a character is put on
// it and it is walkable for that character (core 0.8.4), else refuses with the reason.
function drawnPath(p) { return !!p && p.source === 'user' && p.use === 'generic' && (p.points || []).length >= 2; }

function routeOptions(paths) {
    return (paths || []).filter(function (p) { return p.use === 'route' || drawnPath(p); }).map(function (p) {
        if (drawnPath(p))
            return {ref: p.ref, id: p.id, source: p.source, sourceLabel: sourceLabel(p.source), label: p.name || 'Drawn path',
                    points: (p.points || []).length, closed: !!p.closed, walkable: false, bound: 0, enabled: true,
                    note: 'Drawn with tool 3 · becomes a route', level: ''};
        var bound = (p.bound || []).length, full = bound >= PER_PATH;
        var note = p.walkable !== true ? (p.problems && p.problems.length ? p.problems[0] : 'Not walkable')
                 : full ? PER_PATH + ' characters already walk it'
                 : bound ? bound + (bound === 1 ? ' character walks it' : ' characters walk it') : '';
        return {ref: p.ref, id: p.id, source: p.source, sourceLabel: sourceLabel(p.source), label: pathLabel(p),
                points: (p.points || []).length, closed: !!p.closed, walkable: p.walkable === true, bound: bound,
                enabled: p.walkable === true && !full, note: note, level: p.walkable !== true ? 'warning' : full ? 'muted' : ''};
    });
}

function routeText(paths, ref) {
    if (!ref) return '';
    var p = pathFor(paths, ref);
    return p ? pathLabel(p) : refId(ref);
}

function parseNumber(text) {
    if (typeof text === 'number') return isFinite(text) ? text : NaN;
    var t = String(text === undefined || text === null ? '' : text).trim().replace(',', '.');
    return /^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$/.test(t) ? Number(t) : NaN;
}

function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
function round(v, places) { var f = Math.pow(10, places); return Math.round(v * f) / f; }

function clampSpeed(v) { var n = parseNumber(v); return isFinite(n) ? round(clamp(n, SPEED_MIN, SPEED_MAX), 2) : 1; }
function clampPhase(v) { var n = parseNumber(v); return isFinite(n) ? round(clamp(n, 0, PHASE_MAX), 3) : 0; }

function srgbToLinear(c) { return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
function linearToSrgb(c) { return c <= 0.0031308 ? c * 12.92 : 1.055 * Math.pow(c, 1 / 2.4) - 0.055; }

// '#rrggbb' -> linear [r, g, b] (0..1, 4 places), or null.
function accentFromHex(hex) {
    var m = /^#?([0-9a-fA-F]{6})$/.exec(String(hex || '').trim());
    if (!m) return null;
    return [0, 2, 4].map(function (i) { return round(srgbToLinear(parseInt(m[1].slice(i, i + 2), 16) / 255), 4); });
}

function hexFromAccent(accent) {
    if (!accent || accent.length !== 3) return '';
    return '#' + accent.map(function (v) {
        var s = Math.round(clamp(linearToSrgb(clamp(v, 0, 1)), 0, 1) * 255).toString(16);
        return s.length < 2 ? '0' + s : s;
    }).join('');
}

// Spawn / bind settings {speed, phase, accent: '#rrggbb'|'' , reverse, style?} as params: defaults
// (speed 1, phase 0, no accent, forward) are left out; phase and reverse only with a route.
// style (IPC 0.28): {walk, run, idle} ('' plain) when the core and character take styles;
// spawn sends a style only when one is set, a rebind always (null clears it).
function settingsParams(settings, onRoute) {
    var s = settings || {}, out = {};
    if (s.style) {
        var style = styleParam(s.style);
        if (style || s.clearStyle) out.style = style;
    }
    var speed = clampSpeed(s.speed === undefined ? 1 : s.speed);
    if (speed !== 1) out.speed = speed;
    var accent = accentFromHex(s.accent);
    if (accent) out.accent = accent;
    if (onRoute) {
        var phase = clampPhase(s.phase === undefined ? 0 : s.phase);
        if (phase > 0) out.phase = phase;
        if (s.reverse === true) out.reverse = true;
    }
    return out;
}

function merge(a, b) { var out = {}; Object.keys(a).forEach(function (k) { out[k] = a[k]; }); Object.keys(b).forEach(function (k) { out[k] = b[k]; }); return out; }

// The request for a spawn choice: {kind: 'route', path} | {kind: 'stand'} | {kind: 'draw'}.
function spawnRequest(ref, choice, settings) {
    if (!ref || !choice) return null;
    if (choice.kind === 'route' && choice.path)
        return {method: 'npcs.spawn', params: merge({ref: ref, path: qualified(choice.path)}, settingsParams(settings, true))};
    if (choice.kind === 'stand') return {method: 'npcs.spawn', params: merge({ref: ref}, settingsParams(settings, false))};
    if (choice.kind === 'draw') {
        var spawn = merge({ref: ref}, settingsParams(settings, true));
        delete spawn.reverse; // a drawn route starts where the player starts drawing
        delete spawn.style;   // paths.draw spawn takes no style (set it after, with a rebind)
        return {method: 'paths.draw', params: {use: 'route', spawn: spawn}};
    }
    return null;
}

// Rebinding a user character: another route (npcs.bind) or a freshly drawn one (paths.draw bind).
function bindRequest(instance, choice, settings) {
    if (!instance || instance.source !== 'user' || !choice) return null;
    if (choice.kind === 'route' && choice.path)
        return {method: 'npcs.bind', params: merge({id: instance.id, path: qualified(choice.path)}, settingsParams(settings, true))};
    if (choice.kind === 'draw') return {method: 'paths.draw', params: {use: 'route', bind: instance.id}};
    if (choice.kind === 'settings') {
        var params = settingsParams(settings, !!instance.path);
        if (!Object.keys(params).length) return null;
        return {method: 'npcs.bind', params: merge({id: instance.id}, params)};
    }
    return null;
}

function characters(instances) { return (instances || []).filter(function (i) { return i.character === true; }); }

function disabled(instance) { return !!instance && instance.state === 'hidden'; }

function activityText(instance) {
    if (!instance) return '';
    if (disabled(instance)) return 'Disabled';
    if (instance.state === 'suspended') return 'Suspended · route not walkable';
    if (instance.state === 'missing') return 'Missing';
    if (instance.state === 'loading') return 'Loading';
    return ACTIVITIES[instance.activity] || (instance.activity ? instance.activity : 'Idle');
}

function activityLevel(instance) {
    if (!instance) return 'muted';
    if (instance.state === 'suspended' || instance.state === 'missing' || instance.state === 'blocked') return 'warning';
    if (disabled(instance)) return 'muted';
    return instance.state === 'loading' ? 'busy' : 'ok';
}

function placeText(instance, paths) {
    if (!instance) return '';
    if (instance.path) return 'Route · ' + routeText(paths, instance.path);
    if (instance.seat) return 'Seat · ' + instance.seat;
    return 'Standing spot';
}

// Characters panel rows (authored and user), in core's order.
function characterRows(instances, paths) {
    return characters(instances).map(function (i) {
        return {id: i.id, name: i.name, source: i.source, sourceLabel: sourceLabel(i.source), place: placeText(i, paths),
                activity: activityText(i), level: activityLevel(i), disabled: disabled(i), user: i.source === 'user'};
    });
}

function selectedCharacter(instances, id) {
    var list = characters(instances);
    return id ? list.find(function (i) { return i.id === id; }) || null : null;
}

// Actions on one character: Disable/Enable (authored and user), Rebind and Remove (user only).
function characterActions(instance) {
    if (!instance) return [];
    var user = instance.source === 'user';
    return [{id: 'disable', label: disabled(instance) ? 'Enable' : 'Disable', method: 'npcs.disable', visible: true},
            {id: 'rebind', label: 'Rebind route', method: 'npcs.bind', visible: user},
            {id: 'remove', label: 'Remove', method: 'npcs.remove', visible: user}];
}

function characterRequest(instance, actionId) {
    if (!instance) return null;
    if (actionId === 'disable') return {method: 'npcs.disable', params: {id: instance.id, disabled: !disabled(instance)}};
    if (actionId === 'remove' && instance.source === 'user') return {method: 'npcs.remove', params: {id: instance.id}};
    return null;
}

function motionRequest(motion) {
    return MOTIONS.some(function (m) { return m.id === motion; }) ? {method: 'graphics.set', params: {patch: {npc_motion: motion}}} : null;
}

// The effective state line: "Animating", "Paused · on battery", "Off".
function stateText(npcs) {
    if (!npcs) return '';
    var text = STATES[npcs.state] || npcs.state;
    if (npcs.state === 'paused' && npcs.reason) text += ' · ' + (REASONS[npcs.reason] || npcs.reason);
    return text;
}

function stateLevel(npcs) {
    if (!npcs) return 'muted';
    return npcs.state === 'animating' ? 'ok' : npcs.state === 'paused' ? 'warning' : 'muted';
}

function usageText(npcs) {
    if (!npcs || !npcs.usage || !npcs.limits) return '';
    return npcs.usage.authored + ' / ' + npcs.limits.authored + ' world  ·  ' + npcs.usage.user + ' / ' + npcs.limits.user + ' mine';
}

function userFull(npcs) { return !!npcs && !!npcs.usage && !!npcs.limits && npcs.usage.user >= npcs.limits.user; }

// ---- Stops on user routes ----

function editableRoute(record) { return !!record && record.source === 'user' && record.use === 'route'; }

function stopKind(stop) { return stop.seat ? 'seat' : stop.clip ? 'clip' : stop.face ? 'face' : 'wait'; }

// Editable drafts of a path's stops, by point.
function stopDrafts(record) {
    return ((record && record.stops) || []).slice().sort(function (a, b) { return a.point - b.point; }).map(function (s) {
        return {point: s.point, seconds: typeof s.seconds === 'number' ? s.seconds : STOP_DEFAULT, kind: stopKind(s),
                clip: s.clip || 'look_around', seat: s.seat || '', face: s.face || null};
    });
}

function nextStopPoint(record, drafts) {
    var count = record && record.points ? record.points.length : 0, used = {};
    (drafts || []).forEach(function (d) { used[d.point] = true; });
    for (var i = 0; i < count; i++) if (!used[i]) return i;
    return -1;
}

function addStop(record, drafts) {
    var point = nextStopPoint(record, drafts);
    if (point < 0 || (drafts || []).length >= STOPS_MAX) return drafts || [];
    return (drafts || []).concat([{point: point, seconds: STOP_DEFAULT, kind: 'wait', clip: 'look_around', seat: '', face: null}])
        .sort(function (a, b) { return a.point - b.point; });
}

// paths.set for a user route with edited stops. Returns {method, params} or {error}.
function stopsRequest(record, drafts) {
    if (!editableRoute(record)) return {error: 'Only your own routes take stops.'};
    var count = record.points.length, seen = {}, stops = [];
    if ((drafts || []).length > STOPS_MAX) return {error: 'A route has at most ' + STOPS_MAX + ' stops.'};
    for (var i = 0; i < (drafts || []).length; i++) {
        var d = drafts[i], point = parseNumber(d.point), seconds = parseNumber(d.seconds);
        if (!isFinite(point) || point !== Math.floor(point) || point < 0 || point >= count) return {error: 'Stop points run from 0 to ' + (count - 1) + '.'};
        if (seen[point]) return {error: 'One stop per point (point ' + point + ').'};
        seen[point] = true;
        if (!isFinite(seconds) || seconds < STOP_MIN || seconds > STOP_MAX) return {error: 'Stops last ' + STOP_MIN + ' to ' + STOP_MAX + ' seconds.'};
        var stop = {point: point, seconds: seconds};
        if (d.kind === 'clip') {
            if (!CLIPS.some(function (c) { return c.id === d.clip; })) return {error: 'Pick a gesture for the stop at point ' + point + '.'};
            stop.clip = d.clip;
        } else if (d.kind === 'seat') {
            var seat = String(d.seat || '').trim();
            if (!seat || seat.length > 192) return {error: 'Name a seat for the stop at point ' + point + '.'};
            stop.seat = seat;
        } else if (d.kind === 'face' && d.face) stop.face = d.face;
        stops.push(stop);
    }
    stops.sort(function (a, b) { return a.point - b.point; });
    var path = {id: record.id, use: record.use, closed: !!record.closed, points: record.points, stops: stops};
    if (record.name) path.name = record.name;
    if (typeof record.speed === 'number') path.speed = record.speed;
    return {method: 'paths.set', params: {path: path}};
}

// ---- Drawing (paths.draw in progress: npcs.drawing) ----

function drawingHint(drawing, name) {
    if (!drawing) return null;
    var who = name || 'The character';
    return {title: drawing.use === 'route' ? 'Drawing a route' : 'Drawing a path',
            line: 'Click points with tool 3. Leave tool 3 or press Done to finish.',
            detail: drawing.spawn ? who + ' starts walking it when you finish.' : drawing.bind ? who + ' walks it when you finish.' : '',
            pathId: drawing.pathId};
}

// ---- Interaction prompts ----

// The HUD prompt for the aimed character: one interaction shows its prompt (core's prompt,
// else its label); several show "Talk to <name>". Nothing when it has none. `note`: why it
// stands still and where that is set (pauseNote), '' while characters animate.
function aimedPrompt(aimed, npcs) {
    if (!aimed || !aimed.interactions || !aimed.interactions.length) return null;
    var text = aimed.interactions.length === 1 ? (aimed.prompt || aimed.interactions[0].label) : 'Talk to ' + aimed.name;
    return {key: INTERACT_KEY, text: text, name: aimed.name, objectId: aimed.objectId, count: aimed.interactions.length,
            note: pauseNote(npcs)};
}

// Why characters don't move, short, with the setting's place: "Posed still · Objects › Characters".
// Only the user's settings stop them while the world is shown (core 0.7.2+).
function pauseNote(npcs) {
    if (!npcs) return '';
    if (npcs.state === 'still') return 'Posed still · Objects › Characters';
    if (npcs.state !== 'paused' || !npcs.reason) return '';
    if (npcs.reason === 'reduced motion') return 'Reduced motion · Settings';
    return 'Paused · ' + (REASONS[npcs.reason] || npcs.reason) + ' · Objects › Characters';
}

function interactionKey(interaction) {
    if (!interaction) return '';
    return [interaction.objectId, interaction.interactionId || '', interaction.type, interaction.label].join('|');
}

// The choice list (type choose): numbered choices.
function choiceItems(interaction) {
    if (!interaction || interaction.type !== 'choose') return [];
    return (interaction.choices || []).slice(0, 8).map(function (c, i) { return {id: c.id, label: c.label, key: String(i + 1)}; });
}

function choiceMove(index, count, key) {
    if (count <= 0) return -1;
    if (key === 'next') return index < 0 ? 0 : (index + 1) % count;
    if (key === 'previous') return index < 0 ? count - 1 : (index - 1 + count) % count;
    if (key === 'home') return 0;
    if (key === 'end') return count - 1;
    return clamp(index, 0, count - 1);
}

// option (IPC 0.28): a dance interaction's chosen dance; left out for "any".
function chooseParams(interaction, choiceId, option) {
    if (!interaction) return null;
    var params = {objectId: interaction.objectId, interactionId: choiceId || null};
    if (choiceId && option) params.option = option;
    return params;
}

// ---- Styles and dances (IPC 0.28, the shared clip library) ----

var STYLE_ROLES = [{id: 'walk', label: 'Walk'}, {id: 'run', label: 'Run'}, {id: 'idle', label: 'Idle'}];

// "calm-2" -> "Calm 2", "hip-hop" -> "Hip hop".
function styleLabel(style) {
    var s = String(style || '').replace(/-/g, ' ');
    return s ? s.charAt(0).toUpperCase() + s.slice(1) : 'Plain';
}

// A catalog entry's motion (catalogEntry.motion): does it offer any walk, run or idle style?
function hasStyles(motion) {
    return !!motion && !!motion.styles && STYLE_ROLES.some(function (r) { return (motion.styles[r.id] || []).length > 0; });
}

// The choices for one role: Plain, then the styles the character can play.
function styleChoices(motion, role) {
    var list = motion && motion.styles ? motion.styles[role] || [] : [];
    return [{id: '', label: 'Plain'}].concat(list.map(function (s) { return {id: s, label: styleLabel(s)}; }));
}

// {walk, run, idle} with '' for plain -> the characterStyle param, or null when all are plain.
function styleParam(style) {
    var out = {};
    STYLE_ROLES.forEach(function (r) { if (style && typeof style[r.id] === 'string' && style[r.id]) out[r.id] = style[r.id]; });
    return Object.keys(out).length ? out : null;
}

// A character's dances: the options of its dance interaction (from npcs.aimed), or null.
function danceOptions(interactions, interactionId) {
    var found = (interactions || []).filter(function (i) { return i.id === interactionId && i.type === 'dance'; })[0];
    return found && found.options && found.options.length ? found.options : null;
}

// The dance list: "Any dance" first (core picks), then each dance; keys 1-9.
function danceItems(options) {
    return [{id: '', label: 'Any dance'}].concat((options || []).slice(0, 16)).map(function (o, i) {
        return {id: o.id, label: o.label, key: i < 9 ? String(i + 1) : ''};
    });
}

// The compact caption (type say): who speaks, the current line, and the key hint.
function caption(interaction, name) {
    if (!interaction || interaction.type !== 'say' || !interaction.line) return null;
    var last = interaction.lineIndex + 1 >= interaction.lineCount;
    return {speaker: name || interaction.label, line: interaction.line, index: interaction.lineIndex, count: interaction.lineCount,
            progress: interaction.lineCount > 1 ? (interaction.lineIndex + 1) + ' / ' + interaction.lineCount : '',
            hint: INTERACT_KEY + ' · ' + (last ? 'close' : 'next')};
}

// A panel id (Director tab key or alias) -> {tab, view}, or null when the shell has no such panel.
function panelTarget(panel, tabKeys) {
    if (!panel) return null;
    var key = PANEL_ALIASES[panel] || panel, tab = (tabKeys || []).indexOf(key);
    if (tab < 0) return null;
    return {tab: tab, key: key, view: panel === 'characters' ? 'characters' : ''};
}

function toast(key, title, line, detail, tone) {
    return {key: key, kind: 'toast', category: 'objects', tone: tone || 'info', title: title, line: line, detail: detail || '',
            durationMs: TOAST_MS, count: 1};
}

// What the shell does for a new interaction: {kind: 'choose'|'say'|'panel'|'toast'|'none', ...}.
function interactionEffect(interaction, name, tabKeys) {
    if (!interaction) return {kind: 'none'};
    var who = name || 'Character';
    if (interaction.type === 'choose') return {kind: 'choose'};
    if (interaction.type === 'say') return {kind: 'say'};
    if (interaction.type === 'panel') {
        var target = panelTarget(interaction.panel, tabKeys);
        return target ? {kind: 'panel', tab: target.tab, view: target.view, objectId: interaction.objectId}
                      : {kind: 'end', objectId: interaction.objectId};
    }
    if (interaction.type === 'waypoint')
        return {kind: 'toast', toast: toast('npc:waypoint', who, 'Waypoint set', interaction.label)};
    if (interaction.type === 'guide')
        return {kind: 'toast', toast: toast('npc:guide', who, 'Follow ' + who, interaction.label)};
    return {kind: 'none'};
}

// ---- Feedback ----

function ruleText(rule) { return rule ? RULES[rule] || rule : ''; }

function errorToast(method, error, message) {
    var text = error && error.message ? error.message : String(message || '').replace(/^-?\d+:\s*/, '');
    var rule = error && error.rule ? error.rule : '';
    var title = /^paths\./.test(method) ? 'Route' : /^interaction\./.test(method) ? 'Interaction' : 'Character';
    return {key: 'npcs:error:' + method + ':' + rule, kind: 'toast', category: 'objects', tone: 'warning', title: title,
            line: text || 'Core refused the request.', detail: rule && rule !== 'budget' && rule !== 'walkable' ? 'Rule: ' + ruleText(rule) : '',
            durationMs: TOAST_MS, count: 1};
}

function resultText(method, params, result) {
    var p = params || {};
    if (method === 'npcs.spawn') return p.path ? 'Spawned on ' + refId(p.path) + '.' : 'Spawned in front of you.';
    if (method === 'npcs.bind') return p.path ? 'Now walking ' + refId(p.path) + '.' : 'Settings saved.';
    if (method === 'npcs.disable') return p.disabled ? 'Disabled.' : 'Enabled.';
    if (method === 'npcs.remove') return p.all ? 'Your characters in this world are removed.' : 'Removed.';
    if (method === 'paths.set') return 'Route saved.';
    if (method === 'paths.remove') return 'Route removed.';
    if (method === 'paths.draw') return 'Draw the route with tool 3, then leave tool 3 or press Done.';
    if (method === 'paths.finish') return result && result.id ? (result.bound ? 'Route saved; the character walks it.' : 'Route saved.') : 'Nothing was being drawn.';
    return null;
}

// runtime.notice codes for characters and routes -> a short toast (null: leave it to the notice list).
var NOTICES = {
    'npc.spawned': ['Character', 'info'], 'npc.removed': ['Character', 'info'], 'npc.disabled': ['Character', 'info'],
    'npc.enabled': ['Character', 'info'], 'npc.suspended': ['Character', 'warning'], 'npc.budget': ['Character', 'warning'],
    'path.unwalkable': ['Route', 'warning'], 'path.saved': ['Route', 'info'], 'path.removed': ['Route', 'info'],
    'interaction.refused': ['Interaction', 'warning'],
    'world.library.missing': ['Library', 'warning']};

function noticeToast(notice) {
    var spec = notice ? NOTICES[notice.code] : null;
    if (!spec) return null;
    return toast('npcs:notice:' + notice.code, spec[0], String(notice.message || '').slice(0, 160) || notice.code, '', spec[1]);
}
