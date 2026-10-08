import QtQuick
import Quickshell
import Quickshell.Io
import "theme"
pragma Singleton

QtObject {
    id: root

    property string status: 'connecting'
    property string error: ''
    property var methods: []
    property var missing: []
    property var capabilities: []
    property var state: null
    property double revision: 0
    property string output: ''
    property string screenName: ''
    property string lease: ''
    onLeaseChanged: { if (lease) Qt.callLater(applyCoreStyle); }
    function applyCoreStyle() {
        action('overlay.style', {style:{fontFamily:Tokens.mono,waypointColor:[Tokens.accent.r,Tokens.accent.g,Tokens.accent.b],routeColor:[Tokens.accent.r,Tokens.accent.g,Tokens.accent.b],labelColor:[Tokens.text.r,Tokens.text.g,Tokens.text.b],promptColor:[Tokens.gold.r,Tokens.gold.g,Tokens.gold.b]}});
    }
    property Connections coreThemeConnection: Connections {
        target: Tokens
        function onLightChanged() { root.applyCoreStyle(); }
    }
    property bool director: false
    property int tab: 0
    property var lastCapturedInput: null
    signal beginInputCapture(string mode, string action, int slot)
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
        if ((protocol === '0.2' || (protocol === '0.3' || protocol === '0.4')) && available('travel.start'))
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
        case 'transition.clear':
            warpActive = false;
            pendingArrival = null;
            arrivalHold.stop();
            break;
        case 'transition':
            transitionEvent(msg);
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
            state = msg.state;
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
            var nextMap = spatial ? spatial.map : null;
            if ((!mapData && nextMap) || (mapData && (!nextMap || mapData.sha256 !== nextMap.sha256))) mapData = nextMap;
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
            if (zoneKey !== currentZoneKey) {
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
            samples = samples.concat([{
                "at": Date.now(),
                "position": state.movement.position,
                "heading": angle
            }]).slice(-12);
            break;
        case 'action':
            if (msg.method === 'input.preview' || msg.method === 'input.get') inputFeedback(msg.result);
            break;
        case 'menu.panel':
            if (msg.panel === 'map') tab = 0;
            break;
        case 'director':
            director = msg.open;
            break;
        case 'notice':
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
        case 'action':
            notice(({
                "runtime.exit": 'Returned to the ordinary desktop.',
                "waypoint.set": 'Waypoint set. Your next destination is marked.',
                "camera.set": 'Arrived at the selected location.',
                "travel.start": 'Core travel started.',
                "travel.cancel": 'Core travel cancelled.',
                "surface.focus": 'Surface focus accepted.',
                "world.load": 'World ready.',
                "movement.set": 'Movement mode updated.'
            })[msg.method] || 'Action accepted.', 'info');
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
