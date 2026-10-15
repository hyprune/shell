// IPC 0.19 player settings (movement, view bob, reach, reticle) and the
// overlay style colours. Pure helpers: tested with node in tests/test_ipc19.py.

var MOVEMENT_KEYS = ['walk_speed', 'run_speed', 'view_bob', 'reach_grab', 'reach_mount', 'reach_placement'];
// IPC 0.29 feel settings (seconds on the wire, shown in ms; the head tilt in degrees).
var FEEL = [{key: 'look_inertia', name: 'Look smoothing', note: 'How long the view glides after the mouse stops. 0 is raw input (lowest latency).', ms: true},
            {key: 'move_inertia', name: 'Movement smoothing', note: 'How long walking takes to speed up and slow down.', ms: true},
            {key: 'view_bob_roll', name: 'Head tilt while walking', note: 'A slight left-right tilt with each stride, on top of the view bob.', ms: false},
            {key: 'carry_turn', name: 'Carry: turn toward you', note: 'How long a carried window takes to turn to face you. 0 is rigid.', ms: true},
            {key: 'carry_follow', name: 'Carry: follow', note: 'How far a carried window trails behind when you turn. 0 is rigid.', ms: true}];
var FEEL_KEYS = FEEL.map(function (f) { return f.key; });
var RETICLE_KEYS = ['reticle_style', 'reticle_size', 'reticle_thickness', 'reticle_gap', 'reticle_opacity',
                    'reticle_outline', 'reticle_colour', 'reticle_dynamic'];
// Spec fallbacks until player.get answers; core's `ranges`/`defaults` win.
var RANGES = {walk_speed: [0.5, 20], run_speed: [0.5, 30], reticle_size: [6, 64], reticle_thickness: [1, 6],
              reticle_gap: [0, 20], reticle_opacity: [0.2, 1], reach_grab: [1, 100], reach_mount: [1, 100],
              reach_placement: [1, 100], look_inertia: [0, 0.1], move_inertia: [0, 0.3], view_bob_roll: [0, 2],
              carry_turn: [0, 0.4], carry_follow: [0, 0.3]};
var DEFAULTS = {walk_speed: 4, run_speed: 10, view_bob: 'subtle', reticle_style: 'cross_dot', reticle_size: 18,
                reticle_thickness: 2, reticle_gap: 4, reticle_opacity: 0.9, reticle_outline: true,
                reticle_colour: 'theme', reticle_dynamic: true, reach_grab: 15, reach_mount: 8, reach_placement: 12,
                look_inertia: 0.03, move_inertia: 0.05, view_bob_roll: 0.4, carry_turn: 0.11, carry_follow: 0.04};
var FOV_RANGE = [30, 120];
var FOV_DEFAULT = 65;
var VIEW_BOB = [{value: 'off', name: 'Off'}, {value: 'subtle', name: 'Subtle'}, {value: 'normal', name: 'Normal'}];
var RETICLE_STYLES = [{value: 'cross_dot', name: 'Cross with dot'}, {value: 't_dot', name: 'T with dot'},
                      {value: 'circle_dot', name: 'Circle with dot'}, {value: 'dot', name: 'Dot'},
                      {value: 'cross', name: 'Cross'}, {value: 'chevron', name: 'Chevron'}];
var RETICLE_COLOURS = [{name: 'Theme', value: 'theme'}, {name: 'White', value: [1, 1, 1]},
                       {name: 'Yellow', value: [1, 0.86, 0.2]}, {name: 'Cyan', value: [0.3, 0.88, 1]},
                       {name: 'Magenta', value: [1, 0.35, 0.85]}, {name: 'Green', value: [0.4, 1, 0.45]}];

