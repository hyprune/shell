// Director > Objects > Data sources (data sources phase 2, RFC-0013 draft): every entry of
// sources.json, command and HTTP sources with their gauge map, a live Test (the helper's raw
// response and the mapped values) and secrets by name. Pure helpers: tested with node in
// tests/test_data_sources.py. The bridge (bridge/sources.py) writes the file and stores
// secrets; the helper runs and maps the sources.

var KINDS = [{id: 'http', label: 'HTTP'}, {id: 'command', label: 'Command'}];
var METHODS = ['GET', 'POST', 'PUT', 'PATCH'];
var OUTPUTS = [{id: 'json', label: 'JSON'}, {id: 'number', label: 'Number'}, {id: 'text', label: 'Text'}, {id: 'lines', label: 'Line count'}];
var REDUCES = [{id: '', label: 'First match'}, {id: 'count', label: 'Count'}, {id: 'sum', label: 'Sum'}, {id: 'avg', label: 'Average'},
               {id: 'min', label: 'Minimum'}, {id: 'max', label: 'Maximum'}, {id: 'last', label: 'Last match'}];
var LEVEL_MODES = [{id: 'none', label: 'None'}, {id: 'thresholds', label: 'Thresholds'}, {id: 'match', label: 'Match text'}];
var SLUG = /^[a-z][a-z0-9-]*$/;
var SECRET = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$/;
var PLACEHOLDER = /\{secret:([A-Za-z0-9][A-Za-z0-9_.-]{0,63})\}/g;
var LEVELS = ['ok', 'warn', 'fail'];  // the gauges' level input
var ORIGINS = {env: 'environment', file: 'secrets file', keyring: 'keyring'};

function str(v) { return v === undefined || v === null ? '' : String(v); }
function num(text) {
    var t = String(text === undefined || text === null ? '' : text).trim();
    if (t === '') return null;
    var n = Number(t);
    return isFinite(n) ? n : NaN;
}

// ---- the list ----

