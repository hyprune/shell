// RFC-0012 (IPC 0.21) quests, focus sessions, notifications and the hold ring delay.
// Pure helpers: tested with node in tests/test_ipc21.py.

var SLUG = /^[a-z0-9][a-z0-9-]{0,63}$/;
var MAX_STEPS = 16;
var TITLE_MAX = 64;
var HOLD_RING_DELAY_MS = 180;
var TOAST_LIMIT = 3;
var DURATIONS = {step: 3000, available: 3000, failed: 3000, completed: 5000, focus: 4000};

// ---- Quest references and list grouping ----

function refKey(ref) { return ref ? ref.source + '/' + ref.id : ''; }
function sameRef(a, b) { return !!a && !!b && a.source === b.source && a.id === b.id; }

var GROUPS = [{id: 'active', title: 'Active', states: ['active'], collapsed: false},
              {id: 'available', title: 'Available', states: ['available'], collapsed: false},
              {id: 'completed', title: 'Completed', states: ['completed'], collapsed: true},
              {id: 'closed', title: 'Failed or abandoned', states: ['failed', 'abandoned'], collapsed: true}];

// quests.list summaries -> groups in page order. Active: tracked first, then most recently
// updated; the other groups most recently updated first. Empty groups are kept (count 0).
function groupQuests(list) {
    var quests = Array.isArray(list) ? list : [];
    return GROUPS.map(function (g) {
        var items = quests.filter(function (q) { return g.states.indexOf(q.state) >= 0; });
        items.sort(function (a, b) {
            if (g.id === 'active' && !!a.tracked !== !!b.tracked) return a.tracked ? -1 : 1;
            var au = a.updatedAt || '', bu = b.updatedAt || '';
            if (au !== bu) return au < bu ? 1 : -1;
            return a.title < b.title ? -1 : a.title > b.title ? 1 : 0;
        });
        return {id: g.id, title: g.title, collapsed: g.collapsed, quests: items};
    });
}

// Flat rows for keyboard navigation: a header per group, its quests unless collapsed.
// `open` overrides the default collapse state per group id ({completed: true}).
function rows(groups, open) {
    var out = [];
    (groups || []).forEach(function (g) {
        var expanded = open && open[g.id] !== undefined ? !!open[g.id] : !g.collapsed;
        out.push({type: 'header', group: g.id, title: g.title, count: g.quests.length, expanded: expanded});
        if (expanded) g.quests.forEach(function (q) { out.push({type: 'quest', group: g.id, key: refKey(q.questRef), quest: q}); });
    });
    return out;
}

// Next row index for Up (-1) / Down (+1), clamped.
function move(rowList, index, delta) {
    if (!rowList || !rowList.length) return -1;
    return Math.max(0, Math.min(rowList.length - 1, (index < 0 ? (delta > 0 ? -1 : rowList.length) : index) + delta));
}

function progressText(pair) {
    return pair && pair.length === 2 ? pair[0] + ' / ' + pair[1] : '';
}

// ---- Quest details ----

// The current step (sequential) or the first open one.
function currentStep(detail) {
    if (!detail || !detail.steps) return null;
    return detail.steps.find(function (s) { return s.state === 'current'; }) || null;
}

function objectiveRequired(o) {
    if (o.type === 'focus') return o.sessions || o.count || 1;
    return o.count || 1;
}

// "1 / 2 sessions", "Done", "To do", "2 / 3".
function objectiveProgress(o) {
    if (!o) return '';
    var need = objectiveRequired(o), done = Math.min(o.done || 0, need);
    if (o.type === 'focus') return done + ' / ' + need + (need === 1 ? ' session' : ' sessions');
    if (need > 1) return done + ' / ' + need;
    if (o.type === 'reach') return done ? 'Reached' : 'Not yet';
    return done ? 'Done' : 'To do';
}

function objectiveDone(o) { return !!o && (o.done || 0) >= objectiveRequired(o); }

