// RFC-0015 phase 1: Director > Library (Browse, Installed, Sources) over the hyprune CLI's
// JSON contract (no core IPC in phase 1). Pure helpers: tested with node in
// tests/test_library.py. All index text is plain text; nothing here opens links.

var VIEWS = [{id: 'browse', label: 'Browse'}, {id: 'installed', label: 'Installed'}, {id: 'sources', label: 'Sources'}];
var TYPES = [{id: 'all', label: 'All'}, {id: 'world', label: 'Worlds'}, {id: 'library', label: 'Libraries'}];
var STAGES = [
    {id: 'resolving', label: 'Resolve'}, {id: 'downloading', label: 'Download'}, {id: 'verifying', label: 'Verify hash'},
    {id: 'extracting', label: 'Extract'}, {id: 'validating', label: 'Validate'}, {id: 'committing', label: 'Commit'}];
// Error rules (error.rule) in plain words.
var RULES = {
    'fetch.failed': 'the download failed', 'hash.mismatch': 'the download doesn\'t match its pinned hash',
    'archive.unsafe': 'the archive is unsafe', 'archive.limit': 'the archive is over a size limit',
    'data.executable': 'the package contains executable data', 'format.unsupported': 'needs a newer Hyprune',
    'package.invalid': 'the package is invalid', 'content.conflict': 'conflicts with what is installed',
    'requirement.missing': 'a required library is missing', 'disk.full': 'not enough disk space',
    'managed.system': 'managed by the system configuration', 'source.invalid': 'the source is invalid',
    'world.active': 'the world is loaded: load another world first', 'source.change': 'a source change needs confirmation',
    'not.found': 'not found', 'confirm.required': 'needs confirmation', 'cli.missing': 'the hyprune command didn\'t run'};
var DATA_ONLY = 'Worlds and libraries contain no code. Installing doesn\'t run anything.';
var CUSTOM_NOTICE = 'Hyprune doesn\'t check custom sources. Packages from them are installed with the same safety checks, but nobody has reviewed them.';
var LABEL_MAX = 48;
var KINDS = {official: 'Built-in', community: 'Built-in', index: 'Index', github: 'GitHub', url: 'Package URL'};

// $HYPRUNE_CLI is a command line split on spaces; else `hyprune` on PATH.
function cliCommand(value) {
    var words = String(value || '').split(/\s+/).filter(function (w) { return w; });
    return words.length ? words : ['hyprune'];
}

function typeLabel(type) { return type === 'world' ? 'World' : type === 'library' ? 'Library' : String(type || ''); }

// The source label is the CLI's `display` text (Official, Community registry, Custom: <label>).
function tierLabel(item) {
    if (!item) return '';
    if (item.display) return String(item.display);
    if (item.tier === 'official') return 'Official';
    if (item.tier === 'community') return 'Community registry';
    return item.sourceId ? 'Custom: ' + item.sourceId : '';
}

function tierOf(item) {
    if (!item) return '';
    if (item.tier) return item.tier;
    var d = tierLabel(item);
    return d === 'Official' ? 'official' : d === 'Community registry' ? 'community' : 'custom';
}

// The licence with its source-kind wording (RFC-0015 Provenance and licence on install).
function licenceText(licence, note) {
    var spdx = licence ? String(licence) : 'No licence declared';
    if (note === 'reviewed') return spdx + '  ·  reviewed by Hyprune';
    if (note === 'declared') return spdx + '  ·  declared by the creator, not reviewed';
    return spdx + '  ·  declared by the package, not checked';
}

function sizeText(bytes) {
    if (bytes === null || bytes === undefined || isNaN(bytes)) return '';
    var units = ['bytes', 'KiB', 'MiB', 'GiB', 'TiB'], v = Number(bytes), i = 0;
    while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
    return (i === 0 ? String(Math.round(v)) : v < 10 ? v.toFixed(1) : String(Math.round(v))) + ' ' + units[i];
}

function shortHash(hex) { return hex ? String(hex).slice(0, 12) + '…' : ''; }

function timeText(iso) {
    if (!iso) return '';
    var m = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})/.exec(String(iso));
    return m ? m[1] + ' ' + m[2] + ' UTC' : String(iso);
}

function words(text) { return String(text || '').toLowerCase().split(/\s+/).filter(function (w) { return w; }); }

