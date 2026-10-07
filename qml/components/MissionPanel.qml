import ".."
import "../theme"
import QtQuick

Item {
    width: 430
    height: 160

    Rectangle {
        width: parent.width
        height: 38
        color: Tokens.mission
        opacity: 0.55
    }

    Seal {
        x: 8
        y: -4
        width: 44
        height: 44
        tint: Tokens.accent
        variant: 1
    }

    HudLabel {
        x: 65
        y: 12
        text: 'ESTABLISH YOUR SPACE'
        font.pixelSize: 13
        font.letterSpacing: 2.8
        font.weight: Font.DemiBold
    }

    Rectangle {
        x: 65
        y: 38
        width: parent.width - 65
        height: 1
        color: Tokens.accent
        opacity: 0.6
    }

    Column {
        x: 30
        y: 58
        spacing: 15

        Repeater {
            model: [['Explore your surroundings', ShellState.live], ['Mark a destination', !!ShellState.waypointState], ['Find a workspace', ShellState.workspaces.some((s) => {
                return s.focused;
            })]]

            delegate: Row {
                required property var modelData

                spacing: 22

                Rectangle {
                    width: 11
                    height: 11
                    color: modelData[1] ? Tokens.accent : 'transparent'
                    border.color: Tokens.accent
                    rotation: 45
                    anchors.verticalCenter: parent.verticalCenter
                }

                HudLabel {
                    text: modelData[0]
                    font.pixelSize: 13
                    color: modelData[1] ? Tokens.muted : Tokens.text
                    font.letterSpacing: 0.5
                }

            }

        }

    }

}
