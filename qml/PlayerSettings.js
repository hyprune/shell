// IPC 0.19 player settings (movement, view bob, reach, reticle) and the
// overlay style colours. Pure helpers: tested with node in tests/test_ipc19.py.

var MOVEMENT_KEYS = ['walk_speed', 'run_speed', 'view_bob', 'reach_grab', 'reach_mount', 'reach_placement'];
var RETICLE_KEYS = ['reticle_style', 'reticle_size', 'reticle_thickness', 'reticle_gap', 'reticle_opacity',
                    'reticle_outline', 'reticle_colour', 'reticle_dynamic'];
// Spec fallbacks until player.get answers; core's `ranges`/`defaults` win.
var RANGES = {walk_speed: [0.5, 20], run_speed: [0.5, 30], reticle_size: [6, 64], reticle_thickness: [1, 6],
              reticle_gap: [0, 20], reticle_opacity: [0.2, 1], reach_grab: [1, 100], reach_mount: [1, 100],
              reach_placement: [1, 100]};
var DEFAULTS = {walk_speed: 4, run_speed: 10, view_bob: 'subtle', reticle_style: 'cross_dot', reticle_size: 18,
                reticle_thickness: 2, reticle_gap: 4, reticle_opacity: 0.9, reticle_outline: true,
                reticle_colour: 'theme', reticle_dynamic: true, reach_grab: 15, reach_mount: 8, reach_placement: 12};
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
    else if (RANGES[key]) out[key] = clamp(settings, key, round(Number(v), key === 'reticle_opacity' ? 2 : 1));
    else out[key] = v;
    return out;
}
function resetPatch(keys) { var out = {}; keys.forEach(function (k) { out[k] = null; }); return out; }

function speed(v) { return Number(v).toFixed(1) + ' m/s'; }
function metres(v) { return Number(v).toFixed(1) + ' m'; }
function pixels(v) { return (Math.round(v) === Number(v) ? Number(v).toFixed(0) : Number(v).toFixed(1)) + ' px'; }
function percent(v) { return Math.round(Number(v) * 100) + '%'; }
function degrees(v) { return Math.round(Number(v)) + '°'; }

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
    return style;
}

// Primary tool hint dims while the reticle says the action can't land (0.19).
function reticleBlocked(state) {
    var r = state && state.interaction && state.interaction.reticle;
    return !!r && (r.state === 'out_of_range' || r.state === 'invalid');
}
