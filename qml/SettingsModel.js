// Director Settings (IPC 0.30 presets and overrides): the categories, every setting row and
// the helpers that read a row's value, default and override state from its store and build
// the request that changes or resets it. Pure: tested with node in tests/test_settings.py.
//
// Stores:
//   core     graphics.* and player.*: settings.get / settings.set (IPC 0.30); on older cores
//            graphics.get/set and player.get/set (no preset, overrides from their files).
//   guidance guidance.* (IPC 0.21 guidance.get/set): defaults and overrides of its own.
//   input    options of the keymap file (input.get/set), defaults from settings.get.
//   shell    this shell's presentation preferences (shell.json), defaults below.

var CATEGORIES = [
    {id: 'display', name: 'Display & performance'},
    {id: 'movement', name: 'Movement & camera'},
    {id: 'controls', name: 'Controls & keys'},
    {id: 'hud', name: 'HUD & reticle'},
    {id: 'world', name: 'World & characters'},
    {id: 'guidance', name: 'Guidance & focus'},
    {id: 'data', name: 'Data sources'},
    {id: 'recording', name: 'Recording'},
    {id: 'accessibility', name: 'Accessibility'},
    {id: 'advanced', name: 'Advanced'}
];

// Shell preference defaults (bridge/preferences.py DEFAULTS).
var SHELL_DEFAULTS = {concept: 'Adventure', resource: 'gpu', worldStyles: true, curved: true, curvature: 0.8, theme: 'night'};

function onOff(v) { return v ? 'On' : 'Off'; }
function choices(values, labels) { return values.map(function (v, i) { return {value: v, label: labels ? labels[i] : String(v)}; }); }

