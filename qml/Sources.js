// Machine data sources (RFC-0013 draft; IPC 0.24 adds catalog `machine` and state `live`):
// the Data source section of Director > Objects > Placed. Pure helpers, tested with node in
// tests/test_sources.py. The bridge edits sources.json and talks to the source helper
// (bridge/sources.py); nothing here runs a command.

var SOURCES_CLIENT = 'com.hyprune.sources';
var SLUG = /^[a-z][a-z0-9-]*$/;
// Used until the helper reports status.limits.
var DEFAULT_LIMITS = {command: {intervalS: [5, 86400], devIntervalS: 1, timeoutS: [1, 60]}};
var DEFAULT_INTERVAL = 60;
var CONDITIONS = {fresh: 'fresh', stale: 'stale', missing: 'missing', error: 'error'};
var SAFE = /^[A-Za-z0-9_@%+=:,.\/-]+$/;

// POSIX shell quoting for display: plain words stay as they are, anything else in single
// quotes (a ' inside becomes '\''). The helper runs argv without a shell; this only shows it.
function quote(arg) {
    var s = String(arg);
    return s !== '' && SAFE.test(s) ? s : "'" + s.replace(/'/g, "'\\''") + "'";
}

function argvLine(argv) { return (argv || []).map(quote).join(' '); }

// The panel's "Runs: …" line ('' without a command).
function runsText(argv) { return argv && argv.length ? 'Runs: ' + argvLine(argv) : ''; }

// Arguments, one per line: each line is trimmed and empty lines are skipped.
function parseArgs(text) {
    return String(text || '').split(/\r?\n/).map(function (l) { return l.trim(); }).filter(function (l) { return l !== ''; });
}

function argsText(args) { return (args || []).join('\n'); }

// [script, ...args], or [] without a script.
function buildArgv(script, argsTextValue) {
    var s = String(script || '').trim();
    return s ? [s].concat(parseArgs(argsTextValue)) : [];
}

// {min, max} seconds for a command interval: the helper's limits (devIntervalS when the
// config allows fast prototype intervals), else 5–86400.
function intervalBounds(limits, dev) {
    var command = limits && limits.command ? limits.command : DEFAULT_LIMITS.command;
    var range = command.intervalS && command.intervalS.length === 2 ? command.intervalS : DEFAULT_LIMITS.command.intervalS;
    var lo = range[0];
    if (dev) lo = Math.min(lo, typeof command.devIntervalS === 'number' ? command.devIntervalS : DEFAULT_LIMITS.command.devIntervalS);
    return {min: lo, max: range[1]};
}

// Whole seconds within the bounds; text that is not a number gives the fallback (clamped).
function clampInterval(value, bounds, fallback) {
    var b = bounds || intervalBounds(null, false);
    var text = value === undefined || value === null ? '' : String(value).trim();
    var n = typeof value === 'number' ? value : text === '' ? NaN : Number(text);
    if (!isFinite(n)) n = typeof fallback === 'number' ? fallback : DEFAULT_INTERVAL;
    return Math.max(b.min, Math.min(b.max, Math.round(n)));
}

function intervalText(seconds) {
    if (typeof seconds !== 'number') return '';
    if (seconds >= 3600 && seconds % 3600 === 0) return (seconds / 3600) + ' h';
    if (seconds >= 60 && seconds % 60 === 0) return (seconds / 60) + ' min';
    return seconds + ' s';
}

// The machine's inputs with repeats expanded (health.1 … health.N), in declaration order.
// machine: the catalog entry's `machine` ({primary, inputs}) or null.
function expandInputs(machine) {
    var out = [];
    (machine && machine.inputs ? machine.inputs : []).forEach(function (input) {
        var n = typeof input.repeat === 'number' && input.repeat >= 2 ? Math.min(16, input.repeat) : 0;
        if (!n) { out.push(Object.assign({key: input.id, primary: !!machine && machine.primary === input.id}, input)); return; }
        for (var i = 1; i <= n; i++)
            out.push(Object.assign({}, input, {key: input.id + '.' + i, index: i, label: (input.label || input.id) + ' ' + i, primary: false}));
    });
    return out;
}

// What an input accepts, in a few words: "number 0–100", "ok | warn | fail", "text ≤ 12".
function rangeText(input) {
    if (!input) return '';
    var t = input.type;
    function span() {
        var lo = typeof input.min === 'number', hi = typeof input.max === 'number';
        return lo && hi ? ' ' + input.min + '–' + input.max : lo ? ' ≥ ' + input.min : hi ? ' ≤ ' + input.max : '';
    }
    if (t === 'enum') return (input.values || []).join(' | ');
    if (t === 'int' || t === 'number') return t + span();
    if (t === 'text') return typeof input.maxLength === 'number' ? 'text ≤ ' + input.maxLength : 'text';
    return t || '';
}

function isScalar(v) { return v === null || typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean'; }

// Problems with one value for one input ([] when it fits).
function checkValue(input, value) {
    var t = input.type, problems = [];
    if (!isScalar(value) || value === null) return ['not a single value'];
    if (t === 'enum') {
        if (typeof value !== 'string') problems.push('expected text, got ' + typeof value);
        else if ((input.values || []).indexOf(value) < 0) problems.push('not one of ' + (input.values || []).join(', '));
    } else if (t === 'int' || t === 'number') {
        if (typeof value !== 'number' || !isFinite(value)) problems.push('expected a number, got ' + (typeof value === 'string' ? 'text' : typeof value));
        else {
            if (t === 'int' && Math.round(value) !== value) problems.push('expected a whole number');
            if (typeof input.min === 'number' && value < input.min) problems.push('below ' + input.min);
            if (typeof input.max === 'number' && value > input.max) problems.push('above ' + input.max);
        }
    } else if (t === 'bool') {
        if (typeof value !== 'boolean') problems.push('expected true or false');
    } else if (t === 'text') {
        if (typeof value !== 'string' && typeof value !== 'number') problems.push('expected text');
        else if (typeof input.maxLength === 'number' && String(value).length > input.maxLength) problems.push('longer than ' + input.maxLength + ' (cut)');
    }
    return problems;
}

function valueText(value) {
    if (value === undefined) return '—';
    if (typeof value === 'string') return value;
    return JSON.stringify(value);
}

// A helper `test` result checked against the machine's inputs: one row per input (value,
// level ok | warning | error, problems), the keys no input reads, the reserved keys and the
// inputs with no key. machine null (IPC 0.23): every key is listed, nothing is checked.
function validateTest(result, machine) {
    var values = result && result.values && typeof result.values === 'object' ? result.values : {};
    var inputs = expandInputs(machine), known = {}, reserved = {}, unknown = [], missing = [];
    inputs.forEach(function (i) { known[i.key] = true; });
    Object.keys(values).forEach(function (k) {
        if (k.charAt(0) === '_') reserved[k] = values[k];
        else if (machine && !known[k]) unknown.push(k);
    });
    var rows = inputs.map(function (input) {
        var has = Object.prototype.hasOwnProperty.call(values, input.key);
        if (!has) {
            missing.push(input.key);
            return {key: input.key, label: input.label || input.key, value: '—', present: false, level: 'warning',
                    problems: ['missing' + (input.default !== undefined ? ': shows ' + valueText(input.default) : '')]};
        }
        var problems = checkValue(input, values[input.key]);
        var cut = problems.length === 1 && / \(cut\)$/.test(problems[0]);
        return {key: input.key, label: input.label || input.key, value: valueText(values[input.key]), present: true,
                level: !problems.length ? 'ok' : cut ? 'warning' : 'error', problems: problems};
    });
    if (!machine) rows = Object.keys(values).filter(function (k) { return k.charAt(0) !== '_'; }).map(function (k) {
        return {key: k, label: k, value: valueText(values[k]), present: true, level: 'ok', problems: []};
    });
    var errors = rows.filter(function (r) { return r.level === 'error'; }).length;
    var failed = !!(result && (result.error || (typeof result.exitCode === 'number' && result.exitCode !== 0)));
    var parts = [];
    if (failed) parts.push(result.error || 'exit code ' + result.exitCode);
    if (machine) {
        parts.push((rows.length - missing.length - errors) + ' of ' + rows.length + ' inputs fit');
        if (errors) parts.push(errors + (errors === 1 ? ' mismatch' : ' mismatches'));
        if (missing.length) parts.push(missing.length + ' missing');
        if (unknown.length) parts.push(unknown.length + (unknown.length === 1 ? ' unknown key' : ' unknown keys'));
    } else parts.push(rows.length + (rows.length === 1 ? ' value' : ' values'));
    return {ok: !failed && !errors && !unknown.length, failed: failed, rows: rows, unknown: unknown, missing: missing,
            reserved: reserved, summary: parts.join(' · ')};
}

// The printed JSON as the panel shows it: stdout re-indented when it parses, else as printed.
function printedText(result) {
    if (!result) return '';
    var out = String(result.stdout || '');
    try { return JSON.stringify(JSON.parse(out), null, 2); } catch (e) { return out.replace(/\s+$/, ''); }
}

// The state `live` entry for an instance (null before 0.24 or when it is not bound).
function liveFor(live, instanceId) {
    var list = live && live.instances ? live.instances : [];
    for (var i = 0; i < list.length; i++) if (list[i].id === instanceId) return list[i];
    return null;
}

function defaultSource(instanceId) { return SOURCES_CLIENT + '.' + instanceId; }

// The source the instance reads: live's common source; '' when its inputs read several.
function sourceId(instanceId, liveEntry) {
    if (liveEntry) return liveEntry.source || '';
    return instanceId ? defaultSource(instanceId) : '';
}

// The sources.json id (helper status key) behind a source id, '' when it is not a helper source.
function helperSlug(source) {
    var prefix = SOURCES_CLIENT + '.';
    return typeof source === 'string' && source.indexOf(prefix) === 0 && SLUG.test(source.slice(prefix.length)) ? source.slice(prefix.length) : '';
}

// "now", "4 s", "3 min", "2 h", "5 d" since a wall-clock Unix ms ('' without one).
function ageText(at, now) {
    if (typeof at !== 'number') return '';
    var s = Math.max(0, Math.round(((typeof now === 'number' ? now : Date.now()) - at) / 1000));
    if (s < 1) return 'now';
    if (s < 60) return s + ' s';
    if (s < 3600) return Math.floor(s / 60) + ' min';
    if (s < 86400) return Math.floor(s / 3600) + ' h';
    return Math.floor(s / 86400) + ' d';
}

// One row per input for the live list: the declaration (label, range, explain) and core's
// live value (value, raw, condition, age). Without declarations (IPC 0.23) only live inputs.
function liveRows(machine, liveEntry, now) {
    var live = liveEntry && liveEntry.inputs ? liveEntry.inputs : {};
    var inputs = machine ? expandInputs(machine) : Object.keys(live).map(function (k) { return {key: k, id: k, label: k}; });
    return inputs.map(function (input) {
        var v = live[input.key] || null;
        var condition = v ? v.condition : liveEntry ? 'missing' : '';
        var raw = v && v.raw !== undefined && JSON.stringify(v.raw) !== JSON.stringify(v.value) ? valueText(v.raw) : '';
        return {key: input.key, label: input.label || input.key, type: input.type || '', range: rangeText(input), explain: input.explain || '',
                primary: !!input.primary, value: v ? valueText(v.value) : '—', raw: raw, condition: condition || '',
                age: v ? ageText(v.publishedAt, now) : '', source: v ? v.source || '' : '', sourceKey: v ? v.key || '' : '',
                level: condition === 'fresh' ? 'ok' : condition === 'error' ? 'warning' : 'muted'};
    });
}

// The helper as the panel names it, from the last status answer.
// status: {ok, helper: 'ok'|'missing'|'error', status?, error?} or null before the first.
function helperState(status) {
    if (!status) return {state: 'unknown', text: 'Asking the source helper…', canTest: false, canRestart: false};
    if (!status.ok) {
        if (status.helper === 'missing') return {state: 'missing', canTest: false, canRestart: false,
            text: 'The source helper is not running. Save still writes sources.json; the helper reads it when it starts.'};
        return {state: 'error', canTest: false, canRestart: false, text: 'The source helper is not answering: ' + (status.error || 'unknown error')};
    }
    var s = status.status || {};
    if (!s.connected) return {state: 'disconnected', canTest: true, canRestart: true,
        text: 'The source helper is not connected to core; values are not published. Restart helper reconnects it.'};
    var n = s.sources ? Object.keys(s.sources).length : 0;
    return {state: 'ok', canTest: true, canRestart: true, text: 'Source helper connected · ' + n + (n === 1 ? ' source' : ' sources')};
}

// The helper's status entry for a sources.json id (null when the config has none).
function helperSource(status, slug) {
    var sources = status && status.ok && status.status && status.status.sources ? status.status.sources : null;
    return sources && slug && sources[slug] ? sources[slug] : null;
}

function valuesText(values) {
    var keys = Object.keys(values || {}).filter(function (k) { return k.charAt(0) !== '_'; });
    return keys.slice(0, 8).map(function (k) { return k + ' ' + valueText(values[k]); }).join('  ·  ') + (keys.length > 8 ? '  ·  +' + (keys.length - 8) : '');
}

// The helper's last run of a source in two lines: {line, values, error, level}.
function lastRunText(source, now) {
    if (!source) return null;
    var run = source.lastRun;
    var next = typeof source.nextRunAt !== 'number' ? '' : source.nextRunAt - now < 1000 ? 'due now' : 'next in ' + ageText(now, source.nextRunAt);
    if (!run) return {line: [source.running ? 'Running now' : 'Not run yet', next].filter(function (v) { return v; }).join(' · '), values: '', error: '', level: 'muted'};
    var parts = [(run.ok ? 'Last run ' : 'Last run failed ') + ageText(run.at, now) + (ageText(run.at, now) === 'now' ? '' : ' ago')];
    if (typeof run.exitCode === 'number') parts.push('exit ' + run.exitCode);
    if (typeof run.durationMs === 'number') parts.push(run.durationMs + ' ms');
    if (source.running) parts.push('running');
    else if (next) parts.push(next);
    if (source.resets) parts.push(source.resets + (source.resets === 1 ? ' reset' : ' resets'));
    return {line: parts.join(' · '), values: valuesText(run.values), error: run.error || '', level: run.ok ? 'ok' : 'warning'};
}

// The editor's starting values from a sources.json entry (null: a new command source).
// {script, args, intervalS, kind, editable, note}
function draftFrom(entry, bounds) {
    if (!entry) return {script: '', args: '', intervalS: clampInterval(DEFAULT_INTERVAL, bounds), kind: 'command', editable: true, note: '', exists: false};
    var kind = entry.kind || 'command';
    if (kind !== 'command') return {script: '', args: '', intervalS: clampInterval(entry.intervalS, bounds), kind: kind, editable: false, exists: true,
                                    note: 'This is a ' + kind + ' source; edit it in sources.json.'};
    var argv = Array.isArray(entry.argv) ? entry.argv : [];
    return {script: argv.length ? String(argv[0]) : '', args: argsText(argv.slice(1)), intervalS: clampInterval(entry.intervalS, bounds),
            kind: kind, editable: true, note: '', exists: true};
}

// Why Save or Test can't go yet ('' when they can).
function draftError(argv, intervalText, bounds) {
    if (!argv || !argv.length) return 'Choose a command first.';
    var n = Number(String(intervalText).trim());
    if (String(intervalText).trim() === '' || !isFinite(n)) return 'Enter the interval in seconds.';
    if (n < bounds.min || n > bounds.max) return 'The interval is ' + bounds.min + '–' + bounds.max + ' s.';
    return '';
}

// The browser's rows: a parent row first (when there is one), then folders and files.
function browseRows(listing) {
    if (!listing || !listing.ok) return [];
    var rows = listing.parent ? [{name: '..', path: listing.parent, dir: true, executable: false, parent: true}] : [];
    var base = listing.path === '/' ? '' : listing.path;
    return rows.concat((listing.entries || []).map(function (e) {
        return {name: e.name, path: base + '/' + e.name, dir: !!e.dir, executable: !!e.executable, parent: false};
    }));
}

// Feedback for a finished sources request: {level, text}.
function resultText(reply) {
    if (!reply) return null;
    var reloadNote = reply.reload && !reply.reload.ok ? ' The helper will read it when it runs.' : '';
    if (!reply.ok) return {level: 'warning', text: reply.error || 'The request failed.'};
    if (reply.op === 'save') return {level: 'info', text: 'Saved to ' + reply.path + '.' + reloadNote};
    if (reply.op === 'remove') return {level: 'info', text: reply.removed ? 'Removed from ' + reply.path + '.' + reloadNote : 'sources.json has no entry for it.'};
    if (reply.op === 'restart') return {level: 'info', text: reply.resetAverage ? 'Restarted; the average starts again.' : 'Restarted.'};
    if (reply.op === 'restartAll') return {level: 'info', text: 'Source helper restarted every source.'};
    return null;
}
