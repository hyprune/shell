import ".."
import "../theme"
import QtQuick

Item {
    id: root

    property var destination
    property int variant: 0
    property bool selected: false

    signal chosen()

    width: 380
    height: 410

    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 12
        width: 194
        height: 194
        radius: 97
        color: Tokens.raised
        opacity: hover.containsMouse ? 0.7 : 0.28

        Behavior on opacity {
            NumberAnimation {
                duration: Tokens.motion
            }

        }

    }

    Seal {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 9
        width: 200
        height: 200
        variant: root.variant
        tint: root.selected ? Tokens.text : Tokens.muted
        scale: hover.containsMouse ? 1.04 : 1

        Behavior on scale {
            NumberAnimation {
                duration: Tokens.motion * 2
                easing.type: Easing.OutCubic
            }

        }

    }

    HudLabel {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 235
        text: root.destination.name.toUpperCase()
        font.pixelSize: 22
        font.weight: Font.Light
        font.letterSpacing: 4
    }

    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 278
        width: root.selected ? 150 : 44
        height: 1
        color: Tokens.accent

        Behavior on width {
            NumberAnimation {
                duration: Tokens.motion * 2
            }

        }

    }

    HudLabel {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 300
        width: 340
        text: root.destination.description || 'An explorable desktop world.'
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
        lineHeight: 1.6
        font.pixelSize: 13
        color: Tokens.muted
    }

    MouseArea {
        id: hover

        anchors.fill: parent
        hoverEnabled: true
        onClicked: root.chosen()
        onDoubleClicked: ShellState.action('world.load', {
            "worldId": root.destination.id
        })
    }

    ActionButton {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 367
        width: 230
        text: 'Travel to destination ↗'
        primary: root.selected
        enabled: ShellState.available('world.load')
        onClicked: ShellState.action('world.load', {
            "worldId": root.destination.id
        })
    }

}