// Objectives a key acts on: Space marks the first open manual objective of the current
// step; F starts a session for its first open focus objective.
function firstObjective(detail, type) {
    var step = currentStep(detail);
    if (!step) return null;
    var o = (step.objectives || []).find(function (v) { return v.type === type && !objectiveDone(v); });
    return o ? {stepId: step.id, objectiveId: o.id, objective: o} : null;
}

// Which per-quest actions apply (Accept, Abandon, Resume, Track, Edit, Delete).
function questActions(detail) {
    if (!detail) return {};
    var s = detail.state;
    return {accept: s === 'available', abandon: s === 'active', resume: s === 'failed' || s === 'abandoned',
            track: s === 'active', edit: !!detail.personal, remove: !!detail.personal};
}

// ---- Targets: waypoints and the map ----

function zoneCentre(zone) {
    var b = zone && zone.bounds;
    if (!b) return null;
    return [(b.min[0] + b.max[0]) / 2, b.min[1] + 1.7, (b.min[2] + b.max[2]) / 2];
}

function targetEquals(a, b) {
    if (!a || !b) return false;
    var keys = ['zoneId', 'areaId', 'placeId', 'workspaceId'];
    for (var i = 0; i < keys.length; i++) if (a[keys[i]] !== undefined || b[keys[i]] !== undefined) return a[keys[i]] === b[keys[i]];
    return !!a.position && !!b.position && a.position.every(function (v, j) { return Math.abs(v - b.position[j]) < 0.01; });
}

// The marker core resolved for this quest step/objective (or the same target), if any.
function markerFor(markers, questKey, stepId, objectiveId, target) {
    var list = markers && markers.list ? markers.list : [];
    var withPos = list.filter(function (m) { return m.position; });
    var bySource = questKey ? withPos.filter(function (m) { return m.source && m.source.questId === questKey && (!stepId || m.source.stepId === stepId); }) : [];
    var exact = bySource.find(function (m) { return objectiveId && m.source.objectiveId === objectiveId; });
    return exact || bySource[0] || (target ? withPos.find(function (m) { return targetEquals(m.target, target); }) : null) || null;
}

// Where a quest target is in the loaded world: {position, label, zoneId?} or null.
// position/zone/place resolve directly; areas and workspaces through core's markers.
function resolveTarget(target, ctx) {
    ctx = ctx || {};
    var marker = markerFor(ctx.markers, ctx.questKey, ctx.stepId, ctx.objectiveId, target);
    if (target && target.position && (!target.worldId || !ctx.worldId || target.worldId === ctx.worldId))
        return {position: target.position, label: ctx.label || 'Quest target'};
    if (target && target.zoneId) {
        var zone = (ctx.zones || []).find(function (z) { return z.id === target.zoneId; });
        if (zone) return {position: zoneCentre(zone), zoneId: zone.id, label: zone.name || ctx.label || zone.id};
    }
    if (target && target.placeId) {
        var place = (ctx.places || []).find(function (p) { return p.id === target.placeId; });
        if (place) return {position: place.position, label: place.name || ctx.label || place.id};
    }
    if (marker) return {position: marker.position, label: marker.label || ctx.label || 'Quest target'};
    return null;
}

// waypoint.set params for a resolved target (zones keep their zone target).
function waypointParams(resolved, id, label) {
    if (!resolved) return null;
    var name = String(label || resolved.label || 'Quest target').slice(0, 256) || 'Quest target';
    var wid = String(id || 'quest').slice(0, 128);
    return {id: wid, label: name, target: resolved.zoneId ? {zoneId: resolved.zoneId} : {position: resolved.position}};
}

