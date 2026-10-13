import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import "theme"
import "components"
import "components/LayoutAudit.js" as Audit
import "Quests.js" as Quests
import "Library.js" as Library

ShellRoot {
    id: root
    property var directorViews: []
    property var hudViews: []
    property var warpViews: []
    property string lastScreen: Quickshell.env('HYPRUNE_OUTPUT_SCREEN')

    Connections {
        target: ShellState
        function onScreenNameChanged() {
            if (ShellState.screenName !== '') root.lastScreen = ShellState.screenName;
        }
    }

    // Passive HUD and recovery status stay on the explicitly mapped world screen.
    Variants {
        model: Quickshell.screens
        delegate: PanelWindow {
            required property var modelData
            screen: modelData
            visible: modelData.name === root.lastScreen &&
                     ((ShellState.active && !ShellState.director && !ShellState.warpActive) ||
                      ShellState.status === 'disconnected' || ShellState.status === 'connecting' || ShellState.readyText !== '')
            anchors { left: true; right: true; top: true; bottom: true }
            color: 'transparent'
            exclusionMode: ExclusionMode.Ignore
            WlrLayershell.namespace: 'hyprune-hud'
            WlrLayershell.layer: WlrLayer.Overlay
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
            mask: Region {}

            Hud {
                id: hudScene
                property string outputScreenName: modelData.name
                Component.onCompleted: root.hudViews = root.hudViews.concat([hudScene])
                property real uiScale: Math.max(1, Math.min(parent.width / 1920, parent.height / 1080, 1.5))
                width: parent.width / uiScale
                height: parent.height / uiScale
                scale: uiScale
                transformOrigin: Item.TopLeft
                visible: ShellState.active && !ShellState.authoredCamera && !HudData.focusMode
            }

            // RFC-0012: the focus timer chip in use (E) mode, where the HUD itself is hidden.
            FocusChip {
                property real uiScale: hudScene.uiScale
                visible: ShellState.active && !ShellState.director && HudData.focusMode && !!ShellState.state.interaction && ShellState.state.interaction.mode === 'typing' &&
                         Quests.chipVisible(ShellState.focusState, true, null)
                anchors { right: parent.right; top: parent.top; margins: 24 }
                width: implicitWidth; height: implicitHeight
            }

            Item {
                objectName:'readyNotification'
                visible:ShellState.live && ShellState.readyText!=='' && !ShellState.active
                anchors.horizontalCenter:parent.horizontalCenter; y:40
                width:Math.min(620,parent.width-48); height:readyCaption.implicitHeight+32
                HudTile { anchors.fill:parent; color:Tokens.panel; borderColor:Tokens.hudAccent; borderWidth:Tokens.hudConcept==='Instrument' ? 1 : 0 }
                Rectangle { width:Tokens.hudConcept==='Minimal' ? 2 : 4; height:parent.height; color:Tokens.hudAccent }
                HudText { id:readyCaption; objectName:'readyNotificationText'; x:18;y:16;width:parent.width-36; text:ShellState.readyText; font.pixelSize:14; maximumLineCount:3; wrapMode:Text.Wrap; font.family:Tokens.hudConcept==='Instrument' ? Tokens.mono : Tokens.hudFont }
            }

            Rectangle {
                visible: !ShellState.live
                anchors { top: parent.top; horizontalCenter: parent.horizontalCenter; topMargin: 40 }
                width: Math.min(600, parent.width - 40)
                height: 65
                color: Tokens.panel
                radius: 3
                border.color: Tokens.gold

                Column {
                    anchors.centerIn: parent
                    spacing: 6
                    HudLabel {
                        text: 'HYPRUNE  /  ' + ShellState.status.toUpperCase()
                        color: Tokens.gold
                        font.pixelSize: 12
                    }
                    HudLabel {
                        text: ShellState.error || 'Waiting for a fresh core connection'
                        color: Tokens.muted
                        font.pixelSize: 11
                        width: parent.parent.width - 40
                        horizontalAlignment: Text.AlignHCenter
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }

    // RFC-0012 desktop focus chip (guidance focus.desktop_chip) and focus-phase toasts while
    // the world is not active. Passive: no input region, no keyboard.
    Variants {
        model: Quickshell.screens
        delegate: PanelWindow {
            id: desktopFocus
            required property var modelData
            readonly property bool chip: ShellState.live && !ShellState.state.runtime.active && Quests.chipVisible(ShellState.focusState, false, ShellState.guidanceConfig)
            readonly property var toast: ShellState.toasts.length && ShellState.toasts[0].category === 'focus' ? ShellState.toasts[0] : null
            screen: modelData
            visible: modelData.name === root.lastScreen && ShellState.live && !ShellState.state.runtime.active && (chip || !!toast)
            anchors { top: true; right: true }
            margins { top: 16; right: 16 }
            implicitWidth: 300
            implicitHeight: Math.max(1, desktopColumn.height)
            color: 'transparent'
            exclusionMode: ExclusionMode.Ignore
            WlrLayershell.namespace: 'hyprune-focus'
            WlrLayershell.layer: WlrLayer.Overlay
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
            mask: Region {}
            Column {
                id: desktopColumn
                width: parent.width
                spacing: 10
                FocusChip { objectName: 'desktopFocusChip'; anchors.right: parent.right; visible: desktopFocus.chip; width: implicitWidth; height: implicitHeight }
                QuestToast { width: parent.width; height: implicitHeight; toast: desktopFocus.toast }
            }
        }
    }

    // ShellState.director becomes true only after an accepted exclusive overlay.
    Variants {
        model: Quickshell.screens
        delegate: PanelWindow {
            required property var modelData
            screen: modelData
            visible: ShellState.active && ShellState.director && !ShellState.warpActive &&
                     modelData.name === ShellState.screenName
            anchors { left: true; right: true; top: true; bottom: true }
            color: Tokens.light ? '#f4eff3ed' : '#f40a111d'
            exclusionMode: ExclusionMode.Ignore
            WlrLayershell.namespace: 'hyprune-director'
            WlrLayershell.layer: WlrLayer.Overlay
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive

            Item {
                anchors.fill: parent
                property real uiScale: Math.max(1, Math.min(width / 1920, height / 1080, 1.5))
                Director {
                    id: directorScene
                    property string outputScreenName: modelData.name
                    Component.onCompleted: root.directorViews = root.directorViews.concat([directorScene])
                    x: 20 * parent.uiScale
                    y: 20 * parent.uiScale
                    width: parent.width / parent.uiScale - 40
                    height: parent.height / parent.uiScale - 40
                    scale: parent.uiScale
                    transformOrigin: Item.TopLeft
                }
            }
        }
    }

    // Capture note prompt (IPC 0.17). Same namespace as the Director, so core gives it the
    // keyboard while the shell holds exclusive input; never shown with the Director.
    Variants {
        model: Quickshell.screens
        delegate: PanelWindow {
            required property var modelData
            screen: modelData
            visible: ShellState.active && ShellState.notePrompt !== '' && !ShellState.director && !ShellState.warpActive &&
                     modelData.name === ShellState.screenName
            anchors { bottom: true }
            margins.bottom: 96
            implicitWidth: notePrompt.implicitWidth
            implicitHeight: notePrompt.implicitHeight
            color: 'transparent'
            exclusionMode: ExclusionMode.Ignore
            WlrLayershell.namespace: 'hyprune-director'
            WlrLayershell.layer: WlrLayer.Overlay
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive
            NotePrompt { id: notePrompt; anchors.fill: parent }
        }
    }

    // IPC 0.23 character choice list. The bridge took exclusive input for it (like the note
    // prompt, same namespace), so it has the keyboard and the pointer; never with the Director.
    Variants {
        model: Quickshell.screens
        delegate: PanelWindow {
            required property var modelData
            screen: modelData
            visible: ShellState.active && !!ShellState.npcChoice && !ShellState.director && !ShellState.warpActive &&
                     modelData.name === ShellState.screenName
            anchors { bottom: true }
            margins.bottom: 190
            implicitWidth: npcChoice.implicitWidth
            implicitHeight: npcChoice.implicitHeight
            color: 'transparent'
            exclusionMode: ExclusionMode.Ignore
            WlrLayershell.namespace: 'hyprune-director'
            WlrLayershell.layer: WlrLayer.Overlay
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive
            NpcChoice { id: npcChoice; anchors.fill: parent }
        }
    }

    // A jump is presentation only: it cannot intercept emergency input.
    Variants {
        model: Quickshell.screens
        delegate: PanelWindow {
            required property var modelData
            screen: modelData
            visible: ShellState.active && modelData.name === ShellState.screenName &&
                     (ShellState.warpActive || warpScene.opacity > 0)
            anchors { left: true; right: true; top: true; bottom: true }
            color: 'transparent'
            exclusionMode: ExclusionMode.Ignore
            WlrLayershell.namespace: 'hyprune-warp'
            WlrLayershell.layer: WlrLayer.Overlay
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
            mask: Region {}
            Warp {
                id: warpScene
                property string outputScreenName: modelData.name
                Component.onCompleted: root.warpViews = root.warpViews.concat([warpScene])
                anchors.fill: parent
                activeOutput: modelData.name === ShellState.screenName
            }
        }
    }

    // Only explicit development fixtures expose automation commands. Capture
    // tools always target this child PID within the locked nested session.
    IpcHandler {
        target: 'preview'
        function workspaceWarp(): void {
            if (ShellState.dev && ShellState.state && ShellState.state.world)
                ShellState.action('surface.focus', {
                    surfaceId: ShellState.state.world.id === 'com.hyprune.garden' ? 'workspace-0' : 'workspace-2',
                    intent: 'keyboard'
                });
        }
        function warp(): void {
            if (ShellState.dev && ShellState.state && ShellState.state.world)
                ShellState.send({
                    type: 'dev.warp',
                    worldId: ShellState.state.world.id === 'com.hyprune.garden' ? 'com.hyprune.observatory' : 'com.hyprune.garden'
                });
        }
        function open(): void {
            if (ShellState.dev) ShellState.send({type: 'dev.open'});
        }
        function close(): void {
            if (ShellState.dev) ShellState.close();
        }
        function tab(index: int): void {
            if (ShellState.dev) ShellState.tab = Math.max(0, Math.min(ShellState.tabCount - 1, index));
        }
        // By name: map, quests, objects, library, places, surfaces, workspaces, help, whatsnew, settings, performance.
        function tabNamed(name: string): void {
            const index = ShellState.tabKeys.indexOf(name);
            if (ShellState.dev && index >= 0) ShellState.tab = index;
        }
        // IPC 0.21 preview (dev only): quests.list/get and guidance.get answers, events, keys.
        function questPreview(json: string): void {
            if (!ShellState.dev) return;
            ShellState.questPreview = json ? JSON.parse(json) : null;
            if (ShellState.questPreview) ShellState.refreshGuidance();
        }
        function questEvent(method: string, json: string): void { if (ShellState.dev) ShellState.receive({type: method, value: JSON.parse(json)}); }
        function questSelect(key: string): void { if (ShellState.dev) ShellState.selectQuest(key); }
        function questForm(json: string): bool {
            if (!ShellState.dev || !ShellState.director) return false;
            var page = Audit.find(root.directorViews.find(v => v.outputScreenName === ShellState.screenName), 'directorQuests');
            if (!page) return false;
            page.openForm(json ? JSON.parse(json) : null);
            return true;
        }
        function mapMarkers(): string {
            if (!ShellState.dev || !ShellState.director) return '[]';
            return JSON.stringify(Audit.findAll(root.directorViews.find(v => v.outputScreenName === ShellState.screenName), 'mapMarker:'));
        }
        // IPC 0.22 preview (dev only): objects.catalog / libraries.list answers and page state.
        function objectPreview(json: string): void {
            if (!ShellState.dev) return;
            ShellState.objectPreview = json ? JSON.parse(json) : null;
            if (ShellState.objectPreview) ShellState.refreshCatalog();
        }
        function objectsView(view: string): void { if (ShellState.dev && ['catalog', 'placed', 'characters'].indexOf(view) >= 0) ShellState.objectsView = view; }
        // IPC 0.23 preview (dev only): paths.list answer, spawn / rebind panel, characters, choice list.
        // json: {"paths": [...]} (qs ipc splits a top-level [list] argument).
        function pathPreview(json: string): void {
            if (!ShellState.dev) return;
            ShellState.pathPreview = json ? JSON.parse(json).paths : null;
            ShellState.refreshPaths();
        }
        function npcSpawn(ref: string): void { if (ShellState.dev) ShellState.startSpawn(ref); }
        function npcRebind(id: string): void { if (ShellState.dev) ShellState.startRebind(id); }
        function npcSelect(id: string): void { if (ShellState.dev) ShellState.selectedCharacter = id; }
        function npcRoute(index: int): bool {
            if (!ShellState.dev || !ShellState.director) return false;
            var panel = Audit.find(root.directorViews.find(v => v.outputScreenName === ShellState.screenName), 'npcSpawn');
            if (!panel || index < 0 || index >= panel.rows.length) return false;
            panel.cursor = index;
            return true;
        }
        function npcSettings(json: string): bool {
            if (!ShellState.dev || !ShellState.director) return false;
            var panel = Audit.find(root.directorViews.find(v => v.outputScreenName === ShellState.screenName), 'npcSpawn');
            if (!panel) return false;
            var s = JSON.parse(json);
            ['speed', 'phase', 'reverse', 'accent', 'stops'].forEach(k => { if (s[k] !== undefined) panel[k] = s[k]; });
            return true;
        }
        // The bridge's interaction.prompt event (a choice list), or null.
        function npcChoice(json: string): void { if (ShellState.dev) ShellState.receive({type: 'interaction.prompt', value: json ? JSON.parse(json) : null}); }
        function npcNotice(code: string, message: string): void { if (ShellState.dev) ShellState.receive({type: 'notice', level: 'info', code: code, message: message}); }
        function objectSelect(id: string): void { if (ShellState.dev) ShellState.selectedObject = id; }
        function objectFilter(source: string, category: string, query: string): bool {
            if (!ShellState.dev || !ShellState.director) return false;
            var page = Audit.find(root.directorViews.find(v => v.outputScreenName === ShellState.screenName), 'directorObjects');
            if (!page) return false;
            page.source = source || 'all'; page.category = category; page.query = query;
            return true;
        }
        // A finished object request as core would answer it: a result object, or an error
        // {code, message, rule?} (shown as a toast).
        function objectResult(method: string, params: string, json: string): void {
            if (!ShellState.dev) return;
            var answer = JSON.parse(json), echoed = params ? JSON.parse(params) : {};
            if (answer && answer.code !== undefined && answer.message !== undefined)
                ShellState.receive({type: 'notice', level: 'warning', code: 'shell.action', method: method, params: echoed,
                                    message: answer.code + ': ' + answer.message, error: answer});
            else ShellState.receive({type: 'action', method: method, params: echoed, result: answer});
        }
        // RFC-0015 Library (dev only): view, Browse filters, the selected install, the Add source form.
        function libraryView(view: string): void { if (ShellState.dev && ['browse', 'installed', 'sources'].indexOf(view) >= 0) ShellState.libraryView = view; }
        function libraryRefresh(): void { if (ShellState.dev) ShellState.refreshLibrary(); }
        // Another CLI command line ('' restores $HYPRUNE_CLI / hyprune), e.g. a missing one.
        function libraryCommand(line: string): void { if (ShellState.dev) { ShellState.libraryCli = Library.cliCommand(line || Quickshell.env('HYPRUNE_CLI')); ShellState.refreshLibrary(); } }
        function libraryFilter(source: string, type: string, query: string): bool {
            if (!ShellState.dev || !ShellState.director) return false;
            var page = Audit.find(root.directorViews.find(v => v.outputScreenName === ShellState.screenName), 'directorLibrary');
            if (!page) return false;
            page.source = source || 'all'; page.type = type || 'all'; page.query = query;
            return true;
        }
        function librarySelect(id: string): bool {
            if (!ShellState.dev || !ShellState.director) return false;
            var page = Audit.find(root.directorViews.find(v => v.outputScreenName === ShellState.screenName), 'directorLibrary');
            if (!page) return false;
            if (ShellState.libraryView === 'sources') page.selectedSource = id; else page.selected = id;
            return true;
        }
        function libraryForm(url: string, label: string, sha256: string): bool {
            if (!ShellState.dev || !ShellState.director) return false;
            var view = root.directorViews.find(v => v.outputScreenName === ShellState.screenName);
            var fields = [['source-url', url], ['source-label', label], ['source-sha256', sha256]];
            fields.forEach(f => { var field = Audit.find(view, f[0]); if (field) field.text = f[1]; });
            return !!Audit.find(view, 'source-url');
        }
        // Give a named Director control keyboard focus (nested keyboard checks).
        function focusNamed(name: string): bool {
            if (!ShellState.dev || !ShellState.director) return false;
            var item = Audit.find(root.directorViews.find(v => v.outputScreenName === ShellState.screenName), name);
            if (!item) return false;
            item.forceActiveFocus();
            return true;
        }
        function clockOffset(offset: real): void { if (ShellState.dev) ShellState.receive({type: 'clock', offsetMs: offset}); }
        function monotonicNow(): real { return ShellState.monotonicNow() || 0; }
        function select(index: int): void {
            if (ShellState.dev && ShellState.places[index]) {
                ShellState.selectedPlace = ShellState.places[index].id;
                ShellState.waypoint(ShellState.places[index]);
            }
        }
        function travel(index: int): void {
            if (ShellState.dev && ShellState.places[index]) ShellState.travel(ShellState.places[index]);
        }
        function worldStyles(enabled: bool): void { if (ShellState.dev) ShellState.preference({worldStyles:enabled}); }
        function manipulation(json: string): void {
            if (ShellState.dev) {
                var before=ShellState.manipulationPreview, next=JSON.parse(json);
                ShellState.manipulationPreview=next;
                if (next && next.content && before && (!before.content || next.content.serial!==before.content.serial)) ShellState.contentFeedback(next.content);
            }
        }
        function concept(name: string): void { if (ShellState.dev) ShellState.setConcept(name); }
        function resource(name: string): void { if (ShellState.dev) ShellState.preference({resource:name}); }
        function curvature(amount: real): void {
            if (ShellState.dev) { ShellState.preference({curved:amount > 0,curvature:amount}); }
        }
        function motion(reduced: bool): void {
            if (ShellState.dev) Tokens.reducedMotion = reduced;
        }
        function theme(light: bool): void {
            if (ShellState.dev) Tokens.light = light;
        }
        function zone(): void {
            if (ShellState.dev) ShellState.receive({
                type: 'zone', name: 'The arrival garden', subtitle: 'OBSERVATORY / SECTOR 01'
            });
        }
        function workspace(id: int): void { if (ShellState.dev) ShellState.action('workspace.activate',{id:id}); }
        function drive(index: int): void { if (ShellState.dev && ShellState.places[index]) ShellState.send({type:'drive',position:ShellState.places[index].position}); }
        function inputCapture(mode: string, action: string, slot: int): void { if(ShellState.dev) ShellState.beginInputCapture(mode,action,slot); }
        function settingsSection(section: int): void { if (ShellState.dev) ShellState.browseSettings(section); }
        function settingsScroll(fraction: real): void { if (ShellState.dev) ShellState.scrollSettings(Math.max(0,Math.min(1,fraction))); }
        function graphicsFocus(key: string): bool {
            if (!ShellState.dev || !ShellState.director) return false;
            var choice = Audit.find(root.directorViews.find(v => v.outputScreenName === ShellState.screenName), 'graphics-' + key);
            if (!choice || !choice.enabled) return false;
            choice.forceActiveFocus();
            return true;
        }
        // IPC 0.20 Director preview (dev only): merge state fields, expose methods, feed results.
        function statePreview(json: string, methods: string): void { if (ShellState.dev) ShellState.setStatePreview(json ? JSON.parse(json) : null, methods ? methods.split(',') : []); }
        function pocketResult(surfaceId: string, method: string, json: string): void {
            if (!ShellState.dev) return;
            ShellState.pocketTarget = surfaceId;
            if (json.charAt(0) === '{') ShellState.receive({type: 'action', method: method, result: JSON.parse(json)});
            else ShellState.receive({type: 'notice', level: 'warning', code: 'shell.action', method: method, message: json});
        }
        // Press a named control (Button or map button) as a click would.
        function press(name: string): bool {
            if (!ShellState.dev || !ShellState.director) return false;
            var item = Audit.find(root.directorViews.find(v => v.outputScreenName === ShellState.screenName), name);
            if (!item || !item.enabled) return false;
            item.clicked();
            return true;
        }
        function mapView(zoom: real, panX: real, panY: real, level: string): string {
            if (!ShellState.dev || !ShellState.director) return '{}';
            var map = Audit.find(root.directorViews.find(v => v.outputScreenName === ShellState.screenName), 'mapView');
            if (!map) return '{}';
            map.pickedLevel = level === 'auto' ? '' : level;
            map.setView(zoom, [panX, panY]);
            return JSON.stringify({zoom: map.zoom, pan: [map.panX, map.panY], level: map.level ? map.level.id : null,
                                   auto: map.autoLevel, picked: map.pickedLevel, themed: map.showingLevel, scale: map.scaleBar});
        }
        function playerPreview(json: string): void { if (ShellState.dev) ShellState.playerPreview = json ? JSON.parse(json) : null; }
        function graphicsPatch(patch: string): void { if (ShellState.dev) ShellState.action("graphics.set", {patch:JSON.parse(patch)}); }
        function inputSave(): void { if(ShellState.dev) ShellState.saveInputDraft(); }
        function overlayStyle(): void { if(ShellState.dev) ShellState.action("overlay.style",{style:{waypointColor:[1,0,0],fontFamily:"DejaVu Sans Mono"}}); }
        function routeTo(index: int): void { if(ShellState.dev && ShellState.places[index]) ShellState.action("route.set",{points:[{position:ShellState.places[index].position}]}); }
        function scrollPage(fraction: real): void {
            if (ShellState.dev && ShellState.director)
                Audit.scroll(root.directorViews.find(v => v.outputScreenName === ShellState.screenName), fraction);
        }
        function layoutAudit(): string {
            var views = ShellState.warpActive ? root.warpViews : ShellState.director ? root.directorViews : root.hudViews;
            var view = views.find(v => v.outputScreenName === ShellState.screenName);
            return ShellState.dev ? JSON.stringify(Audit.inspect(view)) : '{}';
        }
        function brandMarks(): string {
            if (!ShellState.dev || !ShellState.director) return '[]';
            var view = root.directorViews.find(v => v.outputScreenName === ShellState.screenName);
            return JSON.stringify(['brandMark:director','brandMark:about'].map(name => Audit.find(view,name)).filter(m => m).map(function(m) {
                var p = m.mapToItem(null, 0, 0), q = m.mapToItem(null, m.width, m.height);
                return {name:m.objectName, size:m.size, pixelRatio:m.pixelRatio, physicalSize:m.physicalSize, variant:m.variant,
                        color:m.color.toString(), sceneBox:[p.x,p.y,q.x,q.y], inkLeft:m.inkLeft, inkRight:m.inkRight, inkTop:m.inkTop, inkBottom:m.inkBottom};
            }));
        }
        function contrastProbe(mode: string): string {
            if (!ShellState.dev || ['normal','background','mask','white','white-background'].indexOf(mode) < 0) return '{}';
            var view = root.hudViews.find(v => v.outputScreenName === ShellState.screenName);
            if (!view) return '{}';
            view.contrastProbe = mode;
            return JSON.stringify(['hudRadarCaption','hudNavigation','hudInputStatus'].map(name => Audit.find(view,name).contrastRegion()));
        }
        function interactionHud(): string {
            if (!ShellState.dev) return '{}';
            var view = root.hudViews.find(v => v.outputScreenName === ShellState.screenName);
            var result = {view:{width:view.width,height:view.height}};
            ['hudToolDeck','hudCursorChip','hudCursorText','hudClimbPrompt','hudClimbText','hudWorldHints','hudToolHint','hudPlacementTile','hudPlacementQueue','hudPlacementTitle','hudPlacementClass','hudPlacementSize','hudPlacementCube','hudPocketObjects','hudUnplacedBadge','hudToolHints','hudGhostIndicator','hudCarryOrientation','hudContentScale'].forEach(name => {
                var item = Audit.find(view,name);
                var at = item ? item.mapToItem(view,0,0) : null;
                result[name] = item ? {visible:true,text:item.text || '',truncated:!!item.truncated,x:at.x,y:at.y,width:item.width,height:item.height} : {visible:false};
            });
            return JSON.stringify(result);
        }
        function status(): string {
            return JSON.stringify({
                outline: ShellState.outline,
                hudVisible: !!root.hudViews.find(v => v.outputScreenName === ShellState.screenName)?.visible, camera: ShellState.camera, capabilities: ShellState.capabilities,
                worldStyle: Tokens.skin.worldId || null, styleId: Tokens.skin.id || null, styleVersion: Tokens.skin.version || null, worldStyles: Tokens.worldStyles, hudFrame: ShellState.hudFrame,
                manipulation: HudData.manipulation, readyText:ShellState.readyText, concept: Tokens.hudConcept, curvature: Tokens.hudCurvature, banner: ShellState.banner, subtype: HudData.subtype,
                graphics: ShellState.graphics, player: ShellState.playerSettings, playerSupported: ShellState.playerSupported,
                menuHold: ShellState.menuHold,
                holdFilling: root.hudViews.find(v => v.outputScreenName === ShellState.screenName)?.holdFilling || false,
                holdStats: ShellState.holdStats,
                focusChip: (function() {
                    var view = root.hudViews.find(v => v.outputScreenName === ShellState.screenName);
                    var time = Audit.find(view, 'hudFocusTime'), phase = Audit.find(view, 'hudFocusPhase');
                    return time ? {time: time.text, phase: phase ? phase.text : ''} : null;
                })(),
                focus: ShellState.focusState,
                quests: {selected: ShellState.selectedQuest, list: ShellState.questList.length, detail: ShellState.questDetail ? ShellState.questDetail.title : null,
                         feedback: ShellState.questFeedback, toasts: ShellState.toasts, banners: ShellState.banners, deferred: ShellState.deferredToasts.length,
                         guidance: ShellState.guidanceConfig, mapFocus: ShellState.mapFocus},
                objects: (function() {
                    var view = root.directorViews.find(v => v.outputScreenName === ShellState.screenName);
                    var page = ShellState.director ? Audit.find(view, 'directorObjects') : null;
                    var panel = page ? Audit.find(page, 'objectConfigure') : null;
                    return {supported: ShellState.objectsSupported, control: ShellState.objectsControl, view: ShellState.objectsView,
                            catalog: ShellState.objectCatalog.length, catalogRevision: ShellState.objectCatalogRevision, catalogFor: ShellState.objectCatalogFor,
                            shown: page ? page.shown.length : null, cursor: page ? page.cursor : null, confirm: page ? page.confirm : null,
                            selected: ShellState.selectedObject, sections: panel ? panel.sectionIds : [], feedback: ShellState.objectFeedback,
                            pocket: ShellState.unplacedObjects, selectedKind: ShellState.selectedKind, gizmo: ShellState.editorGizmo,
                            instances: ShellState.objectsState ? ShellState.objectsState.instances.length : 0};
                })(),
                npcs: (function() {
                    var view = root.directorViews.find(v => v.outputScreenName === ShellState.screenName);
                    var spawn = ShellState.director ? Audit.find(view, 'npcSpawn') : null;
                    var hud = root.hudViews.find(v => v.outputScreenName === ShellState.screenName);
                    function text(name) { var item = hud ? Audit.find(hud, name) : null; return item ? item.text : null; }
                    return {supported: ShellState.npcsSupported, paths: ShellState.pathList.length, spawnRef: ShellState.spawnRef, rebindId: ShellState.rebindId,
                            rows: spawn ? spawn.rows.map(r => r.kind === 'route' ? r.ref : r.kind) : [], cursor: spawn ? spawn.cursor : null,
                            request: spawn ? spawn.request : null, ready: spawn ? spawn.ready : null, stops: spawn ? spawn.stops : [],
                            selected: ShellState.selectedCharacter, characters: ShellState.characterInstances.length, choice: ShellState.npcChoice,
                            drawing: ShellState.npcDrawing, prompt: text('hudNpcPromptText'), promptNote: text('hudNpcPromptNote'), line: text('hudNpcLine'), drawingText: text('hudNpcDrawingText'),
                            toast: text('hudToastLine'),
                            interactionKey: ShellState.npcInteractionKey};
                })(),
                // The tool deck's header and subtype lines (tool 9 names the debug layer, IPC 0.26).
                toolDeck: (function() {
                    var hud = root.hudViews.find(v => v.outputScreenName === ShellState.screenName);
                    var header = hud ? Audit.find(hud, 'hudToolHeader') : null, subtype = hud ? Audit.find(hud, 'hudToolSubtype') : null;
                    return {tool: HudData.tool, header: header ? header.text : null, subtype: subtype ? subtype.text : null};
                })(),
                // Director > Surfaces: the pocket section label and the pocketed cards it draws.
                surfaces: (function() {
                    var view = root.directorViews.find(v => v.outputScreenName === ShellState.screenName);
                    var page = ShellState.director ? Audit.find(view, 'directorSurfaces') : null;
                    var label = page ? Audit.find(page, 'pocketSection') : null;
                    return {pocketed: page ? page.cards.pocketed.length : null, placed: page ? page.cards.placed.length : null,
                            pocketLabel: label ? label.text : null, pocketBadges: page ? Audit.findAll(page, 'pocketBadge:') : []};
                })(),
                library: (function() {
                    var view = root.directorViews.find(v => v.outputScreenName === ShellState.screenName);
                    var page = ShellState.director ? Audit.find(view, 'directorLibrary') : null;
                    var job = ShellState.libraryJob;
                    return {view: ShellState.libraryView, cli: ShellState.libraryCli, loaded: ShellState.libraryLoaded, readError: ShellState.libraryReadError,
                            sources: ShellState.librarySources.length, entries: ShellState.libraryEntries.length, installs: ShellState.libraryInstalls.map(i => i.id + '@' + (i.tag || i.version) + (i.pinned ? ':pinned' : '')),
                            shown: page ? page.shown.length : null, cursor: page ? page.cursor : null, confirm: page ? page.confirm : null,
                            form: page ? page.form : null, busy: ShellState.libraryBusy, feedback: ShellState.libraryFeedback,
                            job: job ? {kind: job.kind, phase: job.phase, stage: job.stage, stages: job.stages, args: job.args, progress: job.progress,
                                        error: job.error, result: job.result, sourceChange: job.plan ? job.plan.sourceChange : null} : null};
                })(),
                holdProgress: root.hudViews.find(v => v.outputScreenName === ShellState.screenName)?.holdProgress || 0,
                captured: ShellState.lastCapturedInput,
                status: ShellState.status, protocol: ShellState.protocol, screen: ShellState.screenName,
                lease: ShellState.lease, director: ShellState.director, notePrompt: ShellState.notePrompt, noteText: ShellState.noteText,
                revision: ShellState.revision, tab: ShellState.tab, tabName: ShellState.tabKeys[ShellState.tab] || '',
                warp: ShellState.warpActive, phase: ShellState.transition.phase,
                world: ShellState.state && ShellState.state.world ? ShellState.state.world.id : null,
                mode: ShellState.state && ShellState.state.interaction ? ShellState.state.interaction.mode : null,
                tool: ShellState.state && ShellState.state.interaction ? ShellState.state.interaction.tool : null,
                workspaces: ShellState.workspaces,
                appDetails: ShellState.state && ShellState.state.apps ? ShellState.state.apps : [],
                apps: ShellState.state && ShellState.state.apps ? ShellState.state.apps.length : 0,
                map: ShellState.mapData !== null, places: ShellState.places, markers: ShellState.markers.length,
                previewActions: ShellState.previewActions, surfaceFeedback: ShellState.surfaceFeedback,
                movement: ShellState.state ? ShellState.state.movement : null
            });
        }
    }
}