// kind: choice (options), toggle, slider (range, step, format), cap (a nullable slider: null
// reads "Automatic"), colour (named colours). cost: show the setting's GPU cost (Performance).
var ROWS = [
    // Display & performance
    {key: 'graphics.quality', category: 'display', group: 'Rendering', label: 'Rendering quality', kind: 'choice',
     options: choices(['auto', 'low', 'medium', 'high', 'ultra'], ['Automatic', 'Low', 'Medium', 'High', 'Ultra']),
     note: 'The shading tier. The preset chooses it; pick one to keep it whatever the preset.'},
    {key: 'graphics.target_fps', category: 'display', group: 'Rendering', label: 'Target frame rate', kind: 'slider', range: [30, 240], step: 1, format: 'fps',
     note: 'Below the display\'s refresh, frames are paced evenly on a fraction of it.'},
    {key: 'graphics.frame_pacing', category: 'display', group: 'Rendering', label: 'Frame pacing', kind: 'choice', options: choices(['even', 'max_rate'], ['Even', 'Max rate']), protocol: 29,
     note: 'With the offload renderer capped below the refresh: Even keeps frames on a steady fraction of it (smooth, a little more latency); Max rate shows as many as the cap allows.'},
    {key: 'graphics.dynamic_resolution', category: 'display', group: 'Rendering', label: 'Dynamic resolution', kind: 'toggle', note: 'Lowers the render scale to hold the target frame rate.'},
    {key: 'graphics.render_scale', category: 'display', group: 'Rendering', label: 'Render scale', kind: 'choice',
     options: choices(['auto', 0.375, 0.5, 0.625, 0.75, 0.875, 1], ['Automatic', '38%', '50%', '63%', '75%', '88%', '100%']), note: 'The ceiling with dynamic resolution, the fixed scale without.'},
    {key: 'graphics.scale_min', category: 'display', group: 'Rendering', label: 'Lowest dynamic scale', kind: 'slider', range: [0.375, 1], step: 0.025, format: 'percent', protocol: 10},
    {key: 'graphics.upscaler', category: 'display', group: 'Rendering', label: 'Upscaler', kind: 'choice', options: choices(['fsr1', 'bilinear'], ['FSR 1', 'Bilinear']), protocol: 16, cost: true},
    {key: 'graphics.sharpen', category: 'display', group: 'Rendering', label: 'Sharpening', kind: 'slider', range: [0, 1], step: 0.05, format: 'fixed2', cost: true},
    {key: 'graphics.msaa', category: 'display', group: 'Rendering', label: 'Anti-aliasing (MSAA)', kind: 'choice', options: choices([1, 2, 4], ['Off', '2x', '4x']), cost: true},
    {key: 'graphics.anisotropy', category: 'display', group: 'Rendering', label: 'Anisotropic filtering', kind: 'choice', options: choices([1, 2, 4, 8, 16], ['Off', '2x', '4x', '8x', '16x']), cost: true},
    {key: 'graphics.bloom', category: 'display', group: 'Effects', label: 'Bloom', kind: 'choice', options: choices(['off', 'low', 'high'], ['Off', 'Low', 'High']), cost: true},
    {key: 'graphics.fog', category: 'display', group: 'Effects', label: 'Fog', kind: 'choice', options: choices(['off', 'linear', 'height'], ['Off', 'Linear', 'Height']), cost: true},
    {key: 'graphics.sky', category: 'display', group: 'Effects', label: 'Sky', kind: 'choice', options: choices(['off', 'gradient', 'environment'], ['Off', 'Gradient', 'Environment']), cost: true},
    {key: 'graphics.reflections', category: 'display', group: 'Effects', label: 'Reflections', kind: 'toggle', cost: true},
    {key: 'graphics.normal_maps', category: 'display', group: 'Effects', label: 'Normal maps', kind: 'toggle', cost: true},
    {key: 'graphics.specular', category: 'display', group: 'Effects', label: 'Specular highlights', kind: 'toggle', cost: true},
    {key: 'graphics.ambient_occlusion', category: 'display', group: 'Effects', label: 'Ambient occlusion', kind: 'toggle', cost: true},
    {key: 'graphics.alpha_haze', category: 'display', group: 'Effects', label: 'Glass and haze', kind: 'toggle', cost: true},
    {key: 'graphics.offload', category: 'display', group: 'Offload renderer', label: 'Offload renderer', kind: 'choice', options: choices(['off', 'auto', 'on'], ['Off', 'Automatic', 'On']), protocol: 10,
     note: 'Renders the world on a second (discrete) GPU and shows it here.'},
    {key: 'graphics.offload_power_cap_w', category: 'display', group: 'Offload renderer', label: 'Power cap', kind: 'cap', range: [20, 350], step: 5, format: 'watts', protocol: 18,
     note: 'Automatic follows the power supply (lower on battery and USB-C).'},
    // Movement & camera
    {key: 'graphics.fov', category: 'movement', group: 'Camera', label: 'Field of view', kind: 'slider', range: [30, 120], step: 1, format: 'degrees'},
    {key: 'player.look_inertia', category: 'movement', group: 'Camera', label: 'Look smoothing', kind: 'slider', range: [0, 0.1], step: 0.005, format: 'ms', protocol: 29,
     note: 'How long the view glides after the mouse stops. 0 is raw input, the lowest latency.'},
    {key: 'player.view_bob', category: 'movement', group: 'Camera', label: 'View bob', kind: 'choice', options: choices(['off', 'subtle', 'normal'], ['Off', 'Subtle', 'Normal']), protocol: 19},
    {key: 'player.view_bob_roll', category: 'movement', group: 'Camera', label: 'Head tilt while walking', kind: 'slider', range: [0, 2], step: 0.1, format: 'degrees1', protocol: 29},
    {key: 'player.walk_speed', category: 'movement', group: 'Movement', label: 'Walk speed', kind: 'slider', range: [0.5, 20], step: 0.1, format: 'speed', protocol: 19},
    {key: 'player.run_speed', category: 'movement', group: 'Movement', label: 'Run speed', kind: 'slider', range: [0.5, 30], step: 0.1, format: 'speed', protocol: 19, note: 'While sprint is held. Flight scales by run / walk.'},
    {key: 'player.move_inertia', category: 'movement', group: 'Movement', label: 'Movement smoothing', kind: 'slider', range: [0, 0.3], step: 0.005, format: 'ms', protocol: 29,
     note: 'How long walking takes to speed up and slow down.'},
    {key: 'player.carry_turn', category: 'movement', group: 'Carrying windows', label: 'Turn toward you', kind: 'slider', range: [0, 0.4], step: 0.005, format: 'ms', protocol: 29, note: '0 is rigid.'},
    {key: 'player.carry_follow', category: 'movement', group: 'Carrying windows', label: 'Follow', kind: 'slider', range: [0, 0.3], step: 0.005, format: 'ms', protocol: 29, note: 'How far a carried window trails behind when you turn. 0 is rigid.'},
    // Controls & keys (the keymap itself is a block of its own)
    {key: 'input.scopeVignette', category: 'controls', group: 'Options', label: 'Scope vignette', kind: 'toggle'},
    // HUD & reticle
    {key: 'shell.concept', category: 'hud', group: 'HUD', label: 'HUD concept', kind: 'choice', options: choices(['Adventure', 'Instrument', 'Minimal'])},
    {key: 'shell.resource', category: 'hud', group: 'HUD', label: 'Resource bar', kind: 'choice',
     options: choices(['gpu', 'cpu', 'ram', 'tool'], ['GPU frame budget', 'CPU render budget', 'RAM (GPU fallback)', 'Tool capacity'])},
    {key: 'shell.worldStyles', category: 'hud', group: 'HUD', label: 'World HUD styles', kind: 'toggle', note: 'Worlds may restyle the HUD colours.'},
    {key: 'shell.theme', category: 'hud', group: 'HUD', label: 'Theme', kind: 'choice', options: choices(['night', 'paper'], ['Night', 'Paper'])},
    {key: 'shell.curved', category: 'hud', group: 'HUD', label: 'Curved HUD', kind: 'toggle'},
    {key: 'shell.curvature', category: 'hud', group: 'HUD', label: 'HUD curvature', kind: 'slider', range: [0, 1], step: 0.05, format: 'percent'},
    {key: 'input.show_area_markers', category: 'hud', group: 'HUD', label: 'Area and place labels', kind: 'toggle'},
    {key: 'player.reticle_style', category: 'hud', group: 'Reticle', label: 'Style', kind: 'choice', protocol: 19,
     options: choices(['cross_dot', 't_dot', 'circle_dot', 'dot', 'cross', 'chevron'], ['Cross with dot', 'T with dot', 'Circle with dot', 'Dot', 'Cross', 'Chevron'])},
    {key: 'player.reticle_size', category: 'hud', group: 'Reticle', label: 'Size', kind: 'slider', range: [6, 64], step: 1, format: 'px', protocol: 19},
    {key: 'player.reticle_thickness', category: 'hud', group: 'Reticle', label: 'Thickness', kind: 'slider', range: [1, 6], step: 0.5, format: 'px', protocol: 19},
    {key: 'player.reticle_gap', category: 'hud', group: 'Reticle', label: 'Gap', kind: 'slider', range: [0, 20], step: 1, format: 'px', protocol: 19},
    {key: 'player.reticle_opacity', category: 'hud', group: 'Reticle', label: 'Opacity', kind: 'slider', range: [0.2, 1], step: 0.05, format: 'percent', protocol: 19},
    {key: 'player.reticle_outline', category: 'hud', group: 'Reticle', label: 'Outline', kind: 'toggle', protocol: 19},
    {key: 'player.reticle_colour', category: 'hud', group: 'Reticle', label: 'Colour', kind: 'colour', protocol: 19,
     options: [{label: 'Theme', value: 'theme'}, {label: 'White', value: [1, 1, 1]}, {label: 'Yellow', value: [1, 0.86, 0.2]},
               {label: 'Cyan', value: [0.3, 0.88, 1]}, {label: 'Magenta', value: [1, 0.35, 0.85]}, {label: 'Green', value: [0.4, 1, 0.45]}]},
    {key: 'player.reticle_dynamic', category: 'hud', group: 'Reticle', label: 'Opens while moving', kind: 'toggle', protocol: 19},
    // World & characters
    {key: 'graphics.npc_motion', category: 'world', group: 'Characters', label: 'Character motion', kind: 'choice', protocol: 23,
     options: choices(['auto', 'always', 'still', 'off'], ['Automatic (mains power)', 'Always', 'Still poses', 'Hidden'])},
    {key: 'player.reach_grab', category: 'world', group: 'Reach', label: 'Grab', kind: 'slider', range: [1, 100], step: 0.5, format: 'metres', protocol: 19, note: 'Super + button window gestures: carry, resize, roll.'},
    {key: 'player.reach_mount', category: 'world', group: 'Reach', label: 'Mount', kind: 'slider', range: [1, 100], step: 0.5, format: 'metres', protocol: 19, note: 'Snapping windows into mount frames.'},
    {key: 'player.reach_placement', category: 'world', group: 'Reach', label: 'Placement', kind: 'slider', range: [1, 100], step: 0.5, format: 'metres', protocol: 19, note: 'Placing and pocketing, wall mounts, path points.'},
    // Accessibility
    {key: 'graphics.reduced_motion', category: 'accessibility', group: 'Motion', label: 'Reduced motion', kind: 'toggle',
     note: 'No view bob or head tilt, rigid carrying, a still reticle and no HUD animations.'},
    {key: 'input.invert_y', category: 'accessibility', group: 'Input', label: 'Invert mouse Y', kind: 'toggle'},
    {key: 'input.longHoldMs', category: 'accessibility', group: 'Input', label: 'Long hold', kind: 'slider', range: [100, 5000], step: 50, format: 'msInt',
     note: 'How long a key is held for a hold action (Tab for the Director).'},
    // Advanced
    {key: 'graphics.visibility_culling', category: 'advanced', group: 'Rendering', label: 'Visibility culling', kind: 'toggle', protocol: 13,
     note: 'Skips what the world says can\'t be seen from where you are.'},
    {key: 'graphics.exposure', category: 'advanced', group: 'Rendering', label: 'Exposure', kind: 'slider', range: [0.25, 4], step: 0.05, format: 'fixed2'},
    {key: 'graphics.bloom_strength', category: 'advanced', group: 'Rendering', label: 'Bloom strength', kind: 'slider', range: [0, 1], step: 0.05, format: 'fixed2'}
];
// Settings kept by a block of their own (the outline settings), counted with their category.
var BLOCK_KEYS = {display: ['graphics.outline', 'graphics.outline_quality', 'graphics.outline_width_px', 'graphics.outline_colour']};