// filter: {source: 'all'|<sourceId>, type: 'all'|'world'|'library', query}. Every query word
// must appear in the name, summary or a tag. The CLI's order (official first) is kept.
function filterEntries(entries, filter) {
    var f = filter || {}, query = words(f.query);
    return (entries || []).filter(function (e) {
        if (f.source && f.source !== 'all' && e.sourceId !== f.source) return false;
        if (f.type && f.type !== 'all' && e.type !== f.type) return false;
        if (!query.length) return true;
        var hay = [e.name, e.summary].concat(e.tags || []).map(function (s) { return String(s || '').toLowerCase(); });
        return query.every(function (w) { return hay.some(function (h) { return h.indexOf(w) >= 0; }); });
    });
}

// Source filter choices: every enabled source with entries, in the sources' order.
function sourceChoices(sources, entries) {
    var listed = {};
    (entries || []).forEach(function (e) { listed[e.sourceId] = true; });
    return [{id: 'all', label: 'All sources'}].concat((sources || []).filter(function (s) { return s.enabled && listed[s.id]; })
        .map(function (s) { return {id: s.id, label: tierLabel(s)}; }));
}

function loadable(entry) {
    if (!entry) return false;
    var versions = entry.versions && entry.versions.length ? entry.versions : entry.latest ? [entry.latest] : [];
    return versions.some(function (v) { return v.loadable !== false && (!v.status || v.status === 'available'); });
}

// System-managed content has no install record, so browse lists it as not installed; the
// content list knows it: such entries read as installed by the system (no action).
function mergeInstalls(entries, installs) {
    var system = {};
    (installs || []).forEach(function (i) { if (i.managed === 'system') system[i.type + ':' + i.id] = i; });
    return (entries || []).map(function (e) {
        var i = system[e.type + ':' + e.id];
        return e.installed || !i ? e : Object.assign({}, e, {installed: {tag: i.tag, sourceId: null, system: true}, update: null});
    });
}

function installedHere(entry) { return !!(entry && entry.installed && entry.installed.sourceId === entry.sourceId); }

// Badges on a card: installed, update available, needs a newer Hyprune.
function entryBadges(entry) {
    var out = [];
    if (!entry) return out;
    if (entry.installed) {
        var system = !entry.installed.sourceId;
        out.push({id: 'installed', tone: 'positive', label: installedHere(entry) ? 'Installed  ' + (entry.installed.tag || '')
                  : system ? 'Installed  ·  system' : 'Installed from another source'});
    }
    if (entry.update) out.push({id: 'update', tone: 'accent', label: 'Update  ' + entry.update});
    if (entry.latest && entry.latest.loadable === false) out.push({id: 'newer', tone: 'warning', label: 'Needs a newer Hyprune'});
    return out.map(function (b) { return {id: b.id, tone: b.tone, label: b.label.trim()}; });
}

// The card's main action: {kind: install|update|installed|switch|system|unavailable, label, enabled}.
function entryAction(entry) {
    if (!entry) return {kind: 'unavailable', label: '', enabled: false};
    if (entry.installed && !entry.installed.sourceId) return {kind: 'system', label: 'Installed by the system', enabled: false};
    if (installedHere(entry)) return entry.update ? {kind: 'update', label: 'Update to ' + entry.update, enabled: true}
                                                  : {kind: 'installed', label: 'Installed', enabled: false};
    if (!loadable(entry)) return {kind: 'unavailable', label: 'Needs a newer Hyprune', enabled: false};
    if (entry.installed) return {kind: 'switch', label: 'Install from this source', enabled: true};
    return {kind: 'install', label: 'Install', enabled: true};
}

function entryFor(entries, id, sourceId) {
    return (entries || []).find(function (e) { return e.id === id && (!sourceId || e.sourceId === sourceId); }) || null;
}

// ---- Installed ----

function installSource(install) {
    if (!install) return '';
    if (install.managed === 'system') return 'system';
    if (install.display) return String(install.display);
    return install.sourceId || 'local';
}

function installName(install, entries) {
    var e = entryFor(entries, install ? install.id : '', install ? install.sourceId : '') || entryFor(entries, install ? install.id : '');
    return e ? e.name : install ? install.id : '';
}

function installBadges(install) {
    var out = [];
    if (!install) return out;
    if (install.managed === 'system') out.push({id: 'system', tone: 'muted', label: 'SYSTEM'});
    if (install.pinned) out.push({id: 'pinned', tone: 'gold', label: 'PINNED'});
    if (install.newerTag) out.push({id: 'update', tone: 'accent', label: install.pinned ? 'NEWER ' + install.newerTag : 'UPDATE ' + install.newerTag});
    if (install.removedFromSource) out.push({id: 'removed', tone: 'warning', label: 'REMOVED FROM SOURCE'});
    return out;
}