function targetText(target, ctx) {
    if (!target) return '';
    ctx = ctx || {};
    if (target.workspaceId !== undefined) return 'Workspace ' + target.workspaceId;
    if (target.areaId) return 'Area ' + target.areaId.replace(/-/g, ' ');
    if (target.placeId) {
        var p = (ctx.places || []).find(function (v) { return v.id === target.placeId; });
        return p && p.name ? p.name : target.placeId.replace(/-/g, ' ');
    }
    if (target.zoneId) {
        var z = (ctx.zones || []).find(function (v) { return v.id === target.zoneId; });
        return z && z.name ? z.name : target.zoneId.replace(/-/g, ' ');
    }
    if (target.position) return target.position.map(function (v) { return Number(v).toFixed(1); }).join(' / ') + ' m';
    return '';
}

// ---- Personal quest form ----

function slugify(text, fallback) {
    var s = String(text || '').toLowerCase();
    if (typeof s.normalize === 'function') s = s.normalize('NFKD').replace(/[\u0300-\u036f]/g, '');
    s = s.replace(/[^a-z0-9]+/g, '-').replace(/^-+/, '').slice(0, 64).replace(/-+$/, '');
    return SLUG.test(s) ? s : (fallback || 'step');
}

function uniqueSlug(base, used) {
    var id = base, n = 2;
    while (used.indexOf(id) >= 0) { var suffix = '-' + n++; id = base.slice(0, 64 - suffix.length).replace(/-+$/, '') + suffix; }
    used.push(id);
    return id;
}

function cleanTitle(text) {
    return String(text || '').replace(/[\u0000-\u001f\u007f-\u009f]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, TITLE_MAX).trim();
}

// "One step per line": trimmed, blank lines and list bullets dropped, at most 16.
function parseSteps(text) {
    return String(text || '').split(/\r?\n/).map(function (line) {
        return cleanTitle(line.replace(/^\s*(?:[-*\u2022]|\d+[.)])\s+/, ''));
    }).filter(function (line) { return line.length > 0; }).slice(0, MAX_STEPS);
}

// The form's quest-wide target: kind none/workspace/area/place plus its value.
function formTarget(kind, value) {
    if (kind === 'workspace') {
        var n = Math.floor(Number(value));
        return n >= 1 && n <= 2147483647 ? {workspaceId: n} : null;
    }
    if ((kind === 'area' || kind === 'place') && value) return kind === 'area' ? {areaId: String(value)} : {placeId: String(value)};
    return null;
}

// Form -> PersonalQuestInput. form: {title, summary, steps (text), targetKind, targetValue,
// sessions: {stepTitle: n}}. `previous` (QuestDetail, when editing) keeps the step ids of
// steps whose title is unchanged so their progress survives the update.
function questInput(form, previous) {
    var title = cleanTitle(form.title);
    var titles = parseSteps(form.steps);
    if (!titles.length && title) titles = [title];
    var target = formTarget(form.targetKind, form.targetValue);
    var used = [], prevSteps = previous && previous.steps ? previous.steps.slice() : [];
    var steps = titles.map(function (t, i) {
        var match = prevSteps.findIndex(function (s) { return s.title === t && used.indexOf(s.id) < 0; });
        var id = match >= 0 ? prevSteps[match].id : uniqueSlug(slugify(t, 'step-' + (i + 1)), used);
        if (match >= 0) used.push(id);
        var step = {id: id, title: t};
        if (target) step.target = target;
        var n = Math.floor(Number((form.sessions || {})[t] || 0));
        if (n > 0) step.objectives = [{id: 'focus', type: 'focus', sessions: Math.min(12, n)}];
        return step;
    });
    var quest = {title: title, steps: steps};
    var summary = String(form.summary || '').replace(/[\u0000-\u0009\u000b-\u001f\u007f]/g, ' ').trim().slice(0, 1000);
    if (summary) quest.summary = summary;
    return quest;
}

// Validation message for the form, or '' when it can be saved.
function formError(form) {
    if (!cleanTitle(form.title)) return 'Give the quest a title.';
    if (String(form.steps || '').split(/\r?\n/).filter(function (l) { return l.trim(); }).length > MAX_STEPS) return 'At most 16 steps; extra lines are dropped.';
    if (form.targetKind === 'workspace' && !formTarget('workspace', form.targetValue)) return 'Choose a workspace number.';
    if ((form.targetKind === 'area' || form.targetKind === 'place') && !form.targetValue) return 'Choose a ' + form.targetKind + '.';
    return '';
}