// A short description of what an entry reads: the URL's host and path, or the command line.
function target(entry) {
    if (!entry) return '';
    if ((entry.kind || 'command') === 'http') {
        var m = /^https?:\/\/([^/?#]+)([^?#]*)/.exec(str(entry.url));
        return m ? (entry.method && entry.method !== 'GET' ? entry.method + ' ' : '') + m[1] + (m[2] && m[2] !== '/' ? m[2] : '') : str(entry.url);
    }
    return (entry.argv || []).join(' ');
}

// Rows for the list: sources.json order, each with the helper's state.
function rows(list) {
    var entries = list && list.entries ? list.entries : [];
    var running = list && list.status && list.status.ok && list.status.sources ? list.status.sources : {};
    return entries.filter(function (e) { return e && typeof e.id === 'string'; }).map(function (e) {
        var s = running[e.id], kind = e.kind || 'command';
        // RFC-0016: a command an assistant proposed waits for Allow ("confirm": "pending").
        var pending = e.confirm === 'pending';
        var state = pending ? 'pending' : e.enabled === false ? 'disabled' : !s ? 'idle' : s.lastRun ? (s.lastRun.ok ? 'ok' : 'error') : 'waiting';
        return {id: e.id, kind: kind, kindLabel: kind === 'http' ? 'HTTP' : kind === 'command' ? 'Command' : kind, pending: pending,
                target: target(e), state: state, editable: kind === 'http' || kind === 'command',
                error: s && s.lastRun && !s.lastRun.ok ? str(s.lastRun.error) : '',
                values: s && s.lastRun ? s.lastRun.values || {} : {}};
    });
}

// A free id for a new source: http-1, command-1 ...
function freeId(list, kind) {
    var taken = {};
    ((list && list.entries) || []).forEach(function (e) { if (e) taken[e.id] = true; });
    for (var i = 1; i < 1000; ++i)
        if (!taken[kind + '-' + i]) return kind + '-' + i;
    return kind + '-' + Date.now();
}

// ---- the editor ----

function selection(sel) {
    if (!sel || typeof sel !== 'object') return {path: '', reduce: ''};
    if (sel.path) return {path: sel.path, reduce: sel.reduce || ''};
    if (sel.field) return {path: '{' + sel.field + '}', reduce: ''};
    if (sel.pointer !== undefined) return {path: String(sel.pointer), reduce: ''};
    return {path: '', reduce: ''};
}

function matchText(match) {
    return Object.keys(match || {}).map(function (k) { return k + '=' + match[k]; }).join(', ');
}

// The form's draft from an entry (null: a new source of `kind`).
function draft(entry, kind, id) {
    var e = entry || {kind: kind || 'http', id: id || ''};
    var map = e.map || {}, value = selection(map.value), level = map.level || null, lab = map.label;
    var headers = Object.keys(e.headers || {}).map(function (name) {
        var v = e.headers[name];
        return v && typeof v === 'object' ? {name: name, secret: str(v.secret), prefix: str(v.prefix), text: ''}
                                          : {name: name, secret: '', prefix: '', text: str(v)};
    });
    var argv = e.argv || [];
    return {
        id: str(e.id), kind: e.kind || 'command', enabled: e.enabled !== false,
        command: str(argv[0]), args: argv.slice(1).join('\n'),
        url: str(e.url), method: e.method || 'GET', headers: headers, local: e.local === true,
        body: e.body === undefined || e.body === null ? '' : typeof e.body === 'string' ? e.body : JSON.stringify(e.body, null, 2),
        output: e.output || 'json', interval: e.intervalS === undefined ? '' : String(e.intervalS),
        timeout: e.timeoutS === undefined ? '' : String(e.timeoutS),
        valuePath: value.path, reduce: value.reduce,
        min: map.value && map.value.min !== undefined ? String(map.value.min) : '',
        max: map.value && map.value.max !== undefined ? String(map.value.max) : '',
        levelMode: !level ? 'none' : level.match ? 'match' : 'thresholds',
        warn: level && level.warn !== undefined ? String(level.warn) : '', fail: level && level.fail !== undefined ? String(level.fail) : '',
        below: !!(level && level.below), ofRaw: !!(level && level.of === 'raw'),
        matchPath: level && level.match ? selection(level).path : '', match: level && level.match ? matchText(level.match) : '',
        otherwise: level && level.otherwise ? level.otherwise : 'ok',
        display: str(map.display),
        labelPath: lab && typeof lab === 'object' ? selection(lab).path : '', label: typeof lab === 'string' ? lab : ''
    };
}

// A path field: "$..." a JSONPath-like path, "{name}" a field (the output's key), "/a/b" a pointer.
function selector(text, reduce) {
    var t = String(text || '').trim();
    if (!t) return null;
    var field = /^\{([^{}]+)\}$/.exec(t);
    if (field) return {field: field[1]};
    if (t.charAt(0) === '/') return {pointer: t};
    var out = {path: t.charAt(0) === '$' ? t : '$.' + t};
    if (reduce) out.reduce = reduce;
    return out;
}

function parseArgs(text) {
    return String(text || '').split('\n').map(function (l) { return l.replace(/\s+$/, ''); }).filter(function (l) { return l !== ''; });
}

function parseMatch(text) {
    var out = {}, bad = '';
    String(text || '').split(',').forEach(function (part) {
        var p = part.trim();
        if (!p) return;
        var m = /^(.+?)\s*=\s*(ok|warn|fail)$/.exec(p);
        if (!m) bad = bad || p;
        else out[m[1].trim().toLowerCase()] = m[2];
    });
    return {match: out, bad: bad};
}

// The entry the page writes ({entry, error}): the keys it edits, null for the ones it clears
// (the bridge removes those and keeps any other key).
function entryFrom(d) {
    var err = function (text) { return {entry: null, error: text}; };
    if (!SLUG.test(d.id || '')) return err('The id is a lower-case slug: letters, digits and dashes, starting with a letter.');
    var e = {id: d.id, kind: d.kind, enabled: d.enabled ? null : false};
    if (d.kind === 'command') {
        var command = String(d.command || '').trim();
        if (!command) return err('Choose a command.');
        e.argv = [command].concat(parseArgs(d.args));
        e.url = e.method = e.headers = e.body = e.local = null;
    } else {
        var url = String(d.url || '').trim();
        if (!/^https?:\/\/[^\s/]+/.test(url)) return err('The URL starts with https:// (or http:// for this machine or a local network).');
        if (/^http:\/\//.test(url) && !d.local && !/^http:\/\/(localhost|127\.|\[::1\])/.test(url))
            return err('Plain http:// is for this machine; for a local network, tick "Local network".');
        e.url = url; e.method = d.method === 'GET' ? null : d.method; e.local = d.local ? true : null; e.argv = null;
        var headers = {}, n = 0;
        for (var i = 0; i < (d.headers || []).length; ++i) {
            var h = d.headers[i], name = String(h.name || '').trim();
            if (!name && !h.text && !h.secret) continue;
            if (!/^[A-Za-z0-9-]{1,64}$/.test(name)) return err('Header "' + name + '" is not a header name.');
            if (h.secret) {
                if (!SECRET.test(h.secret)) return err('Secret names are letters, digits and ._- (at most 64).');
                headers[name] = h.prefix ? {secret: h.secret, prefix: h.prefix} : {secret: h.secret};
            } else headers[name] = String(h.text || '');
            ++n;
        }
        e.headers = n ? headers : null;
        var body = String(d.body || '');
        if (body.trim() === '') e.body = null;
        else if (d.method === 'GET') return err('A body needs POST, PUT or PATCH.');
        else {
            var trimmed = body.trim();
            if (trimmed.charAt(0) === '{' || trimmed.charAt(0) === '[') {
                try { e.body = JSON.parse(trimmed); } catch (x) { return err('The body starts like JSON but is not: ' + x.message); }
            } else e.body = body;
        }
    }
    e.output = d.output === 'json' ? null : d.output;
    var interval = num(d.interval), timeout = num(d.timeout);
    if (Number.isNaN(interval) || interval !== null && interval <= 0) return err('The interval is a number of seconds.');
    if (Number.isNaN(timeout) || timeout !== null && timeout <= 0) return err('The timeout is a number of seconds.');
    e.intervalS = interval; e.timeoutS = timeout;
    var map = {};
    var value = selector(d.valuePath, d.reduce);
    if (value) {
        var lo = num(d.min), hi = num(d.max);
        if (Number.isNaN(lo) || Number.isNaN(hi)) return err('Min and max are numbers.');
        if (lo !== null) value.min = lo;
        if (hi !== null) value.max = hi;
        if ((lo === null ? 0 : lo) === (hi === null ? 100 : hi)) return err('Min and max must differ.');
        map.value = value;
    }
    if (d.levelMode === 'thresholds') {
        var warn = num(d.warn), fail = num(d.fail);
        if (Number.isNaN(warn) || Number.isNaN(fail) || warn === null && fail === null) return err('Thresholds are numbers: warn, fail or both.');
        if (!value && !d.ofRaw) return err('Thresholds compare the value: choose what the value reads.');
        var level = {};
        if (warn !== null) level.warn = warn;
        if (fail !== null) level.fail = fail;
        if (d.below) level.below = true;
        if (d.ofRaw) level.of = 'raw';
        map.level = level;
    } else if (d.levelMode === 'match') {
        var sel = selector(d.matchPath, '');
        if (!sel) return err('Choose the text the level is matched on.');
        var parsed = parseMatch(d.match);
        if (parsed.bad) return err('"' + parsed.bad + '" is not text=ok, text=warn or text=fail.');
        if (!Object.keys(parsed.match).length) return err('Map at least one text to a level (late=fail).');
        map.level = Object.assign(sel, {match: parsed.match}, d.otherwise && d.otherwise !== 'ok' ? {otherwise: d.otherwise} : {});
    }
    if (String(d.display || '').trim()) map.display = String(d.display);
    var labelSel = selector(d.labelPath, '');
    if (labelSel) map.label = labelSel;
    else if (String(d.label || '').trim()) map.label = String(d.label).trim().slice(0, 64);
    e.map = Object.keys(map).length ? map : null;
    return {entry: e, error: ''};
}

// The definition a test runs: the entry without nulls (the helper takes it as written).
function testSource(entry) {
    var out = {};
    // The user's Test runs a proposed command once (their consent); confirm stays until Allow.
    Object.keys(entry || {}).forEach(function (k) { if (entry[k] !== null && k !== 'id' && k !== 'enabled' && k !== 'confirm') out[k] = entry[k]; });
    return out;
}

// Secret names a draft refers to: header secrets and {secret:name} in the URL, headers and body.
function secretNames(d) {
    var names = {};
    var scan = function (text) { String(text || '').replace(PLACEHOLDER, function (_, n) { names[n] = true; return _; }); };
    scan(d.url); scan(d.body);
    (d.headers || []).forEach(function (h) { if (h.secret) names[h.secret] = true; scan(h.text); });
    return Object.keys(names).sort();
}

// Secret rows: where each is found (helper secrets op or a test's secrets).
function secretRows(names, found) {
    return (names || []).map(function (n) {
        var origin = found && Object.prototype.hasOwnProperty.call(found, n) ? found[n] : undefined;
        return {name: n, origin: origin || null, known: origin !== undefined,
                text: origin ? 'Found in the ' + (ORIGINS[origin] || origin) : origin === null ? 'Not set: store it below' : 'Not checked yet'};
    });
}

// ---- the test result ----

function valueText(v) {
    if (typeof v === 'number') return Number.isInteger(v) ? String(v) : String(Math.round(v * 1000) / 1000);
    if (typeof v === 'string') return v;
    return JSON.stringify(v);
}

// What a test answered: a status line, the raw response, the mapped keys (gauge keys first)
// and a gauge preview.
function testView(result) {
    if (!result) return null;
    var values = result.values || {};
    var gauge = ['value', 'level', 'label', 'display'];
    var keys = gauge.filter(function (k) { return k in values; }).concat(Object.keys(values).filter(function (k) { return gauge.indexOf(k) < 0; }));
    var parts = [];
    if (typeof result.httpStatus === 'number') parts.push('HTTP ' + result.httpStatus);
    if (typeof result.exitCode === 'number') parts.push('exit ' + result.exitCode);
    if (result.contentType) parts.push(String(result.contentType).split(';')[0]);
    if (typeof result.rawBytes === 'number') parts.push(result.rawBytes < 1024 ? result.rawBytes + ' B' : Math.round(result.rawBytes / 102.4) / 10 + ' KiB');
    if (typeof result.durationMs === 'number') parts.push(result.durationMs + ' ms');
    var value = typeof values.value === 'number' ? Math.max(0, Math.min(100, values.value)) : null;
    return {line: parts.join(' · '), ok: !result.error, error: str(result.error),
            raw: result.raw !== undefined ? str(result.raw) : str(result.stdout),
            truncated: typeof result.rawBytes === 'number' && result.rawBytes > 4096,
            rows: keys.map(function (k) { return {key: k, value: valueText(values[k]), gauge: gauge.indexOf(k) >= 0}; }),
            preview: {value: value, level: LEVELS.indexOf(values.level) >= 0 ? values.level : 'ok',
                      display: values.display !== undefined ? str(values.display) : value !== null ? valueText(values.value) : '',
                      label: str(values.label)}};
}

// RFC-0016: Allow a proposed command: the whole entry without its confirm key (the helper then runs it).
function allowEntry(entry) {
    var out = {};
    Object.keys(entry || {}).forEach(function (k) { if (k !== 'confirm') out[k] = entry[k]; });
    out.confirm = null;
    return out;
}
function proposalText(entry) { return entry && entry.confirm === 'pending' ? 'An assistant proposed this command. It runs only after you allow it: ' + (entry.argv || []).join(' ') : ''; }