// Actions for one install, in order. System-managed installs offer none.
function installActions(install) {
    if (!install || install.managed === 'system') return [];
    return [
        {id: 'update', label: install.newerTag ? 'Update to ' + install.newerTag : 'Up to date', enabled: !!install.newerTag && !install.pinned},
        {id: 'rollback', label: install.previous ? 'Roll back to ' + install.previous.tag : 'No previous version', enabled: !!install.previous},
        {id: install.pinned ? 'unpin' : 'pin', label: install.pinned ? 'Unpin' : 'Pin to ' + (install.tag || install.version), enabled: true},
        {id: 'remove', label: 'Remove', enabled: true}];
}

function installFacts(install) {
    if (!install) return [];
    return [
        {label: 'Current', value: install.tag ? install.tag + '  (' + install.version + ')' : install.version || '—'},
        {label: 'Previous', value: install.previous ? install.previous.tag + '  (' + install.previous.version + ')' : 'None'},
        {label: 'Source', value: installSource(install) + (install.removedFromSource ? '  ·  removed from source' : '')},
        {label: 'Pinned', value: install.pinned ? 'Yes: updates skip it' : 'No'},
        {label: 'Newer tag', value: install.newerTag || 'None'},
        {label: 'Licence', value: install.license || 'No licence declared'},
        {label: 'Type', value: typeLabel(install.type)},
        {label: 'Folder', value: install.path || ''}].filter(function (f) { return f.value !== ''; });
}

// ---- Sources ----

function sourceLocation(source) {
    if (!source) return '';
    return source.repo ? 'github:' + source.repo : source.url || '';
}

function sourceKind(source) { return source ? (KINDS[source.kind] || String(source.kind || '')) + (source.system ? '  ·  system' : '') : ''; }

function sourceStatus(source) {
    if (!source) return {level: 'muted', text: ''};
    if (source.error) return {level: 'warning', text: String(source.error)};
    var parts = [source.entries === 1 ? '1 entry' : (source.entries || 0) + ' entries'];
    parts.push(source.lastRefresh ? 'refreshed ' + timeText(source.lastRefresh) : 'never refreshed');
    if (!source.enabled) parts.push('disabled');
    return {level: 'muted', text: parts.join('  ·  ')};
}

function removable(source) { return !!source && !source.builtin && !source.system; }

