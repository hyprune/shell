import Quickshell
import ".."
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
            model: ['0.6','0.7'].indexOf(ShellState.protocol) >= 0 ? [['MOVEMENT','HJKL / WASD / arrows; Shift boosts, Space jumps/up, Ctrl crouches/down.'],['USE / FOCUS','E uses a window or workspace in place. F zooms to fullscreen. Super+Tab or Back returns.'],['MAP / SETTINGS','Hold Tab to open Map. Settings captures up to three bindings per action, with conflict feedback.'],['TOOLS','1 normal, 2 window place/lock, 3 path, 4 position move/rotate/scale; wheel changes submode.'],['SCOPE / DEBUG','Hold Q and wheel to zoom; F3/Y toggles debug; U saves a state capture.']] : [['OVERVIEW', 'Core owns the hold-to-open binding and timing.'], ['ESCAPE', 'Return to desktop restores ordinary input through core.'], ['MAP', 'Select a spawn to inspect it. Arrive reloads at that spawn.'], ['SURFACES', 'Focus is a request. Hidden-workspace focus may be refused.'], ['KEYBOARD', 'Tab moves focus. Left / Right change view. Esc closes.']]

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

            HudLabel {
                text: ShellState.state ? ShellState.state.movement.modeId : 'Disconnected'
                font.family: Tokens.mono
                font.pixelSize: 11
                color: Tokens.muted
                Layout.fillWidth: true
            }

            ActionButton {
                text: 'Use free flight'
                Layout.fillWidth: true
                enabled: ShellState.available('movement.set')
                onClicked: ShellState.action('movement.set', {
                    "modeId": 'com.hyprune.fly'
                })
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
