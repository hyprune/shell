// RFC-0010 companions amendment (IPC 0.25, draft): the Settings > Companion picker and the
// companion's status line. Pure helpers: tested with node in tests/test_ipc25.py.

var MODES = [{id: 'follow', label: 'Follow'}, {id: 'stay', label: 'Stay'}];
var ACTIVITIES = {
    following: 'following you', walking: 'walking', running: 'catching up', idle: 'idle', talking: 'talking',
    sitting: 'sitting', waiting: 'waiting for a free spot', carried: 'carried'};

// The picker's entries: installed characters that can be companions (library and user ones,
// capable first, by name), each {ref, name, thumbnail, source, capable, reason}. A world's
// own characters (package refs) never come along.
function choices(catalog) {
    return (catalog || [])
        .filter(e => e && e.companion && e.source !== 'package')
        .map(e => ({ref: e.ref, name: e.companion.name || e.name, thumbnail: e.thumbnail || '', source: e.source,
                    capable: e.companion.capable === true, reason: e.companion.reason || ''}))
        .sort((a, b) => (a.capable === b.capable ? 0 : a.capable ? -1 : 1) || a.name.localeCompare(b.name));
}

// The chosen ref, or '' for None.
function chosen(companion) { return companion && companion.ref ? companion.ref : ''; }

// The route's display name from paths.list (its name, else the ref's id).
function pathName(paths, ref) {
    var p = (paths || []).find(x => x.ref === ref);
    return p && p.name ? p.name : String(ref || '').replace(/^(user|package)\//, '');
}

// One line for the picker and the Director: who, and what they are doing.
function status(companion, paths) {
    if (!companion || companion.state === 'none' || !companion.ref) return 'No companion';
    var name = companion.name || 'Your companion';
    switch (companion.state) {
    case 'loading': return name + ' is on the way';
    case 'unavailable': return name + " can't come along" + (companion.reason ? ': ' + companion.reason : '');
    case 'hidden': return name + ' is resting' + (companion.reason ? ' (' + companion.reason + ')' : '');
    case 'waiting': return name + ' is waiting for a free spot';
    }
    if (companion.mode === 'route') return name + ' walks ' + pathName(paths, companion.path);
    if (companion.mode === 'stay') return name + ' stays here';
    return name + ' is ' + (ACTIVITIES[companion.activity] || 'following you');
}

// Follow/Stay segment index (route counts as neither: -1).
function modeIndex(companion) {
    if (!companion || !companion.ref) return -1;
    return companion.mode === 'follow' ? 0 : companion.mode === 'stay' ? 1 : -1;
}

// The request for a picker choice: {method, params} (None clears).
function choose(ref) { return ref ? {method: 'companion.set', params: {ref: ref}} : {method: 'companion.clear', params: {}}; }
