import ".."
import "../theme"
import QtQuick

Item {
    id: root

    // Noninteractive layer: transparent input region is set by shell.qml.
    Reveal {
        x: 66
        y: 50
        width: 230
        height: 250
        shown: ShellState.active

        MapView {
            width: 200
            height: 200
            compact: true
            clip: true
            opacity: 0.85
        }

        HudLabel {
            x: 0
            y: 216
            text: ShellState.worldName.toUpperCase()
            font.pixelSize: 11
            font.letterSpacing: 2.2
            color: Tokens.accent
            width: 230
        }

    }

    Item {
        anchors.top: parent.top
        anchors.topMargin: 52
        anchors.horizontalCenter: parent.horizontalCenter
        width: 600
        height: 64
        clip: true

        Repeater {
            model: 25

            delegate: Item {
                required property int index

                x: (index - 12) * 48 + 300 - (ShellState.heading % 15) * 3.2
                width: 1
                height: 28

                Rectangle {
                    width: 1
                    height: index % 3 === 0 ? 12 : 5
                    color: Tokens.muted
                    opacity: 0.6
                    anchors.bottom: parent.bottom
                }

                HudLabel {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.bottom
                    anchors.topMargin: 10
                    text: {
                        var deg = (Math.floor(ShellState.heading / 15) * 15 + (index - 12) * 15 + 720) % 360;
                        return deg % 90 === 0 ? ['N', 'E', 'S', 'W'][deg / 90] : deg.toString();
                    }
                    font.pixelSize: 10
                    font.letterSpacing: 1
                    color: Tokens.muted
                }

            }

        }

        Rectangle {
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            width: 7
            height: 7
            rotation: 45
            color: Tokens.accent
        }

        HudLabel {
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.topMargin: 8
            text: Math.round(ShellState.heading) + '°'
            font.pixelSize: 11
            color: Tokens.accent
        }

    }

    Row {
        spacing: 18

        anchors {
            top: parent.top
            right: parent.right
            topMargin: 58
            rightMargin: 74
        }

        Column {
            spacing: 9

            HudLabel {
                text: ShellState.surfaces.some((s) => s.focused) ? 'APPLICATION INPUT' : 'NAVIGATION'
                font.pixelSize: 15
                font.letterSpacing: 4
                horizontalAlignment: Text.AlignRight
                width: 230
            }

            HudLabel {
                text: ShellState.surfaces.some((s) => s.focused) ? 'ESC · RETURN TO EXPLORATION' : 'WORLD RECEIVES INPUT'
                font.pixelSize: 10
                font.letterSpacing: 2
                color: Tokens.muted
                horizontalAlignment: Text.AlignRight
                width: 230
            }

        }

        Seal {
            width: 55
            height: 55
            variant: 1
        }

    }

    Reveal {
        x: 68
        y: 306
        width: 430
        height: 160
        shown: ShellState.active && ShellState.protocol !== '0.3'

        MissionPanel {
        }

    }

    Repeater {
        model: ShellState.markers

        delegate: Item {
            id: marker

            required property var modelData

            x: Math.max(4, Math.min(parent.width - 244, parent.width * modelData.x - 120))
            y: parent.height * modelData.y
            width: 240
            height: 80

            Rectangle {
                x: 45; y: 46; width: 150; height: 45
                color: '#ca0a111d'; radius: 2
            }
            Seal {
                width: 34
                height: 34
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Rectangle {
                x: 118
                y: 39
                width: 4
                height: 4
                color: Tokens.accent
                rotation: 45
            }

            HudLabel {
                anchors.top: parent.top
                anchors.topMargin: 51
                anchors.horizontalCenter: parent.horizontalCenter
                text: marker.modelData.name.toUpperCase()
                font.pixelSize: 11
                font.letterSpacing: 2.1
            }

            HudLabel {
                anchors.top: parent.top
                anchors.topMargin: 71
                anchors.horizontalCenter: parent.horizontalCenter
                text: Math.round(marker.modelData.distance) + ' m'
                font.pixelSize: 10
                color: Tokens.muted
                font.letterSpacing: 1.2
            }

        }

    }

    Reveal {
        x: 94
        y: parent.height - 360
        width: parent.width * 0.65
        height: 150
        shown: ShellState.zone !== ''
        travel: 24

        Rectangle { x: -18; y: -16; width: 550; height: 150; color: '#ce0a111d'; radius: 3 }
        Column {
            spacing: 17

            HudLabel {
                text: 'SECTOR DISCOVERED'
                font.pixelSize: 11
                font.letterSpacing: 4
                color: Tokens.muted
            }

            HudLabel {
                text: ShellState.zone.toUpperCase()
                font.pixelSize: 40
                font.weight: Font.Light
                font.letterSpacing: 6
            }

            HudLabel {
                text: ShellState.zoneSubtitle.toUpperCase()
                font.pixelSize: 13
                font.letterSpacing: 4
                color: Tokens.accent
            }

        }

    }

    Rectangle {
        x: 60; y: parent.height - 118; width: 610; height: 72
        color: '#cf0a111d'; radius: 3; visible: ShellState.active
    }
    Row {
        spacing: 20

        anchors {
            left: parent.left
            bottom: parent.bottom
            leftMargin: 76
            bottomMargin: 60
        }

        Seal {
            width: 32
            height: 32
            anchors.verticalCenter: parent.verticalCenter
            variant: 1
        }

        Column {
            spacing: 8

            HudLabel {
                text: ShellState.state ? (ShellState.state.interaction ? ShellState.state.interaction.mode.toUpperCase() + '  /  ' + (ShellState.state.interaction.noclip ? 'NOCLIP  /  ' : '') : '') + ShellState.state.movement.modeId.split('.').pop().toUpperCase() + '  /  ' + ShellState.pose.map((v) => {
                    return v.toFixed(1);
                }).join(' · ') + ' m' : ''
                font.pixelSize: 11
                font.letterSpacing: 1.3
                color: Tokens.accent
            }

            HudLabel {
                visible: !!(ShellState.state && ShellState.state.interaction)
                text: ShellState.state && ShellState.state.interaction ? ShellState.state.interaction.tools.map((name, i) => (ShellState.state.interaction.tool === i + 1 ? '▸ ' : '') + (i + 1) + ' ' + name.toUpperCase()).join('    ') : ''
                color: Tokens.accent
                font.pixelSize: 11
            }

            HudLabel {
                text: ShellState.protocol !== '0.1' ? 'HOLD TAB  ·  OVERVIEW     /     F12  ·  RETURN TO DESKTOP' : 'OVERVIEW  ·  CORE BINDING     /     DESKTOP ESCAPE  ·  CORE BINDING'
                font.pixelSize: 10
                color: Tokens.muted
                font.letterSpacing: 1
            }

        }

    }

    VehiclePanel {
        anchors {
            right: parent.right
            bottom: parent.bottom
            rightMargin: 76
            bottomMargin: 60
        }

    }

    Column {
        width: 430
        spacing: 15

        anchors {
            right: parent.right
            bottom: parent.bottom
            rightMargin: 76
            bottomMargin: ShellState.dev && ShellState.presentation.vehicle && ShellState.presentation.vehicle.active ? 240 : 90
        }

        Repeater {
            model: ShellState.notices

            delegate: Item {
                required property var modelData

                width: 430
                height: Math.max(45, message.implicitHeight + 16)

                Rectangle {
                    width: 1
                    height: parent.height
                    color: modelData.level === 'info' ? Tokens.accent : Tokens.gold
                    opacity: 0.65
                }

                HudLabel {
                    id: message

                    text: modelData.message
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                    lineHeight: 1.4
                    color: Tokens.muted

                    anchors {
                        left: parent.left
                        right: parent.right
                        verticalCenter: parent.verticalCenter
                        leftMargin: 18
                    }

                }

            }

        }

    }

    HudLabel {
        text: ShellState.presentation.dev ? 'HYPRUNE  /  M0 PREVIEW' : 'HYPRUNE  /  LIVE SESSION'
        font.pixelSize: 9
        font.letterSpacing: 3
        color: Tokens.muted

        anchors {
            horizontalCenter: parent.horizontalCenter
            bottom: parent.bottom
            bottomMargin: 38
        }

    }

}
