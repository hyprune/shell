import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import "theme"
import "components"

ShellRoot {
    id: root
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
                property real uiScale: Math.min(parent.width / 1920, parent.height / 1080)
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
                property real uiScale: Math.min(width / 1920, height / 1080)
                Director {
                    x: 58 * parent.uiScale
                    y: 48 * parent.uiScale
                    width: (parent.width - 116 * parent.uiScale) / parent.uiScale
                    height: (parent.height - 96 * parent.uiScale) / parent.uiScale
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
            if (ShellState.dev) ShellState.tab = Math.max(0, Math.min(6, index));
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
        function inputSave(): void { if(ShellState.dev) ShellState.saveInputDraft(); }
        function status(): string {
            return JSON.stringify({
                captured: ShellState.lastCapturedInput,
                status: ShellState.status, protocol: ShellState.protocol, screen: ShellState.screenName,
                lease: ShellState.lease, director: ShellState.director,
                revision: ShellState.revision, tab: ShellState.tab,
                warp: ShellState.warpActive, phase: ShellState.transition.phase,
                world: ShellState.state && ShellState.state.world ? ShellState.state.world.id : null,
                mode: ShellState.state && ShellState.state.interaction ? ShellState.state.interaction.mode : null,
                tool: ShellState.state && ShellState.state.interaction ? ShellState.state.interaction.tool : null,
                apps: ShellState.state && ShellState.state.apps ? ShellState.state.apps.length : 0,
                map: ShellState.mapData !== null, places: ShellState.places, markers: ShellState.markers.length
            });
        }
    }
}
