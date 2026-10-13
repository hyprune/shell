// Director > Surfaces pocket state (IPC 0.20) and Director > Help movement mode.
// Pure helpers: tested with node in tests/test_ipc20.py.

var WALK = 'com.hyprune.walk';
var FLY = 'com.hyprune.fly';

// Surface ids in the pocket (the Placement queue, editor.unplaced.windows).
function pocketIds(state) {
    var u = state && state.editor && state.editor.unplaced;
    return u && u.windows ? u.windows.map(function(w) { return w.surfaceId; }) : [];
}

// Director > Surfaces cards: non-workspace surfaces, pocketed windows first (in pocket
// order), then the rest in core's order. Pocketed windows core no longer lists among the
// surfaces still get a card from their pocket entry so they can be taken out.
function surfaceCards(state) {
    var surfaces = state && state.surfaces ? state.surfaces.filter(function(s) { return s.kind !== 'workspace'; }) : [];
    var u = state && state.editor && state.editor.unplaced;
    var pocket = u && u.windows ? u.windows : [];
    var pocketed = pocket.map(function(w) {
        var live = surfaces.find(function(s) { return s.id === w.surfaceId; });
        var card = live ? Object.assign({}, live) : {id: w.surfaceId, kind: 'window', title: w.title,
                                                       logicalSize: w.logicalSize, focused: false};
        card.pocketed = true;
        card.appClass = w.appClass;
        return card;
    });
    var ids = pocket.map(function(w) { return w.surfaceId; });
    var placed = surfaces.filter(function(s) { return ids.indexOf(s.id) < 0; })
                         .map(function(s) { return Object.assign({}, s, {pocketed: false}); });
    return {pocketed: pocketed, placed: placed};
}

// A window core keeps a record of (room or home workspace): it can be pocketed, pulled,
// placed or returned. Windows on other workspaces are listed as desktop-window-* for
// keyboard focus only; core refuses world actions on them.
function worldWindow(card) {
    return !!card && card.kind === 'window' && String(card.id).indexOf('desktop-window-') !== 0;
}

// Feedback for a pocket action result (or null when it needs none).
function pocketResult(method, result) {
    if (method === 'surface.unpocket' && result && result.placed === false)
        return {level: 'warning', text: 'No free spot here — aim and click to place it (Placement tool selected)'};
    if (method === 'surface.unpocket' && result && result.placed === true)
        return {level: 'info', text: 'Placed in front of you.'};
    if (method === 'surface.pocket' && result)
        return {level: 'info', text: 'In the pocket. Take it out to place it again.'};
    return null;
}

// Core errors on pocket actions ("<code>: <message>" from the bridge), in plain words.
function pocketError(method, message) {
    var m = /^(-?\d+):\s*(.*)$/.exec(String(message || ''));
    var code = m ? Number(m[1]) : 0, detail = m ? m[2] : String(message || '');
    if (code === -32003) return 'That window is gone.';
    if (method === 'surface.unpocket' && code === -32004) return 'That window is not in the pocket.';
    if (code === -32005 && /inactive/i.test(detail)) return 'Enter the world first.';
    if (code === -32005 && method === 'surface.pocket') return 'This window can\'t go in the pocket' + (detail ? ' (' + detail + ').' : '.');
    return detail || 'The request was refused.';
}

// Help > Movement segmented control: the active segment ('walk', 'fly', 'climb' or '').
function movementSegment(state) {
    var m = state && state.movement;
    if (!m) return '';
    if (m.state === 'climbing') return 'climb';
    return m.modeId === WALK ? 'walk' : m.modeId === FLY ? 'fly' : '';
}

function modeFor(segment) {
    return segment === 'walk' ? WALK : segment === 'fly' ? FLY : '';
}
