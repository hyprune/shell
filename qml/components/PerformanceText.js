// A render-pass measurement must never masquerade as an isolated effect cost.
function effectCost(performance, timings, key) {
    var control = performance && performance.controls && performance.controls[key];
    if (control)
        return typeof control.gpuMs === 'number' ? control.gpuMs.toFixed(2) + ' ms' : '';
    var costs = timings.gpuEffectsMs || {};
    return (key === 'bloom' || key === 'sky') && typeof costs[key] === 'number'
        ? costs[key].toFixed(2) + ' ms' : '';
}

function worldShading(performance, timings, labels) {
    var controls = performance && performance.controls;
    var costs = performance && performance.costsMs || timings.gpuEffectsMs || {};
    var ms = costs.world_shading_shared;
    var keys = ['anisotropy', 'fog', 'ambient_occlusion', 'normal_maps', 'reflections', 'specular'];
    if (controls) {
        keys = keys.filter(function(key) {
            var c = controls[key];
            if (!c || c.sharedPass !== 'world_shading_shared') return false;
            if (typeof ms !== 'number' && typeof c.passGpuMs === 'number') ms = c.passGpuMs;
            return true;
        });
    }
    return 'World shading ' + (typeof ms === 'number' ? ms.toFixed(2) + ' ms' : 'timing unavailable')
        + (keys.length ? ', shared by:\n' + keys.map(function(key) { return labels[key]; }).join(' · ') : '');
}

function policy(performance) {
    if (!performance) return 'Live renderer switching and power policy are unavailable on this core version.';
    if (performance.status === 'warming') return 'Switching renderer…';
    var source = {'usb-c':'On USB-C power', 'full-ac':'On AC power', 'limited-ac':'On limited AC power', 'battery':'On battery power'}[performance.profile] || 'Power source unknown';
    var limits = [];
    if (performance.capW > 0) limits.push(performance.capW + ' W');
    if (performance.targetFPS > 0) limits.push(performance.targetFPS + ' FPS');
    var sentence = source + (limits.length ? ': offload capped at ' + limits.join(' / ') : '') + '.';
    var reasons = {
        'auto requires qualified full AC':'Automatic offload needs full AC power.',
        'power supply unknown':'Offload is paused until the power source is known.',
        'battery discharging on AC':'Offload is paused while the battery is discharging.',
        'edited world transforms use local renderer':'World editing currently uses the local renderer.'
    };
    if (reasons[performance.reason]) sentence += ' ' + reasons[performance.reason];
    else if (performance.reason && ['off','ready','inactive','admitted','warming'].indexOf(performance.reason) < 0)
        sentence += ' Offload unavailable: ' + performance.reason + '.';
    return sentence;
}

// Core renders on demand: while nothing changes it renders no new world frames
// (timings.idleFrames counts cached re-presentations). Idle means two successive
// graphics.get samples saw no new rendered frame, so FPS would read near zero.
function idle(previous, current) {
    return !!(previous && current && typeof current.idleFrames === 'number' &&
              typeof previous.renderedFrames === 'number' && typeof current.renderedFrames === 'number' &&
              current.renderedFrames === previous.renderedFrames && current.idleFrames >= (previous.idleFrames || 0));
}

function stats(fps, frameMs, renderScale, isIdle) {
    if (fps < 0 && !isIdle) return 'FRAME TELEMETRY UNAVAILABLE';
    var scale = renderScale >= 0 ? Math.round(renderScale * 100) + '% SCALE' : '—';
    if (isIdle) return 'IDLE   /   no changes   /   ' + scale;
    return Math.round(fps) + ' FPS   /   ' + (frameMs >= 0 ? frameMs.toFixed(1) + ' ms' : '—') + '   /   ' + scale;
}

// IPC 0.16 graphics.upscaler labels; timings.upscaler = {requested, active, error}.
function upscalerName(value) {
    return value === null || value === undefined ? 'Preset' : value === 'fsr1' ? 'FSR 1' : value === 'bilinear' ? 'Bilinear' : String(value);
}

function upscaler(state) {
    if (!state || !state.active) return 'Active: —';
    var text = 'Active: ' + upscalerName(state.active);
    if (state.requested && state.requested !== state.active) text += state.error ? ' (FSR 1 unavailable)' : ' (native scale)';
    return text;
}