// QuestDetail -> form (Edit). The quest-wide target is the first step target.
function formFromDetail(detail) {
    var form = {title: '', summary: '', steps: '', targetKind: 'none', targetValue: '', sessions: {}};
    if (!detail) return form;
    form.title = detail.title || '';
    form.summary = detail.summary || '';
    form.steps = (detail.steps || []).map(function (s) { return s.title; }).join('\n');
    var t = (detail.steps || []).map(function (s) { return s.target; }).find(function (v) { return !!v; });
    if (t && t.workspaceId !== undefined) { form.targetKind = 'workspace'; form.targetValue = String(t.workspaceId); }
    else if (t && t.areaId) { form.targetKind = 'area'; form.targetValue = t.areaId; }
    else if (t && t.placeId) { form.targetKind = 'place'; form.targetValue = t.placeId; }
    (detail.steps || []).forEach(function (s) {
        var f = (s.objectives || []).find(function (o) { return o.type === 'focus'; });
        if (f) form.sessions[s.title] = f.sessions || 1;
    });
    return form;
}

// ---- Focus sessions ----

function countdown(ms) {
    var total = Math.max(0, Math.ceil((Number(ms) || 0) / 1000));
    var h = Math.floor(total / 3600), m = Math.floor(total % 3600 / 60), s = total % 60;
    function pad(n) { return (n < 10 ? '0' : '') + n; }
    return (h ? h + ':' : '') + pad(m) + ':' + pad(s);
}

// Remaining ms of the running phase at local monotonic time `nowMono`; paused/ready
// phases show the published remainder.
function remaining(focus, nowMono) {
    if (!focus || focus.state === 'idle') return 0;
    if (focus.phaseEndsAtMs !== null && focus.phaseEndsAtMs !== undefined && nowMono !== null && nowMono !== undefined)
        return Math.max(0, focus.phaseEndsAtMs - nowMono);
    return Math.max(0, focus.remainingMs || 0);
}

function phaseLabel(focus) {
    if (!focus) return '';
    switch (focus.state) {
    case 'work': return 'Work';
    case 'break': return focus.breakKind === 'long' ? 'Long break' : 'Short break';
    case 'ready': return 'Ready';
    case 'paused': return 'Paused';
    default: return '';
    }
}

// Phase used for colour: a paused break keeps the break colour.
function phaseTone(focus) {
    if (!focus) return 'idle';
    return focus.state === 'paused' ? (focus.pausedState || 'work') : focus.state;
}

// Ring fill (elapsed share of the phase) and the quiet credit arc (work only).
function ringProgress(focus, remainingMs) {
    if (!focus || !focus.phaseMs) return 0;
    return Math.max(0, Math.min(1, 1 - remainingMs / focus.phaseMs));
}
function creditProgress(focus) {
    if (!focus || !focus.phaseMs || phaseTone(focus) !== 'work') return 0;
    return Math.max(0, Math.min(1, (focus.creditedMs || 0) / focus.phaseMs));
}

// Cycle dots: 'done', 'current' or 'todo' per work interval. Core publishes breakKind
// during a break (also paused, or ready before it): then the current interval is done.
function cycleDots(focus) {
    if (!focus || !focus.cycles) return [];
    var out = [];
    var inBreak = !!focus.breakKind;
    for (var i = 1; i <= focus.cycles; i++)
        out.push(i < focus.cycle || (i === focus.cycle && inBreak) ? 'done' : i === focus.cycle ? 'current' : 'todo');
    return out;
}

// Chip visibility. World view: shown unless idle. Desktop (world not active): only with
// guidance focus.desktop_chip.
function chipVisible(focus, worldActive, guidanceConfig) {
    if (!focus || focus.state === 'idle') return false;
    return worldActive || !!(guidanceConfig && guidanceConfig['focus.desktop_chip']);
}