// The Add source form: URL or github:owner/repo[/name], an optional label (1-48 printable
// characters), and a sha256 for a direct archive URL. -> {ok, error, needsHash, args}
function sourceForm(url, label, sha256) {
    var u = String(url || '').trim(), l = String(label || '').trim(), h = String(sha256 || '').trim().toLowerCase();
    var github = /^github:[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})\/[A-Za-z0-9._-]{1,100}(?:\/[a-z0-9][a-z0-9-]{0,63})?$/.test(u);
    var https = /^https:\/\/[^\s/?#]+[^\s]*$/.test(u);
    var archive = https && /\.tar\.zst(?:[?#].*)?$/.test(u);
    var result = {ok: false, error: '', needsHash: archive, args: []};
    if (!u) return result;
    if (!github && !https) { result.error = 'Use an https:// URL or github:owner/repo.'; return result; }
    if (l.length > LABEL_MAX) { result.error = 'The label is at most ' + LABEL_MAX + ' characters.'; return result; }
    if (/[\u0000-\u001f\u007f-\u009f]/.test(l)) { result.error = 'The label must be printable text.'; return result; }
    if (archive && !/^[0-9a-f]{64}$/.test(h)) { result.error = 'A package URL needs its sha256 (64 hex digits): every install is pinned.'; return result; }
    result.ok = true;
    result.args = ['source', 'add', u].concat(l ? ['--label', l] : []).concat(archive ? ['--sha256', h] : []).concat(['--json']);
    return result;
}

// ---- Jobs ----

// CLI arguments for a job. kind: install|update|rollback|pin|unpin|remove; mode: plan|yes.
function jobArgs(kind, id, sourceId, mode, acceptSourceChange) {
    var args = [kind, id];
    if (kind === 'install' && sourceId) args = args.concat(['--from', sourceId]);
    if (mode === 'plan') args.push('--plan');
    else if (mode === 'yes') args.push('--yes');
    if (acceptSourceChange) args.push('--accept-source-change');
    return args.concat(['--json']);
}

// A fresh job. panel: install and update go through plan, confirmation and progress.
function newJob(kind, target, args) {
    return {kind: kind, target: target || {}, args: args, panel: kind === 'install' || kind === 'update',
            phase: kind === 'install' || kind === 'update' ? 'planning' : 'running',
            stage: '', stages: [], progress: null, plan: null, result: null, error: null, confirmChange: false};
}

// Apply one stdout line (a JSON lines event) to a job; non-JSON lines are ignored.
function jobEvent(job, line) {
    var e;
    try { e = JSON.parse(line); } catch (err) { return job; }
    if (!e || typeof e !== 'object' || !job) return job;
    var next = Object.assign({}, job);
    if (e.event === 'stage' && e.stage) {
        next.stage = String(e.stage);
        if (next.stages.indexOf(next.stage) < 0) next.stages = next.stages.concat([next.stage]);
        if (next.stage !== 'downloading') next.progress = job.stage === 'downloading' && job.progress ? job.progress : null;
    } else if (e.event === 'progress') {
        next.progress = {bytes: Number(e.bytes) || 0, total: e.total ? Number(e.total) : null};
    } else if (e.event === 'plan' && e.plan) {
        next.plan = e.plan;
    } else if (e.event === 'done') {
        next.result = e.result || {};
    } else if (e.event === 'error' && e.error) {
        next.error = {rule: String(e.error.rule || ''), message: String(e.error.message || '')};
    }
    return next;
}

// The process ended: the job's next phase. A plan run that saw a plan (even one that ended on
// rule source.change) waits for confirmation.
function jobFinished(job, exitCode, stderrText) {
    if (!job) return job;
    var next = Object.assign({}, job);
    if (job.phase === 'planning' && job.plan && (exitCode === 0 || (job.error && job.error.rule === 'source.change'))) {
        next.phase = 'confirm'; next.error = null; return next;
    }
    if (exitCode === 0 && !job.error) { next.phase = 'done'; return next; }
    next.phase = 'failed';
    if (!next.error) {
        var tail = stderrLine(stderrText);
        next.error = exitCode < 0 ? {rule: 'cli.missing', message: 'The hyprune command could not be started. Set HYPRUNE_CLI or put hyprune on PATH.'}
                                  : {rule: '', message: tail || 'The hyprune command ended with exit code ' + exitCode + '.'};
    }
    return next;
}

// The line worth showing from stderr: the CLI's own `hyprune: …` message (usage errors print
// the help after it), else the last non-empty line.
function stderrLine(text) {
    var lines = String(text || '').split('\n').map(function (l) { return l.trim(); }).filter(function (l) { return l; });
    var own = lines.filter(function (l) { return /^hyprune: /.test(l); });
    return (own.length ? own[own.length - 1] : lines[lines.length - 1]) || '';
}

function running(job) { return !!job && (job.phase === 'planning' || job.phase === 'running'); }

function ruleText(rule) { return rule ? RULES[rule] || rule : ''; }

function errorText(error) {
    if (!error) return {line: '', detail: ''};
    return {line: error.message || ruleText(error.rule) || 'Failed.', detail: error.rule ? 'Rule: ' + error.rule + (RULES[error.rule] ? '  ·  ' + RULES[error.rule] : '') : ''};
}

function stageRows(job) {
    if (!job) return [];
    var at = STAGES.findIndex(function (s) { return s.id === job.stage; });
    if (at < 0 && job.phase === 'failed') at = 0;  // failed before its first stage (the CLI didn't start)
    return STAGES.map(function (s, i) {
        var state = job.phase === 'done' ? 'done' : i < at ? 'done' : i === at ? (job.phase === 'failed' ? 'failed' : 'current') : 'pending';
        return {id: s.id, label: s.label, state: state};
    });
}

function progressText(progress) {
    if (!progress) return '';
    return sizeText(progress.bytes) + (progress.total ? '  /  ' + sizeText(progress.total) : '');
}

function progressFraction(progress) {
    return progress && progress.total ? Math.max(0, Math.min(1, progress.bytes / progress.total)) : 0;
}

var ACTIONS = {install: 'Install', update: 'Update', downgrade: 'Install an older version', 'already-installed': 'Already installed'};

// Provenance rows for one package of a plan (RFC-0015 confirmation items). name: the entry's
// name when the plan doesn't carry one.
function provenance(pkg, sources, name) {
    if (!pkg) return [];
    var source = (sources || []).find(function (s) { return s.id === pkg.sourceId; }) || null;
    var where = pkg.sourceUrl || sourceLocation(source);
    var repo = [pkg.creator ? 'by ' + pkg.creator : '', pkg.repo || ''].filter(function (v) { return v; }).join('  ·  ');
    return [
        {id: 'name', label: 'Name', value: pkg.name || name || pkg.id},
        {id: 'id', label: 'Id', value: pkg.id},
        {id: 'version', label: 'Version', value: (pkg.tag || '') + (pkg.version ? '  (' + pkg.version + ')' : '') + (pkg.replaces ? '  ·  replaces ' + pkg.replaces : '')},
        {id: 'type', label: 'Type', value: typeLabel(pkg.type)},
        {id: 'source', label: 'Source', value: (pkg.sourceLabel || tierLabel(source) || pkg.sourceId || '') + (where ? '  ·  ' + where : '')},
        {id: 'creator', label: 'Creator', value: repo + (pkg.commit ? '  ·  commit ' + String(pkg.commit).slice(0, 10) : '')},
        {id: 'licence', label: 'Licence', value: licenceText(pkg.license, pkg.licenceNote)},
        {id: 'size', label: 'Size', value: [pkg.bytes ? sizeText(pkg.bytes) + ' download' : '', pkg.expandedBytes ? sizeText(pkg.expandedBytes) + ' installed' : ''].filter(function (v) { return v; }).join('  ·  ')},
        {id: 'asset', label: 'Asset', value: pkg.url || ''},
        {id: 'hash', label: 'sha256', value: shortHash(pkg.sha256)}].filter(function (r) { return r.value; });
}

// Requirements: every package after the first (libraries the world pulls in), named from the
// entries when the plan carries no name.
function requirements(plan, entries) {
    if (!plan || !plan.packages) return [];
    return plan.packages.slice(1).map(function (p) {
        var e = entryFor(entries, p.id, p.sourceId) || entryFor(entries, p.id);
        return {id: p.id, text: (p.name || (e ? e.name : p.id)) + '  ' + (p.tag || p.version || '') + '  ·  ' + (p.sourceLabel || p.sourceId || '')
                + '  ·  ' + (ACTIONS[p.action] || p.action || '') + (p.action === 'already-installed' ? '' : p.bytes ? '  ·  ' + sizeText(p.bytes) : '')};
    });
}

function planTotal(plan) {
    if (!plan || !plan.packages) return 0;
    return plan.packages.filter(function (p) { return p.action !== 'already-installed'; }).reduce(function (n, p) { return n + (p.bytes || 0); }, 0);
}

function changeLabel(side) { return !side ? '' : typeof side === 'string' ? side : side.display || side.label || side.sourceId || 'system'; }

// A source change (installed from one source, now installing from another): {from, to} labels.
function sourceChange(plan) {
    var c = plan ? plan.sourceChange : null;
    if (!c) return null;
    return {id: c.id || '', from: changeLabel(c.from), to: changeLabel(c.to)};
}

// The page line and the HUD toast for a finished job.
function resultText(job, name) {
    if (!job) return '';
    var r = job.result || {};
    var who = name || r.display || r.name || r.id || job.target.id || '';
    var tag = job.result && job.result.tag ? ' ' + job.result.tag : '';
    var verbs = {install: 'Installed', update: 'Updated', rollback: 'Rolled back', pin: 'Pinned', unpin: 'Unpinned', remove: 'Removed',
                 'source.add': 'Added the source', 'source.refresh': 'Refreshed', 'source.enable': 'Enabled', 'source.disable': 'Disabled', 'source.remove': 'Removed the source'};
    var verb = verbs[job.kind] || 'Done';
    if (job.kind === 'rollback') return 'Rolled back ' + who + ' to' + tag + ' and pinned it.';
    if (job.kind === 'source.refresh') return 'Sources refreshed.';
    return verb + ' ' + who + (job.kind === 'install' || job.kind === 'update' || job.kind === 'pin' ? tag : '') + '.';
}

function toast(job, name) {
    var failed = job && job.phase === 'failed';
    var e = errorText(job ? job.error : null);
    return {key: 'library:' + (job ? job.kind : ''), kind: 'toast', category: 'objects', tone: failed ? 'warning' : 'info', title: 'Library',
            line: failed ? e.line : resultText(job, name), detail: failed ? e.detail : '', durationMs: 4000, count: 1};
}