function store(key) { return key.split('.')[0]; }
function name(key) { return key.slice(key.indexOf('.') + 1); }
function minor(protocol) { var v = String(protocol || '0.1').split('.'); return v[0] === '0' ? Number(v[1]) : 999; }

// The guidance rows from core's guidance settings (Quests.guidanceRows gives their names).
function guidanceRows(rows) {
    return (rows || []).map(function (r) {
        var group = String(r.group || '').toLowerCase();
        return {key: 'guidance.' + r.key, category: 'guidance', group: group.charAt(0).toUpperCase() + group.slice(1), label: r.name, note: r.note,
                kind: r.type === 'enum' ? 'choice' : r.type === 'bool' ? 'toggle' : 'slider',
                step: r.step || 1, labels: r.labels || null, format: 'guidance', unit: r.unit || '', scale: r.scale || 1, protocol: 21};
    });
}

// ctx: {protocol, settings (settings.get), graphics (graphics.get), player (player.get),
//       guidance (guidance.get), keymap (state.keymap), prefs (shell values)}
function available(row, ctx) {
    if (row.protocol && minor(ctx.protocol) < row.protocol) return false;
    var s = store(row.key), n = name(row.key);
    if (s === 'graphics') return !!ctx.graphics && ctx.graphics.config[n] !== undefined;
    if (s === 'player') return !!ctx.player && !!ctx.player.config && ctx.player.config[n] !== undefined;
    if (s === 'guidance') return !!ctx.guidance && !!ctx.guidance.config && ctx.guidance.config[n] !== undefined;
    if (s === 'input') return !!ctx.keymap && !!ctx.keymap.config && ctx.keymap.config[n] !== undefined;
    return true;
}
function presets(ctx) { return minor(ctx.protocol) >= 30 && !!ctx.settings; }