// ---- Notifications ----

function minutes(ms) { return Math.round((ms || 0) / 60000); }

// quest.progress / focus.phase params -> a toast, or null for in-place updates.
// kind 'toast' (under the tracker) or 'banner' (top centre).
function toastFor(method, p, focus) {
    if (method === 'quest.progress') {
        var key = 'quest:' + refKey(p.questRef) + ':' + p.kind + ':' + (p.stepId || '');
        if (p.kind === 'step') return {key: key, kind: 'toast', category: 'step', title: p.title,
                                       line: '✓ ' + (p.stepTitle || 'Step done'),
                                       detail: p.nextStepTitle ? 'Next: ' + p.nextStepTitle : '', durationMs: DURATIONS.step, count: 1};
        if (p.kind === 'completed') return {key: key, kind: 'banner', category: 'completed', title: p.title, line: 'Quest complete',
                                            detail: '', durationMs: DURATIONS.completed, count: 1};
        if (p.kind === 'available') return {key: key, kind: 'toast', category: 'available', title: p.title, line: 'New quest available',
                                            detail: 'Track it in Quests', durationMs: DURATIONS.available, count: 1};
        if (p.kind === 'failed') return {key: key, kind: 'toast', category: 'failed', title: p.title, line: 'Due time passed',
                                         detail: 'Resume it any time in Quests', durationMs: DURATIONS.failed, count: 1};
        return null; // objective progress: the tracker updates in place
    }
    if (method === 'focus.phase') {
        var t = {key: 'focus:' + p.phase, kind: 'toast', category: 'focus', title: 'Focus session', line: '', detail: '',
                 durationMs: DURATIONS.focus, count: 1};
        var of = p.cycle + ' of ' + p.cycles;
        if (p.phase === 'work') { t.line = 'Work · interval ' + of; }
        else if (p.phase === 'break') {
            var mins = focus && focus.state === 'break' && focus.phaseMs ? minutes(focus.phaseMs) : 0;
            t.line = (p.breakKind === 'long' ? 'Long break' : 'Break') + (mins ? ' · ' + mins + ' min' : '');
            t.detail = p.suggestion && p.suggestion.label ? 'Stretch, or walk to ' + p.suggestion.label + '.' : 'Stretch, look away, take a breath.';
        }
        else if (p.phase === 'ready') {
            t.line = p.breakKind ? (p.breakKind === 'long' ? 'Long break' : 'Break') + ' when you are ready' : 'Ready for interval ' + of;
            t.detail = 'Start it from Quests when you like.';
        }
        else if (p.phase === 'paused') { t.line = 'Paused'; }
        else if (p.phase === 'ended') {
            t.line = p.outcome === 'completed' ? 'Session complete · ' + p.cycles + (p.cycles === 1 ? ' interval' : ' intervals')
                                               : 'Session ended · interval ' + of;
            t.detail = 'Last interval: ' + minutes(p.creditedMs) + ' min credited';
        }
        else return null;
        return t;
    }
    return null;
}

// What to do with a toast: 'show', 'defer' (calm mode: until the next break) or 'drop'.
// quests.notifications: all, important (completions and focus phases), off (nothing).
function route(toast, notifications, calm) {
    if (!toast || notifications === 'off') return 'drop';
    if (notifications === 'important' && toast.category !== 'completed' && toast.category !== 'focus') return 'drop';
    if (calm && toast.category !== 'focus') return 'defer';
    return 'show';
}

// Queue at most three, merging repeats (same key: newest text, count + 1, kept in place).
// The head (index 0) is the one on screen; overflow drops the oldest waiting toast.
function enqueue(queue, toast, now) {
    var q = (queue || []).slice();
    var at = q.findIndex(function (t) { return t.key === toast.key; });
    if (at >= 0) {
        var merged = Object.assign({}, toast, {count: (q[at].count || 1) + 1, shownAt: q[at].shownAt});
        if (at === 0) merged.shownAt = now; // the visible toast restarts its time
        q[at] = merged;
        return q;
    }
    q.push(Object.assign({}, toast, {count: toast.count || 1, shownAt: q.length ? null : now}));
    while (q.length > TOAST_LIMIT) q.splice(1, 1);
    return q;
}

