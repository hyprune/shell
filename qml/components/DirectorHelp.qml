import Quickshell
import ".."
import "../HudManipulation.js" as Manipulation
import "../DirectorModel.js" as Model
import "../theme"
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Flickable {
    id: page
    clip: true
    contentWidth: width
    contentHeight: body.height
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: ScrollBar {}
RowLayout {
    id: body
    width: page.width - 16
    height: Math.max(implicitHeight, page.height)

    spacing: 24

    ColumnLayout {
        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: 24

        HudLabel {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: 'Keep your bearings.'
            font.pixelSize: 36
            font.weight: Font.Light
        }

        HudLabel {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: 'The world is an interface. Your desktop is always one action away.'
            font.pixelSize: 16
            color: Tokens.muted
        }

        Repeater {
            model: ShellState.supportsProtocol(6) ? [
                ['MOVEMENT','HJKL / WASD / arrows; Shift boosts, Space jumps/up, Ctrl crouches/down.'],
                ['USE / FOCUS','E uses a window or workspace in place. F zooms to fullscreen. Super+Tab or Back returns.'],
                ['MAP / SETTINGS','Hold Tab for the Director. Settings → Appearance selects Adventure, Instrument or Minimal.'],
                ['TOOLS','1–5 select tools; 9 is the debug tool, one debug layer at a time (Cycle steps through them). Primary, Secondary, Alternate and Cycle use the actions published by core below. Hold Super or Super+Shift for global gestures.'],
                ['CARRY ORIENTATION',HudData.placement.available ? Manipulation.binding(ShellState.state,'carry.facing','R')+' toggles Facing you / Keep angle while carrying.' : 'Carry orientation feedback requires the updated core.'],
                ['ROTATE',Manipulation.binding(ShellState.state,'rotate','Super+Ctrl+Wheel')+' rotates a carried window.'],
                ['CONTENT SCALE',HudData.placement.available ? Manipulation.binding(ShellState.state,'content.scale','Super+Shift+Wheel')+' adjusts client content scale. '+Manipulation.binding(ShellState.state,'window.reset','Super+Shift+MMB')+' resets it.' : 'Content scale and window reset require the updated core.'],
                ['SCOPE / DEBUG','Hold Q and wheel to zoom; F3/Y toggles debug; U saves a state capture.']
            ].concat(Manipulation.toolHelp(ShellState.state)) : [['OVERVIEW','Core owns the hold-to-open binding and timing.'],['ESCAPE','Return to desktop restores ordinary input through core.'],['KEYBOARD','Tab moves focus. Left / Right change view. Esc closes.']]

            delegate: RowLayout {
                required property var modelData

                Layout.fillWidth: true
                spacing: 24

                HudLabel {
                    text: modelData[0]
                    color: Tokens.accent
                    font.family: Tokens.mono
                    font.pixelSize: 11
                    Layout.preferredWidth: 110
                }

                HudLabel {
                    text: modelData[1]
                    font.pixelSize: 14
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
                    color: Tokens.muted
                }

            }

        }

        Item {
            Layout.fillHeight: true
        }

        HudLabel {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: 'SESSION  /  ' + ShellState.capabilities.length + ' grants · revision ' + ShellState.revision
            font.family: Tokens.mono
            font.pixelSize: 11
            color: Tokens.muted
        }

    }

    Rectangle {
        implicitHeight: preferences.implicitHeight + 52
        Layout.preferredWidth: 340
        Layout.minimumWidth: 260
        Layout.maximumWidth: Math.min(340, page.width * 0.4)
        Layout.fillHeight: true
        color: Tokens.panel
        radius: 3
        border.color: Tokens.line

        ColumnLayout {
            id: preferences
            anchors.fill: parent
            anchors.margins: 26
            spacing: 22

            HudLabel {
                text: 'Make it yours'
                font.pixelSize: 26
            }

            HudLabel {
                text: 'PRESENTATION'
                font.pixelSize: 11
                color: Tokens.gold
                font.letterSpacing: 2
            }

            ActionButton {
                text: Tokens.light ? 'Theme · Paper' : 'Theme · Night'
                Layout.fillWidth: true
                onClicked: Tokens.light = !Tokens.light
            }

            ActionButton {
                text: Tokens.reducedMotion ? 'Reduced motion · On' : 'Reduced motion · Off'
                Layout.fillWidth: true
                onClicked: Tokens.reducedMotion = !Tokens.reducedMotion
            }

            ActionButton {
            text: Tokens.warpSoundEnabled ? 'Warp sound · On' : 'Warp sound · Off'
            Layout.fillWidth: true
            enabled: Quickshell.env('HYPRUNE_WARP_SOUND')!==''
            onClicked: Tokens.warpSoundEnabled=!Tokens.warpSoundEnabled
        }
        HudLabel {
                text: 'MOVEMENT'
                font.pixelSize: 11
                color: Tokens.gold
                font.letterSpacing: 2
            }

            // Bound to core's movement mode both ways; core decides (and may refuse while climbing).
            Segmented {
                id: movementMode
                objectName: 'movementMode'
                readonly property string segment: Model.movementSegment(ShellState.state)
                Layout.fillWidth: true
                enabled: ShellState.available('movement.set')
                current: segment
                model: segment === 'climb'
                    ? [{id:'walk',label:'Walk'},{id:'climb',label:'Climbing',selectable:false},{id:'fly',label:'Fly'}]
                    : [{id:'walk',label:'Walk'},{id:'fly',label:'Fly'}]
                onPicked: (id) => ShellState.setMovement(Model.modeFor(id))
            }

            HudLabel {
                text: !ShellState.state ? 'Disconnected'
                    : ShellState.movementRefusal ? 'Core kept the current mode: ' + ShellState.movementRefusal
                    : !ShellState.available('movement.set') ? 'Movement mode changes are unavailable.'
                    : movementMode.segment === 'climb' ? 'Climbing. Walk or Fly asks core to end the climb.'
                    : movementMode.segment === '' ? 'Mode · ' + ShellState.state.movement.modeId
                    : movementMode.segment === 'fly' ? 'Free flight: Space rises, Ctrl descends.' : 'On foot: Space jumps, Shift runs.'
                font.pixelSize: 12
                color: ShellState.movementRefusal ? Tokens.warning : Tokens.muted
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }

            Item {
                Layout.fillHeight: true
            }

            HudLabel {
                text: ShellState.missing.length ? 'Partial core profile\n' + ShellState.missing.join(', ') : 'Interactive method profile available'
                color: Tokens.muted
                font.pixelSize: 12
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }

        }

    }

}

}