function entry(row, ctx) {
    var s = store(row.key), n = name(row.key);
    if ((s === 'graphics' || s === 'player') && presets(ctx) && ctx.settings.settings[row.key])
        return ctx.settings.settings[row.key];
    if (s === 'graphics') {
        var g = ctx.graphics, requested = g.config[n], overridden = g.overrides && g.overrides[n] !== undefined && g.overrides[n] !== null && n !== 'quality';
        var effective = g.effective && g.effective[n] !== undefined ? g.effective[n] : requested;
        return {value: n === 'npc_motion' ? requested : effective, default: overridden ? null : effective, source: overridden ? 'user' : 'preset'};
    }
    if (s === 'player') {
        var p = ctx.player;
        return {value: p.config[n], default: p.defaults ? p.defaults[n] : p.config[n], source: p.overrides && p.overrides[n] !== undefined ? 'user' : 'preset'};
    }
    if (s === 'guidance') {
        var q = ctx.guidance, over = q.overrides && q.overrides[n] !== undefined;
        return {value: q.config[n], default: q.defaults ? q.defaults[n] : (over ? null : q.config[n]), source: over ? 'user' : 'preset'};
    }
    if (s === 'input') {
        var d = presets(ctx) && ctx.settings.keymapDefaults ? ctx.settings.keymapDefaults[n] : INPUT_DEFAULTS[n];
        var v = ctx.keymap.config[n];
        return {value: v, default: d, source: JSON.stringify(v) === JSON.stringify(d) ? 'preset' : 'user'};
    }
    var value = ctx.prefs ? ctx.prefs[n] : SHELL_DEFAULTS[n];
    return {value: value, default: SHELL_DEFAULTS[n], source: same(value, SHELL_DEFAULTS[n]) ? 'preset' : 'user'};
}
var INPUT_DEFAULTS = {longHoldMs: 1000, scopeVignette: true, invert_y: false, show_area_markers: false};