// Drop expired heads; the next toast starts its time now.
function advance(queue, now) {
    var q = (queue || []).slice();
    while (q.length && q[0].shownAt !== null && now - q[0].shownAt >= q[0].durationMs) {
        q.shift();
        if (q.length) q[0] = Object.assign({}, q[0], {shownAt: now});
    }
    return q;
}

// ---- Hold ring delay ----

// A TAB tap must never flash the Director hold ring: nothing shows until `delayMs` after
// the hold started, then the ring fills the remaining durationMs - delayMs.
// hold: {durationMs, remainingMs} as the bridge published it; sinceMs: local time since.
function holdView(hold, sinceMs, delayMs) {
    var delay = delayMs === undefined ? HOLD_RING_DELAY_MS : delayMs;
    if (!hold || !(hold.durationMs > 0)) return {visible: false, progress: 0, waitMs: 0, fillMs: 0};
    var elapsed = hold.durationMs - hold.remainingMs + Math.max(0, sinceMs || 0);
    var span = Math.max(1, hold.durationMs - delay);
    if (elapsed < delay) return {visible: false, progress: 0, waitMs: delay - elapsed, fillMs: span};
    var progress = Math.max(0, Math.min(1, (elapsed - delay) / span));
    return {visible: true, progress: progress, waitMs: 0, fillMs: Math.max(0, hold.durationMs - elapsed)};
}

// ---- Errors ----

// Core refusals of quest, focus and guidance requests ("<code>: <message>"), in plain words.
function errorText(method, message) {
    var m = /^(-?\d+):\s*(.*)$/.exec(String(message || ''));
    var code = m ? Number(m[1]) : 0, detail = m ? m[2] : String(message || '');
    if (code === -32003) return 'That quest or step no longer exists.';
    if (code === -32007) return 'Only personal quests can be edited or deleted.';
    if (code === -32008) return 'Limit reached (at most 64 personal quests).';
    if (code === -32004) {
        if (method === 'focus.start') return 'A focus session is already running.';
        if (/^focus\./.test(method)) return 'No focus session to ' + method.split('.')[1] + '.';
        if (method === 'quests.mark') return 'Only the current step can be marked done.';
        if (method === 'quests.accept') return 'That quest is already accepted or complete.';
        if (method === 'quests.resume') return 'That quest is already active.';
        return 'That change is not possible right now.';
    }
    if (code === -32602) return 'Core refused the request' + (detail ? ': ' + detail : '.');
    return detail || 'The request was refused.';
}

// ---- Settings > Guidance (guidance.get / guidance.set, flat dotted keys) ----

