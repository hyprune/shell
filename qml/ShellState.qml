import QtQuick
import Quickshell
import Quickshell.Io
import "theme"
import "HudManipulation.js" as Manipulation
import "PlayerSettings.js" as PlayerSettings
import "Blueprint.js" as Blueprint
import "DirectorModel.js" as DirectorModel
import "Quests.js" as Quests
import "Objects.js" as Objects
import "Shapes.js" as Shapes
import "Npcs.js" as Npcs
import "Companion.js" as Companion
import "Library.js" as Library
import "Sources.js" as Sources
import "Import.js" as Import
import "Builder.js" as Builder
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
    property Timer outlinePoll: Timer { interval:1000; running:root.active && root.director && root.tab === root.tabSettings && root.settingsCategory === 'display' && root.supportsProtocol(13) && root.available('atmosphere.get'); repeat:true; triggeredOnStart:true; onTriggered:root.refreshOutline() }
    // ---- IPC 0.30 settings: one preset for every graphics and player setting, overrides on top ----
    property var settingsState: null // settings.get / settings.set result
    property string settingsCategory: 'display'
    property string settingsSearch: ''      // the Settings search text (dev hooks set it too)
    property bool settingsConfirm: false   // the reset-all confirmation is open
    readonly property bool presetsSupported: supportsProtocol(30) && available('settings.get')
    function refreshSettings() { if (presetsSupported) action('settings.get', {}); }
    property Timer settingsPoll: Timer { interval: 1000; running: root.active && root.director && root.tab === root.tabSettings && root.presetsSupported; repeat: true; triggeredOnStart: true; onTriggered: root.refreshSettings() }
    // Slider drags coalesce into one settings.set per 120 ms.
    property var settingsPending: ({})
    property Timer settingsCommit: Timer { interval: 120; onTriggered: { if (Object.keys(root.settingsPending).length) root.action('settings.set', {set: root.settingsPending}); root.settingsPending = ({}); } }
    function setPreset(id) { if (presetsSupported) action('settings.set', {preset: id}); }
    // A SettingsModel request: set or reset a setting in its store.
    function settingRequest(req) {
        if (!req) return;
        if (req.type === 'core') {
            if (req.params.set && Object.keys(req.params).length === 1) { settingsPending = Object.assign({}, settingsPending, req.params.set); settingsCommit.restart(); }
            else action('settings.set', req.params);
        } else if (req.type === 'graphics') action('graphics.set', {patch: req.patch});
        else if (req.type === 'player') patchPlayer(req.patch);
        else if (req.type === 'guidance') patchGuidance(req.patch);
        else if (req.type === 'input') action('input.set', {config: req.config});
        else if (req.type === 'shell') applyPreferences(req.patch);
    }
    // Shell presentation preferences: shown at once, saved by the bridge (shell.json).
    function applyPreferences(patch) {
        if (patch.concept !== undefined) Tokens.hudConcept = patch.concept;
        if (patch.resource !== undefined) Tokens.hudResource = patch.resource;
        if (patch.worldStyles !== undefined) Tokens.worldStyles = patch.worldStyles;
        if (patch.curved !== undefined) Tokens.hudCurved = patch.curved;
        if (patch.curvature !== undefined) Tokens.hudCurvature = patch.curvature;
        if (patch.theme !== undefined) Tokens.light = patch.theme === 'paper';
        preference(patch);
    }
    readonly property var shellPreferences: ({concept: Tokens.hudConcept, resource: Tokens.hudResource, worldStyles: Tokens.worldStyles,
                                              curved: Tokens.hudCurved, curvature: Tokens.hudCurvature, theme: Tokens.light ? 'paper' : 'night'})
    function refreshOutline() { if (state && state.world) send({type:'outline.get',worldId:state.world.id}); }
    function patchOutline(patch) { if (state && state.world) send({type:'outline.patch',worldId:state.world.id,patch:patch}); }
    property var graphics: null
    property var previousTimings: null // prior graphics.get sample (idle detection)
    property var menuHold: null
    // A TAB tap (RFC-0012 markers.reveal) must not flash the Director hold ring: the ring
    // waits this long after the hold started, then fills the rest (local, no wire field).
    property int holdRingDelayMs: Quests.HOLD_RING_DELAY_MS
    // Diagnostics for the nested checks: holds reported, ring fills shown, last fill delay.
    property var holdStats: ({seen: 0, shown: 0, lastDelayMs: -1})
    // Core's monotonic clock (keymap holds, focus phases) = Date.now() + clockOffset;
    // the bridge measures it with session.ping.
    property double clockOffset: 0
    property bool clockKnown: false
    function monotonicNow() { return clockKnown ? Date.now() + clockOffset : null; }
    property double revision: 0
    property string output: ''
    property string screenName: ''
    property string lease: ''
    onLeaseChanged: { if (lease && !available('hud.subscribe')) Qt.callLater(applyCoreStyle); }
    function protocolMinor() { var v=protocol.split('.'); return v[0]==='0' ? Number(v[1]) : 0; }
    // IPC 0.19 adds the core reticle colours (HUD foreground, positive, warning).
    function coreStyle() {
        return PlayerSettings.overlayStyle({mono:Tokens.mono,accent:Tokens.accent,text:Tokens.text,gold:Tokens.gold,
                                            reticle:Tokens.hudForeground,positive:Tokens.hudPositive,warning:Tokens.hudWarning,quest:Tokens.hudQuest}, protocolMinor());
    }
    function applyCoreStyle() { action('overlay.style', {style:coreStyle()}); }
    property Connections coreThemeConnection: Connections {
        target: Tokens
        function onLightChanged() { if (root.lease) root.applyCoreStyle(); }
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
    // Director > Help: core's refusal of the last movement.set ('' = none).
    property string movementRefusal: ''
    property Timer movementRefusalTimer: Timer { interval: 8000; onTriggered: root.movementRefusal = '' }
    function setMovement(modeId) { movementRefusal = ''; action('movement.set', {modeId: modeId}); }
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
    // ---- IPC 0.21 (RFC-0012): markers, quests, focus sessions, guidance ----
    readonly property var markersState: state && state.markers ? state.markers : null
    readonly property var questsState: state && state.quests ? state.quests : null
    readonly property var focusState: state && state.focus ? state.focus : null
    readonly property bool questsSupported: (supportsProtocol(21) || dev) && available('quests.list')
    readonly property bool focusCalm: !!(focusState && focusState.calm)
    property var questList: []
    property var questDetail: null
    property string selectedQuest: ''      // "<source>/<id>"
    property string questFeedback: ''     // last refusal from core, plain words
    property Timer questFeedbackTimer: Timer { interval: 8000; onTriggered: root.questFeedback = '' }
    property var guidance: null            // guidance.get / guidance.set result
    property bool guidanceRequested: false
    property var mapFocus: null
    // Focus session target picker: {kind: 'any' | 'workspace', workspaceId (0 = current)}.
    property var focusTargetChoice: ({kind: 'any', workspaceId: 0})
    readonly property int currentWorkspace: state && state.workspaces && state.workspaces.currentId ? state.workspaces.currentId : 0
    function focusTarget() { return Quests.focusTargetInput(focusTargetChoice, currentWorkspace); }            // {position, label, at}: Quests > Show on map
    property var questPreview: null        // DEV ONLY: quests.list/get and guidance.get answers
    readonly property var guidanceConfig: guidance && guidance.config ? guidance.config : null
    readonly property string questNotifications: guidanceConfig && guidanceConfig['quests.notifications'] ? guidanceConfig['quests.notifications'] : 'all'
    readonly property bool questsVisible: director && tab === tabQuests
    signal focusPulse(string phase)
    signal questsRefreshed()
    signal questActionDone(string method, var params, var result)
    signal questActionFailed(string method, var params, string message)
    function refreshQuests() {
        if (!questsSupported) return;
        action('quests.list', {});
        if (selectedQuest) loadQuest(selectedQuest);
    }
    property Timer questRefresh: Timer { interval: 150; onTriggered: root.refreshQuests() }
    function questRef(key) { var i = key.indexOf('/'); return i > 0 ? {source: key.slice(0, i), id: key.slice(i + 1)} : null; }
    function loadQuest(key) { var ref = questRef(key); if (ref && questsSupported) action('quests.get', {questRef: ref}); }
    function selectQuest(key) {
        if (key === selectedQuest) return;
        selectedQuest = key;
        questDetail = null;
        if (key) loadQuest(key);
    }
    function questAction(method, params) {
        questFeedback = '';
        action(method, params);
    }
    function refreshGuidance() { if (available('guidance.get')) { guidanceRequested = true; action('guidance.get', {}); } }
    property var guidancePending: ({})
    function patchGuidance(patch) { guidancePending = Object.assign({}, guidancePending, patch); guidanceCommit.restart(); }
    property Timer guidanceCommit: Timer { interval: 120; onTriggered: { if (Object.keys(root.guidancePending).length) root.action('guidance.set', {patch: root.guidancePending}); root.guidancePending = ({}); } }
    function showOnMap(resolved) {
        if (!resolved || !resolved.position) return;
        mapFocus = {position: resolved.position, label: resolved.label || '', at: Date.now()};
        tab = tabMap;
    }
    // Toasts (under the HUD tracker) and banners (top centre), RFC-0012 notifications.
    property var toasts: []
    property var banners: []
    property var deferredToasts: []
    property Timer toastClock: Timer { interval: 200; repeat: true; running: root.toasts.length > 0 || root.banners.length > 0; onTriggered: root.advanceToasts() }
    function advanceToasts() {
        var now = Date.now(), t = Quests.advance(toasts, now), b = Quests.advance(banners, now);
        if (t.length !== toasts.length || (t.length && t[0] !== toasts[0])) toasts = t;
        if (b.length !== banners.length || (b.length && b[0] !== banners[0])) banners = b;
    }
    function showToast(toast) {
        var now = Date.now();
        if (Tokens.reducedMotion) toast = Object.assign({}, toast, {instant: true});
        if (toast.kind === 'banner') banners = Quests.enqueue(banners, toast, now);
        else toasts = Quests.enqueue(toasts, toast, now);
    }
    function presentToast(toast) {
        var route = Quests.route(toast, questNotifications, focusCalm);
        if (route === 'show') showToast(toast);
        else if (route === 'defer') deferredToasts = Quests.enqueue(deferredToasts, Object.assign({}, toast), Date.now());
    }
    onFocusCalmChanged: {
        // Calm ends with the work interval: deferred quest toasts show at the break.
        if (!focusCalm && deferredToasts.length) {
            var pending = deferredToasts; deferredToasts = [];
            pending.forEach(t => presentToast(Object.assign({}, t, {count: 1})));
        }
    }
    onQuestsVisibleChanged: { if (questsVisible) refreshQuests(); }
    // ---- IPC 0.22 (RFC-0011 P1): object catalog, user placements, libraries ----
    readonly property var objectsState: state && state.objects ? state.objects : null
    readonly property bool objectsSupported: (supportsProtocol(22) || dev) && available('objects.catalog')
    // Changes need the objects.control grant (requested from 0.22); reads need state.read.
    readonly property bool objectsControl: capabilities.indexOf('objects.control') >= 0 || (dev && previewMethods.indexOf('objects.pocket') >= 0)
    function objectsCan(method) { return objectsControl && available(method); }
    readonly property var editorState: state && state.editor ? state.editor : null
    readonly property string selectedKind: editorState && editorState.selectedKind ? editorState.selectedKind : ''
    readonly property var editorGizmo: editorState && editorState.gizmo ? editorState.gizmo : null
    readonly property var unplacedObjects: Objects.pocketObjects(editorState ? editorState.unplaced : null)
    property var objectCatalog: []
    property int objectCatalogRevision: -1   // revision of the last objects.catalog result
    // objects.catalogRevision when the last catalog was requested: a refresh follows a change of
    // the state value only, whatever revision the result carries.
    property int objectCatalogFor: -1
    property bool objectCatalogLoaded: false
    property var libraries: null             // libraries.list result
    property string selectedObject: ''       // instance id (Director > Objects > Placed)
    property string objectsView: 'catalog'   // Director > Objects view: catalog | shapes | placed | characters | sources
    property var objectFeedback: null        // {level, text, at}: last object result or refusal
    property Timer objectFeedbackTimer: Timer { interval: 8000; onTriggered: root.objectFeedback = null }
    property var objectPreview: null         // DEV ONLY: objects.catalog / libraries.list answers
    readonly property bool objectsVisible: director && tab === tabObjects
    signal objectActionDone(string method, var params, var result)
    signal objectActionFailed(string method, var params, string message)
    function refreshCatalog() {
        if (!objectsSupported) return;
        objectCatalogFor = objectsState ? objectsState.catalogRevision : -1;
        action('objects.catalog', {});
    }
    property Timer catalogRefresh: Timer { interval: 150; onTriggered: root.refreshCatalog() }
    function refreshLibraries() { if (available('libraries.list')) action('libraries.list', {}); }
    function objectAction(method, params) {
        objectFeedback = null;
        action(method, params);
    }
    function pocketObject(ref) { if (ref) objectAction('objects.pocket', {ref: ref}); }
    function installLibrary(archive, sha256) { objectAction('libraries.install', {archive: archive, sha256: sha256}); }
    function removeLibrary(id, version) { objectAction('libraries.remove', {id: id, version: version}); }
    function sayObjects(text, level) {
        objectFeedback = text ? {level: level || 'info', text: text, at: Date.now()} : null;
        if (text) objectFeedbackTimer.restart();
    }
    onObjectsVisibleChanged: {
        if (!objectsVisible) return;
        refreshCatalog();
        // A tool selection (editor.selectedKind object) opens in Placed.
        if (!selectedObject && selectedKind === 'object' && editorState && Objects.selectedInstance(objectsState ? objectsState.instances : [], editorState.selectedId))
            selectedObject = editorState.selectedId;
    }
    function objectResult(method, params, result) {
        if (!method || !result) return;
        if (method === 'objects.catalog') {
            objectCatalog = result.entries; objectCatalogRevision = result.revision; objectCatalogLoaded = true;
            if (placedPending) seedDemoSources();
            return;
        }
        if (method === 'libraries.list') { libraries = result.libraries; return; }
        if (!/^(objects|libraries)\./.test(method)) return;
        if (method === 'objects.pocket') {
            var entry = Objects.entryFor(objectCatalog, params ? params.ref : '');
            showToast(Objects.pocketToast(entry ? entry.name : ''));
        }
        if (method === 'objects.remove' && params && (params.all || params.id === selectedObject)) {
            if (params.all) { var mine = Objects.selectedInstance(objectsState ? objectsState.instances : [], selectedObject); if (mine && mine.source === 'user') selectedObject = ''; }
            else selectedObject = '';
        }
        if (method === 'libraries.install' || method === 'libraries.remove') { catalogRefresh.restart(); refreshLibraries(); }
        sayObjects(Objects.resultText(method, params), 'info');
        objectActionDone(method, params || null, result);
    }
    // ---- Machine data sources (RFC-0013 draft): sources.json and the source helper ----
    // Local to this machine, not core IPC: the bridge (bridge/sources.py) edits sources.json
    // and talks to the helper's control socket. Every request answers one 'sources' message.
    // IPC 0.24 adds state `live` (per bound instance: inputs, values, conditions).
    readonly property var liveState: state && state.live ? state.live : null
    property var sourcesStatus: null        // last status answer {ok, helper, status?, error?}
    property int sourcesSeq: 0
    property int sourcesStatusSeq: 0        // status request in flight (0: none)
    property real sourcesStatusAt: 0
    property bool sourcesWanted: false      // a Data source section is showing (polls ~1 s)
    signal sourcesReply(var reply)
    function sourcesRequest(type, payload) {
        if (!socket.connected) return 0;
        sourcesSeq += 1;
        send(Object.assign({}, payload || {}, {type: type, seq: sourcesSeq}));
        return sourcesSeq;
    }
    function pollSources() {
        // One status request at a time (a hung helper times out in the bridge after 2 s).
        if (sourcesStatusSeq && Date.now() - sourcesStatusAt < 4000) return;
        sourcesStatusAt = Date.now();
        sourcesStatusSeq = sourcesRequest('sources.status', {});
    }
    property Timer sourcesPoll: Timer {
        interval: 1000; repeat: true; triggeredOnStart: true
        running: root.sourcesWanted && root.objectsVisible && root.socket.connected
        onTriggered: root.pollSources()
    }
    onSourcesWantedChanged: { if (!sourcesWanted) { sourcesStatusSeq = 0; } }
    // A newly placed machine starts with a demo source (Sources.demoSeeds): the user placements
    // that appear after a world's first state, when the catalog declares machine inputs (IPC
    // 0.24). The bridge adds the entry only when sources.json has none for that id.
    property var placedKnown: null           // instance id -> true; null until this world's first state
    property string placedWorld: ''
    property bool placedPending: false       // new user placements the catalog didn't list yet
    function seedDemoSources() {
        var instances = objectsState ? objectsState.instances || [] : [];
        var wid = state && state.world ? state.world.id : '';
        if (!placedKnown || wid !== placedWorld) {
            var known = {};
            instances.forEach(function (i) { known[i.id] = true; });
            placedKnown = known, placedWorld = wid, placedPending = false;
            return;
        }
        var fresh = instances.filter(function (i) { return i.source === 'user' && !i.character && !placedKnown[i.id]; });
        if (!fresh.length) return;
        Sources.demoSeeds(fresh, objectCatalog, placedKnown).forEach(function (seed) {
            sourcesRequest('sources.seed', {id: seed.id, argv: seed.argv, intervalS: Sources.DEMO_INTERVAL});
        });
        // Not in the catalog yet (a library just installed, or never fetched): fetch it once.
        placedPending = fresh.some(function (i) { return !placedKnown[i.id]; });
        if (placedPending && objectsSupported && !catalogRefresh.running) catalogRefresh.restart();
    }

    // ---- IPC 0.25 (RFC-0010 companions amendment, draft): the companion ----
    readonly property var companionState: state && state.companion ? state.companion : null
    readonly property bool companionSupported: (supportsProtocol(25) || dev) && available('companion.set')
    readonly property var companionChoices: Companion.choices(objectCatalog)
    readonly property string companionStatus: Companion.status(companionState, pathList)
    // None clears; a ref sets (the catalog says which characters are capable).
    function chooseCompanion(ref) { var r = Companion.choose(ref); if (objectsCan(r.method)) objectAction(r.method, r.params); }
    function companionMode(mode) { if (objectsCan('companion.mode')) objectAction('companion.mode', {mode: mode}); }
    // IPC 0.26: Walk / Run (companion.mode with pace; the mode is kept).
    readonly property bool companionPaceSupported: supportsProtocol(26) && available('companion.mode')
    function companionPace(pace) {
        var params = Companion.paceParams(companionState, pace);
        if (params && companionPaceSupported && objectsCan('companion.mode')) objectAction('companion.mode', params);
    }
    // IPC 0.28 (shared clip library): walk, run and idle styles, from the catalog's motion.
    readonly property bool styleSupported: supportsProtocol(28)
    function catalogMotion(ref) { var entry = Objects.entryFor(objectCatalog, ref || ''); return entry && entry.motion ? entry.motion : null; }
    function companionStyle(role, style) {
        var params = Companion.styleParams(companionState, role, style);
        if (params && styleSupported && objectsCan('companion.mode')) objectAction('companion.mode', params);
    }

    // ---- RFC-0015 phase 1: Director > Library over the hyprune CLI (no core IPC) ----
    // The command is $HYPRUNE_CLI (a command line split on spaces), else hyprune on PATH.
    // Listings print one JSON document; jobs print JSON lines (stage, plan, progress, done,
    // error). Install and update run with --plan first; --yes (and --accept-source-change after
    // the page's second confirmation) only once the user confirms the plan.
    property var libraryCli: Library.cliCommand(Quickshell.env('HYPRUNE_CLI'))   // dev hook libraryCommand may replace it
    property string libraryView: 'browse'     // Director > Library view: browse | installed | sources
    property var librarySources: []
    property var libraryEntries: []
    property var libraryInstalls: []
    property bool libraryLoaded: false
    property string libraryReadError: ''
    property var libraryJob: null             // Library.newJob(): the running or last panel job
    property var libraryFeedback: null        // {level, text}: the last finished job
    property Timer libraryFeedbackTimer: Timer { interval: 8000; onTriggered: root.libraryFeedback = null }
    readonly property bool libraryBusy: Library.running(libraryJob)
    readonly property bool libraryVisible: director && tab === tabLibrary
    onLibraryVisibleChanged: { if (libraryVisible) refreshLibrary(); }
    function refreshLibrary() {
        libraryReadError = '';
        [libraryReadSources, libraryReadBrowse, libraryReadInstalls].forEach(p => { if (!p.running) { p.started = false; p.running = true; } });
    }
    function libraryDocument(key, text, code, errors) {
        var doc = null;
        try { doc = code === 0 ? JSON.parse(text) : null; } catch (e) { doc = null; }
        if (!doc) {
            var tail = Library.stderrLine(errors);
            libraryReadError = code < 0 ? 'The hyprune command didn\'t run: set HYPRUNE_CLI or put hyprune on PATH.'
                                        : 'hyprune ' + key + ': ' + (tail || (code === 0 ? 'not a JSON document' : 'exit code ' + code));
            return;
        }
        if (key === 'sources') librarySources = doc.sources || [];
        else if (key === 'browse') libraryEntries = doc.entries || [];
        else if (key === 'installed') libraryInstalls = doc.installs || [];
        libraryLoaded = true;
    }
    component LibraryRead: Process {
        id: reader
        property string key: ''
        property var args: []
        property bool started: false
        command: root.libraryCli.concat(args)
        stdout: StdioCollector { id: readOut }
        stderr: StdioCollector { id: readErr }
        onStarted: started = true
        onExited: (code) => Qt.callLater(() => root.libraryDocument(reader.key, readOut.text, code, readErr.text))
        onRunningChanged: { if (!running && !started) root.libraryDocument(key, '', -1, ''); }
    }
    property LibraryRead libraryReadSources: LibraryRead { key: 'sources'; args: ['source', 'list', '--json'] }
    property LibraryRead libraryReadBrowse: LibraryRead { key: 'browse'; args: ['browse', '--json'] }
    property LibraryRead libraryReadInstalls: LibraryRead { key: 'installed'; args: ['content', 'list', '--json'] }
    property Process libraryRun: Process {
        property bool started: false
        stdout: SplitParser { onRead: (line) => root.libraryJob = Library.jobEvent(root.libraryJob, line) }
        stderr: StdioCollector { id: libraryRunErr }
        onStarted: started = true
        onExited: (code) => Qt.callLater(() => root.libraryEnded(code, libraryRunErr.text))
        onRunningChanged: { if (!running && !started) root.libraryEnded(-1, ''); }
    }
    function libraryStart(job) {
        if (libraryBusy) return false;
        libraryFeedback = null;
        libraryJob = job;
        libraryRun.command = libraryCli.concat(job.args);
        // A command that can't start drops running without started (and never exits).
        libraryRun.started = false;
        libraryRun.running = true;
        return true;
    }
    function libraryTarget(item) {
        var e = Library.entryFor(libraryEntries, item.id, item.sourceId) || Library.entryFor(libraryEntries, item.id);
        return {id: item.id, sourceId: item.sourceId || '', type: item.type || '', name: e ? e.name : item.id};
    }
    // Install or update: the plan first (--plan), shown for confirmation.
    function libraryPlan(kind, item) {
        if (!item || (kind !== 'install' && kind !== 'update')) return false;
        var target = libraryTarget(item);
        return libraryStart(Library.newJob(kind, target, Library.jobArgs(kind, target.id, kind === 'install' ? target.sourceId : '', 'plan')));
    }
    // The confirmed plan runs with --yes; a source change only with acceptChange (the second dialog).
    function libraryConfirm(acceptChange) {
        var job = libraryJob;
        if (!job || job.phase !== 'confirm') return false;
        var change = !!Library.sourceChange(job.plan);
        if (change && !acceptChange) return false;
        var next = Library.newJob(job.kind, job.target, Library.jobArgs(job.kind, job.target.id, job.kind === 'install' ? job.target.sourceId : '', 'yes', change));
        return libraryStart(Object.assign(next, {phase: 'running', plan: job.plan}));
    }
    // rollback | pin | unpin | remove of an install (the page asks before removing).
    function libraryInstallAction(kind, install) {
        if (!install || ['rollback', 'pin', 'unpin', 'remove'].indexOf(kind) < 0) return false;
        var target = libraryTarget(install);
        return libraryStart(Library.newJob(kind, target, Library.jobArgs(kind, target.id, '', 'yes')));
    }
    // Sources: refresh [id] | enable id | disable id | remove id | add (Library.sourceForm args).
    function librarySource(verb, id, args) {
        var source = librarySources.find(s => s.id === id) || null;
        var target = {id: id || '', sourceId: id || '', type: '', name: source ? Library.tierLabel(source) : id || ''};
        var argv = verb === 'add' ? args : ['source', verb].concat(id ? [id] : []).concat(['--json']);
        return libraryStart(Library.newJob('source.' + verb, target, argv));
    }
    function libraryCancel() { if (libraryBusy && libraryRun.running) { libraryJob = Object.assign({}, libraryJob, {cancelled: true}); libraryRun.signal(15); } }
    function libraryClose() { if (!libraryBusy) libraryJob = null; }
    function libraryEnded(code, errors) {
        if (!libraryJob) return;
        var job = Library.jobFinished(libraryJob, code, errors);
        if (job.cancelled && job.phase === 'failed') job.error = {rule: '', message: 'Cancelled.'};
        libraryJob = job.panel || job.phase === 'confirm' ? job : null;
        if (job.phase === 'confirm') return;
        var e = Library.errorText(job.error);
        libraryFeedback = job.phase === 'done' ? {level: 'info', text: Library.resultText(job, job.target.name)} : {level: 'warning', text: e.line + (e.detail ? '  (' + e.detail + ')' : '')};
        libraryFeedbackTimer.restart();
        if (!libraryVisible) showToast(Library.toast(job, job.target.name));
        // A library change shows in Objects: refresh core's catalog and library list.
        var type = job.result && job.result.type ? job.result.type : job.target.type;
        if (job.phase === 'done' && type === 'library') { catalogRefresh.restart(); refreshLibraries(); }
        refreshLibrary();
    }
    // ---- Imports (RFC-0014 as amended): Director > Objects > Import… over the hyprune CLI ----
    // `object import FILE --inspect --json` measures the file; the review form follows; the
    // import itself prints JSON lines (stage, done, error). It writes the user object folder,
    // which core watches: the object joins the catalog without a reload. No core IPC.
    property var importJob: null              // Import.newJob(): browse, inspecting, review, running, done, failed
    readonly property bool importing: importJob !== null
    readonly property bool importBusy: !!importJob && (importJob.phase === 'inspecting' || importJob.phase === 'running')
    function importOpen() { if (!importBusy) importJob = Import.newJob('browse', ''); }
    function importPick(path) {
        if (importBusy || !Import.importable(path)) return false;
        importStart(Import.newJob('inspecting', path), Import.inspectArgs(path));
        return true;
    }
    function importForm(patch) { if (importJob && importJob.phase === 'review') importJob = Object.assign({}, importJob, {form: Object.assign({}, importJob.form, patch)}); }
    function importRun() {
        var job = importJob;
        if (!job || job.phase !== 'review' || Import.formErrors(job.form).length) return false;
        importStart(Object.assign({}, job, {phase: 'running', stage: '', stages: [], error: null}), Import.jobArgs(job.path, job.form));
        return true;
    }
    function importStart(job, args) {
        importJob = job;
        importProcess.command = libraryCli.concat(args);
        importProcess.started = false;
        importProcess.running = true;
    }
    function importBack() { if (importJob && !importBusy) importJob = importJob.inspection ? Object.assign({}, importJob, {phase: 'review', error: null}) : Import.newJob('browse', ''); }
    function importClose() {
        if (importBusy) { importJob = Object.assign({}, importJob, {cancelled: true}); importProcess.signal(15); return; }
        importJob = null;
    }
    function importEnded(code, errors) {
        var job = Import.jobFinished(importJob, code, errors);
        importJob = job;
        if (!job) return;
        if (job.phase === 'done') {
            sayObjects(Import.resultText(job.result), 'info');
            importCatalogPoll.tries = 0;
            importCatalogPoll.restart();
        }
    }
    // The new object is listed once core's folder watch has scanned it (a second or two).
    readonly property bool importListed: !!importJob && importJob.phase === 'done' && !!Objects.entryFor(objectCatalog, importJob.result ? importJob.result.ref : '')
    property Timer importCatalogPoll: Timer {
        property int tries: 0
        interval: 700; repeat: true
        onTriggered: { if (root.importListed || ++tries > 30) stop(); else root.refreshCatalog(); }
    }
    function importPocket() { if (importListed && objectsCan('objects.pocket')) { objectAction('objects.pocket', {ref: importJob.result.ref}); importJob = null; } }
    property Process importProcess: Process {
        property bool started: false
        stdout: SplitParser { onRead: (line) => root.importJob = Import.jobEvent(root.importJob, line) }
        stderr: StdioCollector { id: importErr }
        onStarted: started = true
        onExited: (code) => Qt.callLater(() => root.importEnded(code, importErr.text))
        onRunningChanged: { if (!running && !started) root.importEnded(-1, ''); }
    }
    // ---- World folders (RFC-0014 as amended): Director > Builder over the hyprune CLI ----
    // `builder create|save|release|sky|remote --json` run one at a time (JSON lines); list and
    // status refresh on their own process. A folder opens with world.load local.<slug>: core
    // loads it in editor mode (state.builder) and writes the placements; git is the CLI's.
    readonly property var builderState: state && state.builder ? state.builder : null
    readonly property bool builderEditing: builderState !== null
    readonly property bool builderVisible: director && tab === tabBuilder
    property var builderJob: null           // Builder.newJob(): running, done, failed
    property var builderProjects: []        // `builder list`
    property var builderStatus: null        // `builder status` of the loaded folder
    property var builderSky: null           // the sky form while choosing an image: {path, license, author, source}
    property var builderIdentity: null      // {name, email} when git has none (asked on create)
    property var builderWizard: null        // Builder.newWizard() while New world is open
    property var builderFloor: null         // the floor form in a folder: {preset, tile} or {path, license, author, source, tile}
    property var builderSkies: []           // `builder skies`: built-in skies with thumbnails
    property var builderFloors: []          // `builder floors`: built-in floors with thumbnails
    readonly property bool builderBusy: !!builderJob && builderJob.phase === 'running'
    function builderRun(job, args) {
        if (builderBusy) return false;
        builderJob = job;
        builderProcess.command = libraryCli.concat(args);
        builderProcess.started = false;
        builderProcess.running = true;
        return true;
    }
    function builderCreate(name) {
        if (Builder.nameError(name) || Builder.identityErrors(builderIdentity).length) return false;
        return builderRun(Builder.newJob('create', '', {name: String(name).trim()}), Builder.createArgs(name, builderIdentity));
    }
    function builderOpen(slug) { if (slug) action('world.load', {worldId: Builder.worldId(slug)}); }
    // ---- New world: name (and starter), sky, floor, where you start; then create and open ----
    function builderWizardStart() { if (builderBusy) return; builderWizard = Builder.newWizard(); builderJob = null; builderLoadPresets(); }
    function builderWizardSet(patch) { if (builderWizard) builderWizard = Object.assign({}, builderWizard, patch); }
    function builderWizardMove(delta) {
        if (!builderWizard || (delta > 0 && Builder.wizardErrors(builderWizard, builderIdentity).length)) return false;
        builderWizard = Builder.wizardMove(builderWizard, delta);
        return true;
    }
    function builderWizardCreate() {
        var w = builderWizard;
        if (!w || builderBusy) return false;
        for (var i = 0; i < Builder.WIZARD_STEPS.length; i++)
            if (Builder.wizardErrors(Object.assign({}, w, {step: i}), builderIdentity).length) { builderWizard = Object.assign({}, w, {step: i}); return false; }
        return builderRun(Builder.newJob('create', '', {name: String(w.name).trim()}), Builder.createArgs(w.name, builderIdentity, w));
    }
    function builderLoadPresets() {
        if (builderSkies.length && builderFloors.length) return;
        builderPresetsProc.command = libraryCli.concat(builderSkies.length ? Builder.floorsArgs() : Builder.skiesArgs());
        builderPresetsProc.running = true;
    }
    property Process builderPresetsProc: Process {
        stdout: SplitParser {
            onRead: (line) => {
                var e = null;
                try { e = JSON.parse(line); } catch (x) { return; }
                if (!e || e.event !== 'done' || !e.result) return;
                if (e.result.skies) root.builderSkies = e.result.skies;
                if (e.result.floors) root.builderFloors = e.result.floors;
            }
        }
        onRunningChanged: { if (!running && root.builderSkies.length && !root.builderFloors.length) Qt.callLater(root.builderLoadPresets); }
    }
    // ---- sky and floor of the open folder (the same choices as the wizard) ----
    function builderSkyPreset(id) {
        if (!builderEditing || !id) return false;
        return builderRun(Builder.newJob('sky', builderState.projectId), Builder.skyArgs(builderState.projectId, {preset: id}));
    }
    function builderFloorPick(path) { if (Builder.floorImage(path)) builderFloor = {path: path, license: '', author: '', source: '', tile: 2}; }
    function builderFloorForm(patch) { if (builderFloor) builderFloor = Object.assign({}, builderFloor, patch); }
    function builderFloorApply(form) {
        var f = form || builderFloor;
        if (!builderEditing || !f || Builder.floorErrors(f).length) return false;
        return builderRun(Builder.newJob('floor', builderState.projectId), Builder.floorArgs(builderState.projectId, f));
    }
    function builderSave(message) { return builderEditing && builderRun(Builder.newJob('save', builderState.projectId), Builder.saveArgs(builderState.projectId, message)); }
    function builderRelease(version, notes) {
        if (!builderEditing || Builder.versionError(version)) return false;
        return builderRun(Builder.newJob('release', builderState.projectId), Builder.releaseArgs(builderState.projectId, version, notes));
    }
    function builderSkyPick(path) { if (Builder.skyImage(path)) builderSky = {path: path, license: '', author: '', source: ''}; }
    function builderSkyForm(patch) { if (builderSky) builderSky = Object.assign({}, builderSky, patch); }
    function builderSkyApply() {
        if (!builderEditing || Builder.skyErrors(builderSky).length) return false;
        return builderRun(Builder.newJob('sky', builderState.projectId), Builder.skyArgs(builderState.projectId, builderSky));
    }
    function builderRemote(url) {
        if (!builderEditing || Builder.remoteError(url)) return false;
        return builderRun(Builder.newJob('remote', builderState.projectId), Builder.remoteArgs(builderState.projectId, url));
    }
    function builderClose() { if (!builderBusy) builderJob = null; }
    function builderEnded(code, errors) {
        var job = Builder.jobFinished(builderJob, code, errors);
        builderJob = job;
        if (!job) return;
        if (job.phase === 'failed' && job.error && job.error.code === 'git.identity') builderIdentity = builderIdentity || {name: '', email: ''};
        if (job.phase !== 'done') return;
        var r = job.result || {};
        if (r.status && builderEditing && r.status.projectId === builderState.projectId) builderStatus = r.status;
        if (job.kind === 'create') { builderIdentity = null; builderWizard = null; builderOpen(r.projectId); }
        if (job.kind === 'sky') { builderSky = null; builderOpen(job.slug); } // the panorama loads with the world
        if (job.kind === 'floor') { builderFloor = null; builderOpen(job.slug); }
        builderRefresh();
    }
    function builderRefresh() {
        if (builderPoll.running) { builderPollAgain = true; return; }
        builderPoll.command = libraryCli.concat(builderEditing ? Builder.statusArgs(builderState.projectId) : Builder.listArgs());
        builderPoll.running = true;
    }
    property bool builderPollAgain: false
    property Process builderProcess: Process {
        property bool started: false
        stdout: SplitParser { onRead: (line) => root.builderJob = Builder.jobEvent(root.builderJob, line) }
        stderr: StdioCollector { id: builderErr }
        onStarted: started = true
        onExited: (code) => Qt.callLater(() => root.builderEnded(code, builderErr.text))
        onRunningChanged: { if (!running && !started) root.builderEnded(-1, ''); }
    }
    property Process builderPoll: Process {
        stdout: SplitParser {
            onRead: (line) => {
                var e = null;
                try { e = JSON.parse(line); } catch (x) { return; }
                if (!e || e.event !== 'done' || !e.result) return;
                if (e.result.projects) root.builderProjects = e.result.projects;
                else if (root.builderEditing && e.result.projectId === root.builderState.projectId) root.builderStatus = e.result;
            }
        }
        onRunningChanged: { if (!running && root.builderPollAgain) { root.builderPollAgain = false; Qt.callLater(root.builderRefresh); } }
    }
    // Core counts its project writes: each is a pending change to show.
    property Timer builderStatusTimer: Timer { interval: 500; onTriggered: root.builderRefresh() }
    readonly property string builderKey: builderState ? builderState.projectId + ':' + builderState.revision : ''
    onBuilderKeyChanged: { if (!builderState) builderStatus = null; if (builderVisible || builderEditing) builderStatusTimer.restart(); }
    onBuilderVisibleChanged: { if (builderVisible) { builderRefresh(); if (builderEditing) builderLoadPresets(); } }
    // ---- Shapes (RFC-0014 amendment: primitives and materials, IPC 0.31) ----
    // `builder primitive|material|materials|rebuild <slug>` in a world folder, `object …` elsewhere;
    // one at a time (JSON lines). A made shape is pocketed for tool 5; a changed size or material
    // swaps the placement to the new folder (objects.configure {ref}); a saved material rebuilds
    // the shapes made with it and swaps their placements.
    readonly property bool shapesSupported: supportsProtocol(31) || dev
    readonly property string shapesSlug: builderEditing ? builderState.projectId : ''
    property var shapesJob: null            // {kind: make | apply | material | rebuild, phase, result, error, id?, key?}
    property var shapesMaterials: []        // `materials`: the library of the folder (or the user's)
    property var shapesPocket: null         // {ref, tries}: a made shape waiting for the catalog to list it
    property var shapesSwaps: []            // [{id, ref, tries}]: swaps waiting for their new asset to load
    readonly property bool shapesBusy: !!shapesJob && shapesJob.phase === 'running'
    function shapesRun(job, args) {
        if (shapesBusy) return false;
        shapesJob = Object.assign({phase: 'running', result: null, error: null}, job);
        shapesProcess.command = libraryCli.concat(args);
        shapesProcess.started = false;
        shapesProcess.running = true;
        return true;
    }
    function shapesMake(form) {
        if (Shapes.sizeErrors(form).length) return false;
        return shapesRun({kind: 'make'}, Shapes.primitiveArgs(shapesSlug, form));
    }
    function shapesApply(id, form) {
        if (!id || Shapes.sizeErrors(form).length) return false;
        return shapesRun({kind: 'apply', id: id}, Shapes.primitiveArgs(shapesSlug, form));
    }
    function shapesSaveMaterial(m) {
        if (Shapes.materialErrors(m).length) return false;
        return shapesRun({kind: 'material', key: m.key}, Shapes.materialArgs(shapesSlug, m));
    }
    function shapesRename(id, key) {
        if (!id || Shapes.keyError(key)) return false;
        objectAction('objects.configure', {id: id, patch: {key: String(key || '').trim() || null}});
        return true;
    }
    // A swap to a just-made shape: its asset may still be decoding (a retryable refusal), so it is
    // tried again for a few seconds.
    function shapesSwap(id, ref) {
        shapesSwaps = shapesSwaps.filter(function (s) { return s.id !== id; }).concat([{id: id, ref: ref, tries: 0}]);
        objectAction('objects.configure', {id: id, patch: {ref: ref}});
    }
    function shapesLoadMaterials() {
        if (shapesMaterialsProc.running) return;
        shapesMaterialsProc.command = libraryCli.concat(Shapes.materialsArgs(shapesSlug));
        shapesMaterialsProc.running = true;
    }
    function shapesEnded(code, errors) {
        var job = Builder.jobFinished(shapesJob, code, errors);
        shapesJob = job;
        if (!job || job.phase !== 'done') { if (job && job.phase === 'failed') sayObjects(Shapes.errorText(job.error), 'warning'); return; }
        var r = job.result || {};
        if (job.kind === 'make') {
            shapesPocket = {ref: r.ref, tries: 0};
            pocketObject(r.ref);
            sayObjects((r.created ? 'Made ' : 'Reused ') + r.name + ': place it with tool 5', 'info');
        } else if (job.kind === 'apply') {
            var inst = Objects.selectedInstance(objectsState ? objectsState.instances : [], job.id);
            if (inst && inst.ref !== r.ref) shapesSwap(job.id, r.ref);
        } else if (job.kind === 'material') {
            shapesLoadMaterials();
            if (r.stale && r.stale.length) Qt.callLater(function () { root.shapesRun({kind: 'rebuild', key: job.key}, Shapes.rebuildArgs(root.shapesSlug, job.key)); });
            else sayObjects('Saved the material ' + job.key, 'info');
        } else if (job.kind === 'rebuild') {
            var moves = Shapes.swapsFor(objectsState ? objectsState.instances : [], r.swaps);
            moves.forEach(function (m) { root.shapesSwap(m.id, m.ref); });
            sayObjects('Saved the material ' + job.key + (moves.length ? '; ' + moves.length + ' placed shape' + (moves.length === 1 ? '' : 's') + ' updated' : ''), 'info');
        }
        if (job.kind === 'make' || job.kind === 'apply') shapesLoadMaterials(); // a built-in texture may have joined the library
        catalogRefresh.restart();
    }
    property Process shapesProcess: Process {
        property bool started: false
        stdout: SplitParser { onRead: (line) => root.shapesJob = Builder.jobEvent(root.shapesJob, line) }
        stderr: StdioCollector { id: shapesErr }
        onStarted: started = true
        onExited: (code) => Qt.callLater(() => root.shapesEnded(code, shapesErr.text))
        onRunningChanged: { if (!running && !started) root.shapesEnded(-1, ''); }
    }
    property Process shapesMaterialsProc: Process {
        stdout: SplitParser {
            onRead: (line) => {
                var e = null;
                try { e = JSON.parse(line); } catch (x) { return; }
                if (e && e.event === 'done' && e.result && e.result.materials) root.shapesMaterials = e.result.materials;
            }
        }
    }
    // Outside a world folder the user folder is rescanned on its own clock: try the pocket again.
    property Timer shapesPocketRetry: Timer { interval: 700; onTriggered: { if (root.shapesPocket) root.pocketObject(root.shapesPocket.ref); } }
    property Timer shapesSwapRetry: Timer {
        interval: 500
        onTriggered: {
            var due = root.shapesSwaps.filter(function (s) { return s.waiting; });
            root.shapesSwaps = root.shapesSwaps.map(function (s) { return Object.assign({}, s, {waiting: false}); });
            due.forEach(function (s) { root.objectAction('objects.configure', {id: s.id, patch: {ref: s.ref}}); });
        }
    }
    onObjectActionFailed: (method, params, message) => {
        if (method === 'objects.configure' && params && params.patch && params.patch.ref) {
            var swap = shapesSwaps.filter(function (s) { return s.id === params.id && s.ref === params.patch.ref; })[0];
            if (!swap) return;
            if (swap.tries >= 16) { shapesSwaps = shapesSwaps.filter(function (s) { return s !== swap; }); return; }
            shapesSwaps = shapesSwaps.map(function (s) { return s === swap ? Object.assign({}, s, {tries: s.tries + 1, waiting: true}) : s; });
            shapesSwapRetry.restart();
            return;
        }
        if (method !== 'objects.pocket' || !shapesPocket || !params || params.ref !== shapesPocket.ref) return;
        if (shapesPocket.tries >= 12) { shapesPocket = null; return; }
        shapesPocket = {ref: shapesPocket.ref, tries: shapesPocket.tries + 1};
        shapesPocketRetry.restart();
    }
    onObjectActionDone: (method, params, result) => {
        if (method === 'objects.pocket' && shapesPocket && params && params.ref === shapesPocket.ref) shapesPocket = null;
        if (method === 'objects.configure' && params && params.patch && params.patch.ref)
            shapesSwaps = shapesSwaps.filter(function (s) { return !(s.id === params.id && s.ref === params.patch.ref); });
    }
    // ---- IPC 0.23 (RFC-0011 P2): characters, routes and character interactions ----
    readonly property var npcsState: state && state.npcs ? state.npcs : null
    readonly property bool npcsSupported: (supportsProtocol(23) || dev) && available('paths.list')
    // Character and path changes need objects.control; paths.list state.read; choosing world.control.
    function npcsCan(method) { return method === 'paths.list' || method === 'interaction.choose' || method === 'graphics.set' ? available(method) : objectsCan(method); }
    readonly property var characterInstances: Npcs.characters(objectsState ? objectsState.instances : [])
    property var pathList: []                // paths.list result: package and user paths of this world
    property bool pathsLoaded: false
    property string selectedCharacter: ''    // Director > Objects > Characters
    // The spawn panel: a catalog character ref (spawn) or a user character id (rebind); '' = closed.
    property string spawnRef: ''
    property string rebindId: ''
    property var npcChoice: null             // the choice list on screen (bridge interaction.prompt)
    property string npcInteractionKey: ''    // the last npcs.interaction acted on (panel, waypoint, guide)
    property string pathsSignature: ''
    property var pathPreview: null           // DEV ONLY: paths.list answer
    readonly property var npcDrawing: npcsState ? npcsState.drawing : null
    readonly property var drawingHint: Npcs.drawingHint(npcDrawing, drawingName())
    function drawingName() {
        if (!npcDrawing) return '';
        if (npcDrawing.spawn) { var e = Objects.entryFor(objectCatalog, npcDrawing.spawn.ref); return e ? e.name : ''; }
        var i = npcDrawing.bind ? Objects.selectedInstance(objectsState ? objectsState.instances : [], npcDrawing.bind) : null;
        return i ? i.name : '';
    }
    function characterName(objectId) {
        var i = Objects.selectedInstance(objectsState ? objectsState.instances : [], objectId);
        if (i) return i.name;
        return npcsState && npcsState.aimed && npcsState.aimed.objectId === objectId ? npcsState.aimed.name : '';
    }
    function refreshPaths() { if (npcsSupported) action('paths.list', {}); }
    property Timer pathsRefresh: Timer { interval: 150; onTriggered: root.refreshPaths() }
    function npcAction(method, params) {
        if (!npcsCan(method)) return;
        objectFeedback = null;
        action(method, params);
    }
    function startSpawn(ref) { rebindId = ''; spawnRef = ref || ''; if (spawnRef) refreshPaths(); }
    function startRebind(id) { spawnRef = ''; rebindId = id || ''; if (rebindId) refreshPaths(); }
    function closeSpawn() { spawnRef = ''; rebindId = ''; }
    function finishDrawing() { npcAction('paths.finish', {}); }
    // There is no paths.cancel: Cancel removes the path being drawn.
    function cancelDrawing() { if (npcDrawing) npcAction('paths.remove', {id: npcDrawing.pathId}); }
    function setNpcMotion(motion) { var r = Npcs.motionRequest(motion); if (r && available(r.method)) action(r.method, r.params); }
    function chooseInteraction(choiceId, option) {
        var params = Npcs.chooseParams(npcChoice || (npcsState ? npcsState.interaction : null), choiceId, styleSupported ? option : '');
        if (params) action('interaction.choose', params);
    }
    // IPC 0.28: a dance interaction's dances for the choice list, from the character last aimed at
    // (the list is open while the player faces it); null without (Dance then picks any).
    property var lastAimed: null
    onNpcsStateChanged: { if (npcsState && npcsState.aimed) lastAimed = npcsState.aimed; }
    function danceOptions(objectId, interactionId) {
        if (!styleSupported || !lastAimed || lastAimed.objectId !== objectId) return null;
        return Npcs.danceOptions(lastAimed.interactions, interactionId);
    }
    // A new npcs.interaction: panel opens the Director there (unknown ids just end it),
    // waypoint and guide show a toast. Choice lists come from the bridge (exclusive input);
    // the say caption is drawn from state by the HUD.
    function handleInteraction(interaction) {
        var effect = Npcs.interactionEffect(interaction, characterName(interaction.objectId), tabKeys);
        if (effect.kind === 'toast') showToast(effect.toast);
        else if (effect.kind === 'end') action('interaction.choose', {objectId: effect.objectId, interactionId: null});
        else if (effect.kind === 'panel') {
            tab = effect.tab;
            if (effect.view) objectsView = effect.view;
            if (dev && previewMethods.indexOf('interaction.choose') >= 0 && methods.indexOf('interaction.choose') < 0) {
                send({type: 'dev.open'}); // DEV ONLY: the mock has no 0.23 bridge command
                action('interaction.choose', {objectId: effect.objectId, interactionId: null});
            } else send({type: 'interaction.panel', objectId: effect.objectId});
        }
    }
    function npcResult(method, params, result) {
        if (!method || !result) return;
        if (method === 'paths.list') { pathList = result.paths; pathsLoaded = true; return; }
        if (!/^(npcs|paths)\./.test(method)) return;
        if (method === 'npcs.spawn') { closeSpawn(); objectsView = 'characters'; selectedCharacter = result.id; }
        if (method === 'npcs.bind') closeSpawn();
        if (method === 'npcs.remove' && params && (params.all || params.id === selectedCharacter)) selectedCharacter = '';
        if (method === 'paths.draw') { closeSpawn(); if (director) close(); } // tool 3 draws in the world
        sayObjects(Npcs.resultText(method, params, result), 'info');
        pathsRefresh.restart();
        objectActionDone(method, params || null, result);
    }
    readonly property bool charactersVisible: objectsVisible && (objectsView === 'characters' || spawnRef !== '' || rebindId !== '')
    onCharactersVisibleChanged: { if (charactersVisible) refreshPaths(); }
    // DEV ONLY (preview IPC): state fields and methods shown without a newer core. The
    // patch is merged into every snapshot; preview-only methods are recorded, never sent.
    property var statePreview: null
    property var previewMethods: []
    property var previewActions: []
    property var lastStateMessage: null
    function mergePreview(base, patch) {
        if (patch === null || typeof patch !== 'object' || Array.isArray(patch) || base === null || typeof base !== 'object' || Array.isArray(base)) return patch;
        var out = Object.assign({}, base);
        Object.keys(patch).forEach(k => { out[k] = mergePreview(base[k], patch[k]); });
        return out;
    }
    function setStatePreview(patch, extraMethods) {
        if (!dev) return;
        statePreview = patch; previewMethods = extraMethods || [];
        if (lastStateMessage) receive(lastStateMessage);
    }
    property bool director: false
    // IPC 0.17 debug capture note: the capture awaiting a note ('' = no prompt).
    property string notePrompt: ''
    property string noteText: ''
    // IPC 0.29: the prompt labels a debug recording just stopped (id recording:<path>).
    readonly property bool noteRecording: notePrompt.indexOf('recording:') === 0
    function cleanNote(text) { return String(text).replace(/[\u0000-\u001f\u007f-\u009f]/g, ' ').slice(0, 1000); }
    function submitNote() { if (notePrompt) send({type: 'capture.note', captureId: notePrompt, note: cleanNote(noteText), release: true}); }
    function dismissNote() { if (notePrompt) send({type: 'capture.dismiss', captureId: notePrompt}); }
    property int tab: 0
    // Director tab indices (Quests sits directly after Map, RFC-0012).
    // Objects follows Quests (RFC-0011).
    readonly property int tabMap: 0
    readonly property int tabQuests: 1
    readonly property int tabObjects: 2
    // Library follows Objects (RFC-0015).
    readonly property int tabLibrary: 3
    readonly property int tabBuilder: 4
    readonly property int tabSettings: 10
    readonly property int tabCount: 11
    // Stable names for the Director tabs (dev hooks and checks address tabs by name, not position).
    readonly property var tabKeys: ['map', 'quests', 'objects', 'library', 'builder', 'places', 'surfaces', 'workspaces', 'help', 'whatsnew', 'settings']
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
    // Dev automation: hide the world HUD (tool deck, hints, toasts, notices) for clean demo
    // recordings; the Director still opens. Set only through the preview IPC (dev builds).
    property bool hudHidden: false
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
        return live && (methods.indexOf(method) >= 0 || (dev && previewMethods.indexOf(method) >= 0));
    }

    function send(value) {
        if (socket.connected)
            socket.write(JSON.stringify(value) + '\n');

    }

    function action(method, params) {
        if (dev && previewMethods.indexOf(method) >= 0 && methods.indexOf(method) < 0) {
            previewActions = previewActions.concat([{method: method, params: params}]).slice(-16);
            var answer = previewAnswer(method, params);
            if (answer) Qt.callLater(() => receive({type: 'action', method: method, params: params, result: answer}));
            return;
        }
        if (available(method))
            send({
            "type": 'action',
            "method": method,
            "params": params
        });

    }

    // DEV ONLY: answers for preview-only reads (questPreview: {list, details, guidance};
    // objectPreview: {catalog: {revision, entries}, libraries}; object changes answer a revision).
    function previewAnswer(method, params) {
        if (objectPreview && /^(objects|libraries)\./.test(method)) {
            if (method === 'objects.catalog') return objectPreview.catalog || {revision: 0, entries: []};
            if (method === 'libraries.list') return {libraries: objectPreview.libraries || []};
            if (method === 'objects.pocket') return {revision: 1, itemId: 'pocket-1'};
            if (method === 'objects.place') return {revision: 1, id: 'u-0a0b0c'};
            if (method === 'libraries.install') return {revision: 1, id: 'org.example.preview', version: '1.0.0'};
            return {revision: 1};
        }
        if (/^(npcs|paths|interaction)\./.test(method)) {
            if (method === 'paths.list') return {paths: pathPreview || []};
            if (method === 'npcs.spawn') return {revision: 1, id: 'u-npc001'};
            if (method === 'paths.draw') return {revision: 1, id: 'path-9'};
            if (method === 'paths.set') return {revision: 1, id: params.path.id || 'path-9'};
            if (method === 'paths.finish') return {revision: 1, id: 'path-9', bound: null};
            return {revision: 1};
        }
        if (!questPreview) return null;
        if (method === 'quests.list') return {quests: questPreview.list || []};
        if (method === 'quests.get') { var d = (questPreview.details || {})[Quests.refKey(params.questRef)]; return d ? {quest: d} : null; }
        if (method === 'guidance.get') return questPreview.guidance || null;
        if (method === 'guidance.set' && questPreview.guidance) {
            var g = JSON.parse(JSON.stringify(questPreview.guidance));
            Object.keys(params.patch).forEach(k => { g.config[k] = params.patch[k] === null ? g.defaults[k] : params.patch[k]; });
            questPreview = Object.assign({}, questPreview, {guidance: g});
            return g;
        }
        return null;
    }

    function questResult(method, params, result) {
        if (!method || !result) return;
        if (method === 'quests.list') { questList = result.quests; questsRefreshed(); return; }
        if (method === 'quests.get') { if (Quests.refKey(result.quest.questRef) === selectedQuest) questDetail = result.quest; return; }
        if (method === 'guidance.get' || method === 'guidance.set') { guidance = result; return; }
        if (method === 'quests.create' && result.questRef) { selectedQuest = Quests.refKey(result.questRef); questDetail = null; }
        if (method === 'quests.delete' && params && Quests.refKey(params.questRef) === selectedQuest) { selectedQuest = ''; questDetail = null; }
        if (/^quests\./.test(method)) questRefresh.restart();
        questActionDone(method, params || null, result);
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
            if (msg.value.theme !== undefined) Tokens.light = msg.value.theme === 'paper';
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
            if (msg.hold && (!menuHold || menuHold.startedAtMs !== msg.hold.startedAtMs))
                holdStats = Object.assign({}, holdStats, {seen: holdStats.seen + 1});
            menuHold = msg.hold;
            break;
        case 'clock':
            clockOffset = msg.offsetMs; clockKnown = true;
            break;
        case 'quest.progress':
            presentToast(Quests.toastFor('quest.progress', msg.value, focusState));
            if (questsVisible) questRefresh.restart();
            break;
        case 'focus.phase':
            focusPulse(msg.value.phase);
            presentToast(Quests.toastFor('focus.phase', msg.value, focusState, guidanceConfig));
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
                questList = []; questDetail = null; guidance = null; guidanceRequested = false; clockKnown = false;
                objectCatalog = []; objectCatalogRevision = -1; objectCatalogFor = -1; objectCatalogLoaded = false; libraries = null; objectFeedback = null;
                pathList = []; pathsLoaded = false; npcChoice = null; npcInteractionKey = ''; pathsSignature = ''; spawnRef = ''; rebindId = '';
                toasts = []; banners = []; deferredToasts = [];
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
            if (dev) {
                lastStateMessage = msg;
                if (statePreview && msg.state) msg = Object.assign({}, msg, {state: mergePreview(msg.state, statePreview)});
            }
            if (!state || !state.world || !msg.state || !msg.state.world || state.world.id !== msg.state.world.id) { camera = null; outline = null; }
            if (state && msg.state && state.workspaces && msg.state.workspaces && state.workspaces.currentId !== msg.state.workspaces.currentId) showBanner('WORKSPACE FOCUSED');
            var contentChange=Manipulation.changedContent(state,msg.state);
            var previousQuests = state ? state.quests || null : null;
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
            if (questsVisible && JSON.stringify(previousQuests) !== JSON.stringify(state.quests || null)) questRefresh.restart();
            if (!guidanceRequested && available('guidance.get')) refreshGuidance();
            if (objectsState && socket.connected) seedDemoSources();
            // objects.catalogRevision bumps when any catalog source changes.
            if (objectsVisible && objectsState && objectsState.catalogRevision !== objectCatalogFor && !catalogRefresh.running) catalogRefresh.restart();
            // IPC 0.23: act once on each new character interaction; refresh routes when paths change.
            var interaction = state.npcs ? state.npcs.interaction : null;
            var interactionKey = Npcs.interactionKey(interaction);
            if (interactionKey !== npcInteractionKey) { npcInteractionKey = interactionKey; if (interaction) handleInteraction(interaction); }
            var editorPaths = state.editor && state.editor.paths ? state.editor.paths : [];
            var nextPaths = editorPaths.map(p => p.id + ':' + p.points.length + ':' + (p.stops ? p.stops.length : 0)).join(',') + '|' + JSON.stringify(state.npcs ? state.npcs.drawing : null);
            if (nextPaths !== pathsSignature) { pathsSignature = nextPaths; if (charactersVisible) pathsRefresh.restart(); }
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
                // The HUD's animations follow the world's reduced motion setting.
                if (graphics && graphics.effective && graphics.effective.reduced_motion !== undefined) Tokens.reducedMotion = !!graphics.effective.reduced_motion;
            }
            if (msg.method === 'settings.get' || msg.method === 'settings.set') {
                settingsState = msg.result;
                if (msg.method === 'settings.set') { refreshPlayer(); action('graphics.get', {}); }
            }
            if (msg.method === 'input.preview' || msg.method === 'input.get') inputFeedback(msg.result);
            if (msg.method === 'player.get' || msg.method === 'player.set') player = msg.result;
            if (msg.method === 'surface.pocket' || msg.method === 'surface.unpocket') pocketFeedback(msg.method, msg.result);
            questResult(msg.method, msg.params, msg.result);
            objectResult(msg.method, msg.params, msg.result);
            npcResult(msg.method, msg.params, msg.result);
            break;
        case 'sources':
            if (msg.op === 'status') { sourcesStatus = msg; if (msg.seq === sourcesStatusSeq) sourcesStatusSeq = 0; }
            sourcesReply(msg);
            break;
        case 'interaction.prompt':
            npcChoice = msg.value || null;
            break;
        case 'menu.panel':
            if (msg.panel === 'map') tab = 0;
            break;
        case 'director':
            director = msg.open;
            if (!msg.open) mapFocus = null;
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
            if (msg.code === 'shell.action' && msg.method === 'movement.set') { movementRefusal = String(msg.message).replace(/^-?\d+:\s*/, ''); movementRefusalTimer.restart(); }
            if (msg.code === 'shell.action' && (msg.method === 'surface.pocket' || msg.method === 'surface.unpocket')) pocketFeedback(msg.method, null, msg.message);
            if (msg.code === 'shell.action' && /^(quests|focus|guidance)\./.test(msg.method || '')) {
                questFeedback = Quests.errorText(msg.method, msg.message); questFeedbackTimer.restart();
                questActionFailed(msg.method, msg.params || null, questFeedback);
                if (msg.method === 'quests.get' && msg.params && Quests.refKey(msg.params.questRef) === selectedQuest) questDetail = null;
                break; // shown on the Quests page, not as a HUD notice
            }
            if (msg.code === 'shell.action' && /^(npcs|paths|interaction)\./.test(msg.method || '')) {
                var npcRefusal = Npcs.errorToast(msg.method, msg.error || null, msg.message);
                showToast(npcRefusal);
                sayObjects(npcRefusal.line + (npcRefusal.detail ? ' (' + npcRefusal.detail + ')' : ''), 'warning');
                objectActionFailed(msg.method, msg.params || null, npcRefusal.line);
                break;
            }
            if (Npcs.noticeToast(msg)) {
                // Character and route notices (IPC 0.23 runtime.notice codes) are short toasts.
                showToast(Npcs.noticeToast(msg));
                if (charactersVisible) pathsRefresh.restart();
                break;
            }
            if (msg.code === 'shell.action' && /^(objects|libraries)\./.test(msg.method || '')) {
                // A short toast with core's words (and the placement rule), and the page line.
                var refusal = Objects.errorToast(msg.method, msg.error || null, msg.message);
                showToast(refusal);
                sayObjects(refusal.line + (refusal.detail ? ' (' + refusal.detail + ')' : ''), 'warning');
                objectActionFailed(msg.method, msg.params || null, refusal.line);
                break;
            }
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