function same(a, b) {
    if (typeof a === 'number' && typeof b === 'number') return Math.abs(a - b) < 1e-9;
    return JSON.stringify(a) === JSON.stringify(b);
}
function overridden(row, ctx) { return available(row, ctx) && entry(row, ctx).source === 'user'; }
function fromLua(row, ctx) { return available(row, ctx) && entry(row, ctx).source === 'lua'; }

// The rows of a category (guidance rows come from core), or every row matching a search.
function rows(category, ctx, guidance) {
    var all = ROWS.concat(guidanceRows(guidance));
    return all.filter(function (r) { return r.category === category && available(r, ctx); });
}
function search(text, ctx, guidance) {
    var q = String(text || '').trim().toLowerCase();
    if (!q) return [];
    var all = ROWS.concat(guidanceRows(guidance));
    return all.filter(function (r) {
        return available(r, ctx) && (r.label.toLowerCase().indexOf(q) >= 0 || (r.note || '').toLowerCase().indexOf(q) >= 0 ||
                                     r.key.toLowerCase().indexOf(q) >= 0 || (r.group || '').toLowerCase().indexOf(q) >= 0);
    });
}
// Overrides per category: rows, block keys and (controls) the rebound actions.
function counts(ctx, guidance) {
    var out = {}, total = 0;
    CATEGORIES.forEach(function (c) {
        var n = rows(c.id, ctx, guidance).filter(function (r) { return overridden(r, ctx); }).length;
        (BLOCK_KEYS[c.id] || []).forEach(function (k) {
            if (presets(ctx) && ctx.settings.settings[k] && ctx.settings.settings[k].source === 'user') n++;
        });
        if (c.id === 'controls') n += reboundActions(ctx).length;
        out[c.id] = n;
        total += n;
    });
    out.total = total;
    return out;
}
// Keymap actions whose bindings differ from the defaults: [{mode, action}].
function reboundActions(ctx) {
    var d = presets(ctx) && ctx.settings.keymapDefaults, k = ctx.keymap && ctx.keymap.config;
    if (!d || !k) return [];
    var out = [];
    Object.keys(d.modes).forEach(function (mode) {
        Object.keys(d.modes[mode]).forEach(function (action) {
            if (k.modes[mode] && !same(k.modes[mode][action], d.modes[mode][action])) out.push({mode: mode, action: action});
        });
    });
    return out;
}

