import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import "theme"
import "components"
import "components/LayoutAudit.js" as Audit

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
                      ShellState.status === 'disconnected' || ShellState.status === 'connecting')
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
                visible: ShellState.active
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
            if (ShellState.dev) ShellState.tab = Math.max(0, Math.min(7, index));
        }
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
        function cycleHud(): void { if (ShellState.dev) ShellState.cycleHud(); }
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
            if (!choice) return false;
            choice.forceActiveFocus();
            return true;
        }
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
            var result = {};
            ['hudCursorChip','hudCursorText','hudClimbPrompt','hudClimbText','hudWorldHints','hudToolHint'].forEach(name => {
                var item = Audit.find(view,name);
                result[name] = item ? {visible:true,text:item.text || '',truncated:!!item.truncated} : {visible:false};
            });
            return JSON.stringify(result);
        }
        function status(): string {
            return JSON.stringify({
                worldStyle: Tokens.skin.worldId || null, styleId: Tokens.skin.id || null, styleVersion: Tokens.skin.version || null, worldStyles: Tokens.worldStyles, hudFrame: ShellState.hudFrame,
                concept: Tokens.hudConcept, curvature: Tokens.hudCurvature, banner: ShellState.banner, subtype: HudData.subtype,
                graphics: ShellState.graphics,
                menuHold: ShellState.menuHold,
                holdProgress: root.hudViews.find(v => v.outputScreenName === ShellState.screenName)?.holdProgress || 0,
                captured: ShellState.lastCapturedInput,
                status: ShellState.status, protocol: ShellState.protocol, screen: ShellState.screenName,
                lease: ShellState.lease, director: ShellState.director,
                revision: ShellState.revision, tab: ShellState.tab,
                warp: ShellState.warpActive, phase: ShellState.transition.phase,
                world: ShellState.state && ShellState.state.world ? ShellState.state.world.id : null,
                mode: ShellState.state && ShellState.state.interaction ? ShellState.state.interaction.mode : null,
                tool: ShellState.state && ShellState.state.interaction ? ShellState.state.interaction.tool : null,
                workspaces: ShellState.workspaces,
                appDetails: ShellState.state && ShellState.state.apps ? ShellState.state.apps : [],
                apps: ShellState.state && ShellState.state.apps ? ShellState.state.apps.length : 0,
                map: ShellState.mapData !== null, places: ShellState.places, markers: ShellState.markers.length
            });
        }
    }
}