function config(settings) { return settings && settings.config ? settings.config : DEFAULTS; }
function value(settings, key) { var c = config(settings); return c[key] === undefined ? DEFAULTS[key] : c[key]; }
function range(settings, key) {
    var r = settings && settings.ranges && settings.ranges[key];
    return r && r.length === 2 ? r : RANGES[key];
}
function defaultValue(settings, key) {
    return settings && settings.defaults && settings.defaults[key] !== undefined ? settings.defaults[key] : DEFAULTS[key];
}
function clamp(settings, key, v) { var r = range(settings, key); return Math.min(r[1], Math.max(r[0], v)); }
function round(v, places) { var f = Math.pow(10, places); return Math.round(v * f) / f; }

// One player.set patch; numbers are clamped to core's ranges, sliders round to the shown precision.
function patch(settings, key, v) {
    var out = {};
    if (v === null) out[key] = null;
    else if (RANGES[key]) out[key] = clamp(settings, key, round(Number(v), FEEL_KEYS.indexOf(key) >= 0 && key !== 'view_bob_roll' ? 3 : key === 'reticle_opacity' || key === 'view_bob_roll' ? 2 : 1));
    else out[key] = v;
    return out;
}
function resetPatch(keys) { var out = {}; keys.forEach(function (k) { out[k] = null; }); return out; }

function speed(v) { return Number(v).toFixed(1) + ' m/s'; }
function metres(v) { return Number(v).toFixed(1) + ' m'; }
function pixels(v) { return (Math.round(v) === Number(v) ? Number(v).toFixed(0) : Number(v).toFixed(1)) + ' px'; }
function percent(v) { return Math.round(Number(v) * 100) + '%'; }
function degrees(v) { return Math.round(Number(v)) + '°'; }
function ms(v) { return Math.round(Number(v) * 1000) + ' ms'; }
function feelText(item, v) { return item.ms ? ms(v) : Number(v).toFixed(1) + '°'; }
// The core offers the feel settings (IPC 0.29).
function feelSupported(settings) { return !!(settings && settings.config && settings.config.look_inertia !== undefined); }

function viewBobIndex(v) { return VIEW_BOB.map(function (o) { return o.value; }).indexOf(v); }
function styleIndex(v) { return RETICLE_STYLES.map(function (o) { return o.value; }).indexOf(v); }
function sameRgb(a, b) { return Array.isArray(a) && Array.isArray(b) && a.length === 3 && a.every(function (x, i) { return Math.abs(x - b[i]) < 0.005; }); }
// -1 = a custom colour set elsewhere (Lua or SDK): shown as "Custom", kept until changed.
function colourIndex(v) {
    for (var i = 0; i < RETICLE_COLOURS.length; i++)
        if (v === RETICLE_COLOURS[i].value || sameRgb(v, RETICLE_COLOURS[i].value)) return i;
    return -1;
}
function colourNames(v) {
    var names = RETICLE_COLOURS.map(function (o) { return o.name; });
    return colourIndex(v) < 0 ? names.concat(['Custom']) : names;
}

// Qt colour (or {r,g,b}) to a schema RGB array.
function rgb(c) { return [round(c.r, 4), round(c.g, 4), round(c.b, 4)]; }

// overlay.style params style. reticle/valid/invalid colours only for IPC >= 0.19
// (older cores reject them).
function overlayStyle(t, minor) {
    var style = {fontFamily: t.mono, waypointColor: rgb(t.accent), routeColor: rgb(t.accent),
                 labelColor: rgb(t.text), promptColor: rgb(t.gold)};
    if (minor >= 19) {
        style.reticleColor = rgb(t.reticle);
        style.validColor = rgb(t.positive);
        style.invalidColor = rgb(t.warning);
    }
    if (minor >= 21 && t.quest) style.questColor = rgb(t.quest); // RFC-0012 marker colour
    return style;
}

// Primary tool hint dims while the reticle says the action can't land (0.19).
function reticleBlocked(state) {
    var r = state && state.interaction && state.interaction.reticle;
    return !!r && (r.state === 'out_of_range' || r.state === 'invalid');
}