var GUIDANCE = [
    {group: 'MARKERS', key: 'markers.reveal_ms', name: 'Reveal time', unit: 's', scale: 0.001, step: 500, note: 'How long a TAB tap shows the markers.'},
    {group: 'MARKERS', key: 'markers.reveal_mode', name: 'TAB tap', labels: {timer: 'Show for a while', toggle: 'Show until next tap'}},
    {group: 'MARKERS', key: 'markers.max_revealed', name: 'Markers at once', step: 1},
    {group: 'MARKERS', key: 'markers.labels', name: 'Labels at once', step: 1},
    {group: 'MARKERS', key: 'markers.persistent', name: 'Without a tap', labels: {off: 'Waypoint only', edge: 'Tracked step', always: 'With label'},
     note: 'Tracked step: a small marker or edge arrow for the tracked quest’s current step.'},
    {group: 'MARKERS', key: 'markers.core_draw', name: 'Core draws world markers', note: 'Off only for shells that draw markers themselves.'},
    {group: 'QUESTS', key: 'quests.notifications', name: 'Notifications', labels: {all: 'All', important: 'Important', off: 'Off'},
     note: 'Important: quest completions and focus phases only.'},
    {group: 'FOCUS SESSIONS', key: 'focus.work_min', name: 'Work interval', unit: 'min', step: 1},
    {group: 'FOCUS SESSIONS', key: 'focus.short_break_min', name: 'Short break', unit: 'min', step: 1},
    {group: 'FOCUS SESSIONS', key: 'focus.long_break_min', name: 'Long break', unit: 'min', step: 1},
    {group: 'FOCUS SESSIONS', key: 'focus.long_break_every', name: 'Long break every', unit: 'intervals', step: 1},
    {group: 'FOCUS SESSIONS', key: 'focus.cycles', name: 'Intervals per session', step: 1},
    {group: 'FOCUS SESSIONS', key: 'focus.auto_start_breaks', name: 'Start breaks automatically'},
    {group: 'FOCUS SESSIONS', key: 'focus.auto_start_work', name: 'Start work after a break automatically', note: 'Off: the timer waits as Ready until you start the next interval.'},
    {group: 'FOCUS SESSIONS', key: 'focus.count_mode', name: 'Time that counts', labels: {focus: 'While working in the target', wall: 'All of the interval'},
     note: 'While working: keyboard focus on the chosen window or workspace, with recent input. All: suits paper, calls and thinking.'},
    {group: 'FOCUS SESSIONS', key: 'focus.idle_s', name: 'Idle after', unit: 's', step: 10},
    {group: 'FOCUS SESSIONS', key: 'focus.grace_s', name: 'Short look-ups still count', unit: 's', step: 5},
    {group: 'FOCUS SESSIONS', key: 'focus.calm', name: 'Calm mode in work intervals', note: 'Only the tracked step on TAB; quest notices wait for the break.'},
    {group: 'FOCUS SESSIONS', key: 'focus.calm_npc_distance', name: 'Characters keep away', unit: 'm', step: 1},
    {group: 'FOCUS SESSIONS', key: 'focus.desktop_chip', name: 'Timer on the desktop', note: 'Shows the focus timer outside the world view too.'},
    {group: 'FOCUS SESSIONS', key: 'focus.history_days', name: 'Keep history', unit: 'days', step: 1, note: '0 keeps no history. Times and app classes only, never titles.'}
];

// 'number', 'enum' or 'bool' from the guidance.get answer.
function guidanceType(settings, key) {
    if (settings && settings.ranges && settings.ranges[key]) return 'number';
    if (settings && settings.options && settings.options[key]) return 'enum';
    var v = settings && settings.config ? settings.config[key] : undefined;
    return typeof v === 'boolean' ? 'bool' : typeof v === 'number' ? 'number' : typeof v === 'string' ? 'enum' : '';
}

// Rows for keys the core reports (unknown keys are skipped).
function guidanceRows(settings) {
    if (!settings || !settings.config) return [];
    return GUIDANCE.filter(function (g) { return settings.config[g.key] !== undefined; }).map(function (g, i, all) {
        return Object.assign({}, g, {type: guidanceType(settings, g.key), first: i === 0 || all[i - 1].group !== g.group});
    });
}

function guidanceValue(settings, key, value) {
    var g = GUIDANCE.find(function (v) { return v.key === key; }) || {};
    var shown = g.scale ? value * g.scale : value;
    return (Math.round(shown * 10) / 10) + (g.unit ? ' ' + g.unit : '');
}

// One guidance.set patch: numbers clamped to core's range and rounded to the slider step.
function guidancePatch(settings, key, value) {
    var out = {};
    if (value === null) { out[key] = null; return out; }
    var r = settings && settings.ranges ? settings.ranges[key] : null;
    if (r) {
        var g = GUIDANCE.find(function (v) { return v.key === key; }) || {};
        var step = g.step || 1;
        value = Math.round(Number(value) / step) * step;
        value = Math.min(r[1], Math.max(r[0], value));
    }
    out[key] = value;
    return out;
}