// The request that sets or resets a row: {type: 'core'|'graphics'|'player'|'guidance'|'input'|'shell', ...}.
function setRequest(row, value, ctx) {
    var s = store(row.key), n = name(row.key), p = {};
    if ((s === 'graphics' || s === 'player') && presets(ctx)) { p[row.key] = value; return {type: 'core', params: {set: p}}; }
    p[n] = value;
    if (s === 'input') { var config = JSON.parse(JSON.stringify(ctx.keymap.config)); config[n] = value; return {type: 'input', config: config}; }
    return {type: s, patch: p};
}
function resetRequest(row, ctx) {
    var s = store(row.key), n = name(row.key), p = {};
    if ((s === 'graphics' || s === 'player') && presets(ctx)) return {type: 'core', params: {reset: [row.key]}};
    if (s === 'input') return setRequest(row, entry(row, ctx).default, ctx);
    if (s === 'shell') { p[n] = SHELL_DEFAULTS[n]; return {type: 'shell', patch: p}; }
    p[n] = null;
    return {type: s, patch: p};
}
// Reset all: every core override and the keymap (settings.set resetAll), the guidance
// overrides and this shell's preferences. The preset stays.
function resetAllRequests(ctx) {
    var out = [];
    if (presets(ctx)) out.push({type: 'core', params: {resetAll: true}});
    else {
        if (ctx.graphics && ctx.graphics.overrides) {
            var g = {};
            Object.keys(ctx.graphics.overrides).forEach(function (k) { if (k !== 'quality') g[k] = null; });
            if (Object.keys(g).length) out.push({type: 'graphics', patch: g});
        }
        if (ctx.player && ctx.player.overrides && Object.keys(ctx.player.overrides).length) {
            var p = {};
            Object.keys(ctx.player.overrides).forEach(function (k) { p[k] = null; });
            out.push({type: 'player', patch: p});
        }
    }
    if (ctx.guidance && ctx.guidance.overrides && Object.keys(ctx.guidance.overrides).length) {
        var q = {};
        Object.keys(ctx.guidance.overrides).forEach(function (k) { q[k] = null; });
        out.push({type: 'guidance', patch: q});
    }
    out.push({type: 'shell', patch: JSON.parse(JSON.stringify(SHELL_DEFAULTS))});
    return out;
}

function format(row, v) {
    if (v === null || v === undefined) return row.kind === 'cap' ? 'Automatic' : '—';
    if (row.kind === 'toggle') return onOff(v);
    if (row.kind === 'choice' || row.kind === 'colour') {
        var o = (row.options || []).find(function (x) { return same(x.value, v); });
        return o ? o.label : (row.labels && row.labels[v]) || String(v);
    }
    switch (row.format) {
    case 'fps': return Math.round(v) + ' FPS';
    case 'percent': return Math.round(v * 100) + '%';
    case 'fixed2': return Number(v).toFixed(2);
    case 'degrees': return Math.round(v) + '°';
    case 'degrees1': return Number(v).toFixed(1) + '°';
    case 'speed': return Number(v).toFixed(1) + ' m/s';
    case 'metres': return Number(v).toFixed(1) + ' m';
    case 'ms': return Math.round(v * 1000) + ' ms';
    case 'msInt': return Math.round(v) + ' ms';
    case 'px': return (Math.round(v) === Number(v) ? Number(v).toFixed(0) : Number(v).toFixed(1)) + ' px';
    case 'watts': return Math.round(v) + ' W';
    case 'guidance': return (Math.round(v * (row.scale || 1) * 10) / 10) + (row.unit ? ' ' + row.unit : '');
    default: return String(Math.round(v * 100) / 100);
    }
}
// A slider's range: core's when it publishes one (player and guidance ranges), else the row's.
function range(row, ctx) {
    var s = store(row.key), n = name(row.key);
    if (s === 'player' && ctx.player && ctx.player.ranges && ctx.player.ranges[n]) return ctx.player.ranges[n];
    if (s === 'guidance' && ctx.guidance && ctx.guidance.ranges && ctx.guidance.ranges[n]) return ctx.guidance.ranges[n];
    return row.range || [0, 1];
}
function options(row, ctx) {
    if (row.options) return row.options;
    var s = store(row.key), n = name(row.key);
    if (s === 'guidance' && ctx.guidance && ctx.guidance.options && ctx.guidance.options[n])
        return ctx.guidance.options[n].map(function (o) { return {value: o, label: row.labels && row.labels[o] ? row.labels[o] : o}; });
    return [];
}
// The preset bar: presets with their names (IPC 0.30), the selected one.
function presetList(ctx) { return presets(ctx) ? ctx.settings.presets.map(function (p) { return {id: p.id, name: p.name, description: p.description}; }) : []; }
// What switching to `preset` would change (settings at their default whose default differs).
function presetChanges(ctx, preset) {
    if (!presets(ctx)) return [];
    var target = ctx.settings.presets.find(function (p) { return p.id === preset; });
    if (!target) return [];
    var out = [];
    Object.keys(ctx.settings.settings).forEach(function (k) {
        var e = ctx.settings.settings[k];
        if (e.source === 'preset' && target.defaults[k] !== undefined && !same(target.defaults[k], e.default)) out.push(k);
    });
    return out;
}
