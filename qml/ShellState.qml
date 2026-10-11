import QtQuick
import Quickshell
import Quickshell.Io
import "theme"
import "HudManipulation.js" as Manipulation
import "PlayerSettings.js" as PlayerSettings
import "Blueprint.js" as Blueprint
import "DirectorModel.js" as DirectorModel
pragma Singleton

QtObject {
    id: root

    property string status: 'connecting'
    property string error: ''
    property var methods: []
    property var missing: []
    property var capabilities: []
    property var state: null
    property var hudFrame: null
    property var hudPose: null
    property var hudTool: null
    property var manipulationPreview: null
    signal contentFeedback(var sample)
    property string readyText: ''
    property string readyWorld: ''
    property Timer readyTimer: Timer { interval:7000; onTriggered:root.readyText='' }
    function showReady(text) { if (!state || !state.runtime.active) { readyText=text;readyTimer.restart(); } }
    property string banner: ''
    property Timer bannerTimer: Timer { interval: 2200; onTriggered: root.banner = '' }
    function showBanner(text) { banner = text; if (!warpActive) bannerTimer.restart(); }
    onWarpActiveChanged: { if (warpActive) bannerTimer.stop(); else if (banner) bannerTimer.restart(); }
    function preference(patch) { send({type:'preferences',patch:patch}); }
    function setConcept(name) { if (['Adventure','Instrument','Minimal'].indexOf(name) < 0) return; Tokens.hudConcept=name; preference({concept:name}); showBanner(name.toUpperCase()); }
    property Timer graphicsPoll: Timer { interval: 1000; running: root.active && root.available('graphics.get'); repeat: true; triggeredOnStart: true; onTriggered: root.action('graphics.get',{}) }
    property var camera: null
    property var outline: null
    function supportsProtocol(minor) { var v=protocol.split('.'); return v[0]==='0' && Number(v[1])>=minor; }
    readonly property bool authoredCamera: supportsProtocol(13) && (!camera || camera.held)
    property Timer cameraPoll: Timer { interval:250; running:root.active && root.supportsProtocol(13) && root.available('camera.get'); repeat:true; triggeredOnStart:true; onTriggered:root.action('camera.get',{}) }
    property Timer outlinePoll: Timer { interval:1000; running:root.active && root.director && root.tab === 7 && root.supportsProtocol(13) && root.available('atmosphere.get'); repeat:true; triggeredOnStart:true; onTriggered:root.refreshOutline() }
    function refreshOutline() { if (state && state.world) send({type:'outline.get',worldId:state.world.id}); }
    function patchOutline(patch) { if (state && state.world) send({type:'outline.patch',worldId:state.world.id,patch:patch}); }
    property var graphics: null
    property var previousTimings: null // prior graphics.get sample (idle detection)
    property var menuHold: null
    property double revision: 0
    property string output: ''
    property string screenName: ''
    property string lease: ''
    onLeaseChanged: { if (lease && !available('hud.subscribe')) Qt.callLater(applyCoreStyle); }
    function protocolMinor() { var v=protocol.split('.'); return v[0]==='0' ? Number(v[1]) : 0; }
    // IPC 0.19 adds the core reticle colours (HUD foreground, positive, warning).
    function coreStyle() {
        return PlayerSettings.overlayStyle({mono:Tokens.mono,accent:Tokens.accent,text:Tokens.text,gold:Tokens.gold,
                                            reticle:Tokens.hudForeground,positive:Tokens.hudPositive,warning:Tokens.hudWarning}, protocolMinor());
    }
    function applyCoreStyle() { action('overlay.style', {style:coreStyle()}); }
    property Connections coreThemeConnection: Connections {
        target: Tokens
        function onLightChanged() { root.applyCoreStyle(); }
        function onHudConceptChanged() { if (root.supportsProtocol(19) && root.lease) Qt.callLater(root.applyCoreStyle); }
        function onSkinChanged() { if (root.supportsProtocol(19) && root.lease) Qt.callLater(root.applyCoreStyle); }
    }
    // IPC 0.19 player settings: player.get result (config/defaults/overrides/options/ranges).
    property var player: null
    property var playerPreview: null // DEV ONLY (preview IPC): settings shown without a 0.19 core
    readonly property bool playerSupported: (supportsProtocol(19) && available('player.get')) || (dev && !!playerPreview)
    readonly property var playerSettings: dev && playerPreview ? playerPreview : player
    property var playerPending: ({})
    function refreshPlayer() { if (supportsProtocol(19)) action('player.get', {}); }
    // Slider drags coalesce into one player.set per 120 ms; nulls remove overrides.
    readonly property bool playerEditable: available('player.set') || (dev && !!playerPreview)
    function patchPlayer(patch) {
        if (dev && playerPreview) { // DEV ONLY: preview applies locally (nulls restore defaults)
            var next = JSON.parse(JSON.stringify(playerPreview));
            Object.keys(patch).forEach(k => { next.config[k] = patch[k] === null ? next.defaults[k] : patch[k]; });
            playerPreview = next;
            return;
        }
        playerPending = Object.assign({}, playerPending, patch); playerCommit.restart();
    }
    property Timer playerCommit: Timer { interval: 120; onTriggered: { if (Object.keys(root.playerPending).length && root.supportsProtocol(19)) root.action('player.set', {patch:root.playerPending}); root.playerPending = ({}); } }
    // IPC 0.20 pocket: put a window in / take it out; the latest result shows in Surfaces.
    property var surfaceFeedback: null // {surfaceId, level, text, at}
    property string pocketTarget: ''
    property Timer surfaceFeedbackTimer: Timer { onTriggered: root.surfaceFeedback = null }
    function pocket(surfaceId, into) {
        var method = into ? 'surface.pocket' : 'surface.unpocket';
        if (!available(method)) return;
        pocketTarget = surfaceId; surfaceFeedback = null;
        action(method, {surfaceId: surfaceId});
    }
    function pocketFeedback(method, result, error) {
        var text = error !== undefined ? DirectorModel.pocketError(method, error) : null;
        var info = text ? {level: 'warning', text: text} : DirectorModel.pocketResult(method, result);
        if (!info) return;
        surfaceFeedback = {surfaceId: pocketTarget, level: info.level, text: info.text, at: Date.now()};
        surfaceFeedbackTimer.interval = info.level === 'warning' ? 12000 : 5000; surfaceFeedbackTimer.restart();
        if (method === 'surface.unpocket' && result && result.placed === false) showBanner('AIM AND CLICK TO PLACE');
    }
    property bool director: false
    // IPC 0.17 debug capture note: the capture awaiting a note ('' = no prompt).
    property string notePrompt: ''
    property string noteText: ''
    function cleanNote(text) { return String(text).replace(/[\u0000-\u001f\u007f-\u009f]/g, ' ').slice(0, 1000); }
    function submitNote() { if (notePrompt) send({type: 'capture.note', captureId: notePrompt, note: cleanNote(noteText), release: true}); }
    function dismissNote() { if (notePrompt) send({type: 'capture.dismiss', captureId: notePrompt}); }
    property int tab: 0
    property var lastCapturedInput: null
    signal beginInputCapture(string mode, string action, int slot)
    signal browseSettings(int section)
    signal scrollSettings(real fraction)
    signal saveInputDraft()
    signal inputFeedback(var result)
    signal inputCapture(var result)
    property var worlds: []
    property var presentation: ({
    })
    property var notices: []
    property string zone: ''
    property string zoneSubtitle: ''
    property string currentZoneKey: ''
    property var samples: []
    property var projectionSamples: []
    property var markers: []
    property var pose: [0, 0, 0]
    property real heading: 0
    property real clockMs: Date.now()
    property string selectedPlace: ''
    property string protocol: '0.2'
    // Matches VERSION (checked by tests/test_brand.py).
    readonly property string shellVersion: '0.2.0'
    property var transition: ({
        "id": '',
        "phase": 'idle',
        "progress": 0,
        "to": {
            "id": '',
            "name": '',
            "subtitle": ''
        }
    })
    property bool warpActive: false
    property var pendingArrival: null
    property Timer arrivalHold
    readonly property bool live: status === 'live' && state !== null
    readonly property bool active: live && state.runtime.active && lease !== ''
    readonly property bool dev: presentation.dev === true || Quickshell.env('HYPRUNE_DEV_AUTOMATION') === '1'
    readonly property var waypointState: state && state.location ? state.location.waypoint : null
    readonly property var world: state && state.world ? worlds.find((w) => {
        return w.id === state.world.id;
    }) || null : null
    readonly property var spatial: state && state.spatial ? state.spatial : null
    property var mapData: null
    property var corePlaces: []
    readonly property string worldName: spatial && spatial.world ? spatial.world.name : world ? world.name : (state && state.world ? state.world.id : 'No world')
    readonly property var places: spatial && spatial.world ? corePlaces : world ? world.spawns.map((p, i) => {
        return ({
            "id": p.id,
            "name": p.id.replace(/-/g, ' '),
            // Core M1 spawns place the capsule feet; Target uses eye position.
            "position": [p.pose.position[0], p.pose.position[1] + 1.7, p.pose.position[2]],
            "index": i
        });
    }) : []
    readonly property var surfaces: state ? state.surfaces : []
    readonly property var workspaces: {
        var locations = state && state.workspaces ? state.workspaces.locations : [];
        var entries = surfaces.filter((s) => s.kind === 'workspace').map((s) => {
            var id = Number(s.id.replace('workspace-', ''));
            var home = locations.find((w) => w.id === id);
            return ({id:id, surfaceId:s.id, title:s.title, kind:'workspace', focused:s.focused, worldId:home ? home.worldId : '', desktop:!home});
        });
        locations.forEach((w) => { if (!entries.some((e) => e.id === w.id)) entries.push({id:w.id,title:w.label,kind:'workspace',worldId:w.worldId,desktop:false}); });
        return entries;
    }
    property Socket socket
    property Timer retry
    property Timer frames
    property Timer zoneTimer
    property Connections screens

    signal warpStarted(string sequence)

    function arrive() {
        if (pendingArrival && state && state.world && state.world.id === pendingArrival.to.id && (!pendingArrival.revision || revision >= pendingArrival.revision)) {
            transition = pendingArrival;
            pendingArrival = null;
            arrivalHold.restart();
            zone = transition.to.name;
            zoneSubtitle = transition.to.subtitle;
            zoneTimer.restart();
        }
    }

    function transitionEvent(event) {
        if (event.phase === 'departing' && (event.id !== transition.id || !warpActive)) {
            transition = event;
            warpActive = true;
            pendingArrival = null;
            arrivalHold.stop();
            warpStarted(event.id);
        } else if (event.id === transition.id && (event.phase === 'failed' || event.indeterminate || event.progress >= transition.progress)) {
            if (event.phase === 'arrived') {
                pendingArrival = event;
                arrive();
            } else {
                transition = event;
                if (event.phase === 'failed') {
                    notice('Destination unavailable. Remaining in the current world.', 'warning');
                    warpActive = false;
                }
            }
        }
    }

    function available(method) {
        return live && methods.indexOf(method) >= 0;
    }

    function send(value) {
        if (socket.connected)
            socket.write(JSON.stringify(value) + '\n');

    }

    function action(method, params) {
        if (available(method))
            send({
            "type": 'action',
            "method": method,
            "params": params
        });

    }

    function waypoint(point) {
        if (available('waypoint.set'))
            action('waypoint.set', {
            "id": point.id,
            "target": {"position": point.position},
            "label": point.name
        });

    }

    function travel(point) {
        if (available('travel.start'))
            action('travel.start', {
                "to": {"position": point.position},
                "durationMs": Tokens.reducedMotion ? 0 : 5800
            });
        else
            notice('Travel is unavailable. Arrive at spawn reloads the world here.', 'warning');
    }

    function close() {
        director = false;
        send({
            "type": 'close'
        });
    }

    function reportScreens() {
        send({
            "type": 'screens',
            "names": Quickshell.screens.map((s) => {
                return s.name;
            })
        });
    }

    function notice(message, level) {
        notices = [{
            "message": message,
            "level": level || 'info',
            "at": Date.now()
        }].concat(notices).slice(0, 4);
    }

    function receive(msg) {
        switch (msg.type) {
        case 'world.style': Tokens.worldStyle=msg.value; break;
        case 'hud.bound': applyCoreStyle(); break;
        case 'hud.frame': hudFrame = msg.value; break;
        case 'hud.pose':
            hudPose = msg.value;
            hudTool = {slot:msg.value.tool,subtype:msg.value.subtype};
            samples = samples.concat([{at:Date.now(),position:msg.value.position,heading:msg.value.heading*180/Math.PI}]).slice(-12);
            if (msg.value.zone && currentZoneKey !== msg.value.worldId+'/'+msg.value.zone.id) {
                currentZoneKey = msg.value.worldId+'/'+msg.value.zone.id;
                zone = msg.value.zone.homeName; zoneSubtitle = msg.value.zone.worldName; zoneTimer.restart();
            }
            break;
        case 'tool.changed': hudTool = msg.value; break;
        case 'zone.entered': zone=msg.value.zone.homeName;zoneSubtitle=msg.value.zone.worldName;zoneTimer.restart();break;
        case 'preferences':
            Tokens.hudConcept = msg.value.concept;
            Tokens.hudCurved = msg.value.curved;
            Tokens.hudCurvature = msg.value.curvature;
            Tokens.hudResource = msg.value.resource;
            Tokens.worldStyles = msg.value.worldStyles;
            break;
        case 'transition.clear':
            warpActive = false;
            pendingArrival = null;
            arrivalHold.stop();
            break;
        case 'transition':
            transitionEvent(msg);
            break;
        case 'menu.hold':
            menuHold = msg.hold;
            break;
        case 'connection':
            status = msg.status;
            error = msg.message || '';
            if (status !== 'live') {
                director = false;
                warpActive = false;
                pendingArrival = null;
                arrivalHold.stop();
                samples = [];
                projectionSamples = [];
                markers = [];
                camera = null; outline = null; graphics = null; player = null; previousTimings = null; hudFrame = null; hudPose = null; hudTool = null;
                menuHold = null; readyText=''; readyWorld='';readyTimer.stop();
                methods = [];
                capabilities = [];
            }
            break;
        case 'hello':
            protocol = msg.protocol;
            methods = msg.methods;
            missing = msg.missing;
            capabilities = msg.capabilities;
            break;
        case 'catalog':
            worlds = msg.worlds;
            break;
        case 'presentation':
            presentation = msg;
            break;
        case 'state':
            if (!state || !state.world || !msg.state || !msg.state.world || state.world.id !== msg.state.world.id) { camera = null; outline = null; }
            if (state && msg.state && state.workspaces && msg.state.workspaces && state.workspaces.currentId !== msg.state.workspaces.currentId) showBanner('WORKSPACE FOCUSED');
            var contentChange=Manipulation.changedContent(state,msg.state);
            state = msg.state;
            if (contentChange) contentFeedback(contentChange);
            revision = msg.revision;
            lease = msg.lease || '';
            output = msg.output || '';
            screenName = msg.screen || '';
            if (!state) {
                director = false;
                samples = [];
                mapData = null; corePlaces = [];
                break;
            }
            if (!state.runtime.active || !lease) {
                warpActive = false;
                pendingArrival = null;
                arrivalHold.stop();
            }
            if (state.runtime.active) {readyText='';readyTimer.stop();}
            else if (state.world && state.world.id!==readyWorld) showReady('HYPRUNE READY · '+worldName+' · Loaded and ready to enter');
            if (state.world) readyWorld=state.world.id;
            var nextMap = spatial ? spatial.map : null;
            if (Blueprint.mapKey(mapData) !== Blueprint.mapKey(nextMap)) mapData = nextMap;
            var nextPlaces = spatial && spatial.world ? spatial.world.places : [];
            if (JSON.stringify(corePlaces) !== JSON.stringify(nextPlaces)) corePlaces = nextPlaces;
            if (spatial && spatial.projection && spatial.projection.outputId === output && state.world && spatial.projection.worldId === state.world.id) {
                var projected = spatial.projection.markers.filter((m) => !m.occluded).map((m) => ({id:m.id,name:m.label,distance:m.distance,x:m.x,y:m.y}));
                projectionSamples = projectionSamples.concat([{at:Date.now(),markers:projected}]).slice(-12);
            } else if ((protocol === '0.3' || protocol === '0.4')) { projectionSamples = []; markers = []; }
            var zones = state.location ? state.location.zones : (world ? world.zones : []);
            var position = state.movement.position;
            var entered = (zones || []).find((z) => position.every((v, i) => v >= z.bounds.min[i] && v <= z.bounds.max[i]));
            var zoneKey = entered && state.world ? state.world.id + '/' + entered.id : '';
            if (!hudPose && zoneKey !== currentZoneKey) {
                currentZoneKey = zoneKey;
                if (entered) {
                    zone = entered.name;
                    zoneSubtitle = worldName.toUpperCase();
                    zoneTimer.restart();
                }
            }
            if (state.keymap && state.keymap.capture && state.keymap.capture.status === 'captured') inputCapture(state.keymap.capture);
            arrive();
            var q = state.movement.orientation;
            var angle = -Math.atan2(2 * (q[3] * q[1] + q[0] * q[2]), 1 - 2 * (q[1] * q[1] + q[2] * q[2])) * 180 / Math.PI;
            if (!hudPose) samples = samples.concat([{
                "at": Date.now(),
                "position": state.movement.position,
                "heading": angle
            }]).slice(-12);
            break;
        case 'outline':
            if (state && state.world && msg.value.worldId === state.world.id) outline = msg.value;
            break;
        case 'action':
            if (msg.method === 'camera.get') camera = msg.result;
            if (msg.method === 'waypoint.set') showBanner('WAYPOINT SET');
            if (msg.method === 'graphics.get' || msg.method === 'graphics.set') {
                previousTimings = graphics ? graphics.timings : null;
                graphics = msg.result;
            }
            if (msg.method === 'input.preview' || msg.method === 'input.get') inputFeedback(msg.result);
            if (msg.method === 'player.get' || msg.method === 'player.set') player = msg.result;
            if (msg.method === 'surface.pocket' || msg.method === 'surface.unpocket') pocketFeedback(msg.method, msg.result);
            break;
        case 'menu.panel':
            if (msg.panel === 'map') tab = 0;
            break;
        case 'director':
            director = msg.open;
            break;
        case 'capture.prompt':
            if (msg.captureId) {
                // U again while the prompt is open: the previous capture keeps its text as-is.
                if (msg.previous) send({type: 'capture.note', captureId: msg.previous, note: cleanNote(noteText), release: false});
                noteText = '';
                notePrompt = msg.captureId;
            } else {
                // The Director replacing the prompt keeps typed text; Esc and loss keep nothing.
                if (msg.reason === 'director' && notePrompt && noteText !== '')
                    send({type: 'capture.note', captureId: notePrompt, note: cleanNote(noteText), release: false});
                notePrompt = '';
                noteText = '';
            }
            break;
        case 'notice':
            if (msg.code === 'placement.pocketed') {showBanner('POCKETED '+msg.message.replace(/^pocketed\s*/i,''));break;}
            if (msg.code === 'runtime.ready') {showReady(msg.message);break;}
            if (msg.code === 'shell.action' && (msg.method === 'surface.pocket' || msg.method === 'surface.unpocket')) pocketFeedback(msg.method, null, msg.message);
            notice(msg.message, msg.level);
            break;
        case 'zone':
            if (dev) {
                zone = msg.name;
                zoneSubtitle = msg.subtitle;
                zoneTimer.restart();
            }
            break;
        case 'projection':
            if (dev)
                projectionSamples = projectionSamples.concat([{
                "at": Date.now(),
                "markers": msg.markers
            }]).slice(-12);

            break;
        case 'dev.tab':
            if (dev)
                tab = msg.index;

            break;

        }
    }

    function interpolate() {
        clockMs = Date.now();
        notices = notices.filter((n) => {
            return clockMs - n.at < 7000;
        });
        if (projectionSamples.length && clockMs - projectionSamples[projectionSamples.length - 1].at > 500) { projectionSamples = []; markers = []; }
        if (projectionSamples.length) {
            var ptarget = clockMs - (Tokens.reducedMotion ? 0 : 70);
            var pa = projectionSamples[0], pb = projectionSamples[projectionSamples.length - 1];
            for (var j = 1; j < projectionSamples.length; j++) if (projectionSamples[j].at >= ptarget) {
                pa = projectionSamples[j - 1];
                pb = projectionSamples[j];
                break;
            }
            var pt = Tokens.reducedMotion || pa.at === pb.at ? 1 : Math.max(0, Math.min(1, (ptarget - pa.at) / (pb.at - pa.at)));
            markers = pb.markers.map((m) => {
                var prev = pa.markers.find((v) => {
                    return v.id === m.id;
                }) || m;
                return {
                    "id": m.id,
                    "name": m.name,
                    "distance": m.distance,
                    "x": prev.x + (m.x - prev.x) * pt,
                    "y": prev.y + (m.y - prev.y) * pt
                };
            });
        }
        if (!samples.length)
            return ;

        var target = clockMs - (Tokens.reducedMotion ? 0 : 70);
        var a = samples[0], b = samples[samples.length - 1];
        for (var i = 1; i < samples.length; i++) if (samples[i].at >= target) {
            a = samples[i - 1];
            b = samples[i];
            break;
        }
        var t = Tokens.reducedMotion || a.at === b.at ? 1 : Math.max(0, Math.min(1, (target - a.at) / (b.at - a.at)));
        pose = a.position.map((v, i) => {
            return v + (b.position[i] - v) * t;
        });
        var delta = ((b.heading - a.heading + 540) % 360) - 180;
        heading = (a.heading + delta * t + 360) % 360;
    }

    arrivalHold: Timer {
        interval: 1400
        onTriggered: root.warpActive = false
    }

    socket: Socket {
        path: Quickshell.env('HYPRUNE_BRIDGE_SOCKET')
        connected: true
        onConnectedChanged: {
            if (connected)
                root.reportScreens();
            else
                root.menuHold = null;

        }

        parser: SplitParser {
            onRead: (data) => {
                try {
                    root.receive(JSON.parse(data));
                } catch (e) {
                    console.warn('Presentation:', e);
                }
            }
        }

    }

    retry: Timer {
        interval: 1000
        repeat: true
        running: true
        onTriggered: {
            if (!root.socket.connected)
                root.socket.connected = true;

        }
    }

    frames: Timer {
        interval: 16
        repeat: true
        running: root.active
        onTriggered: root.interpolate()
    }

    zoneTimer: Timer {
        interval: 4200
        onTriggered: root.zone = ''
    }

    screens: Connections {
        function onScreensChanged() {
            root.reportScreens();
        }

        target: Quickshell
    }

}
