import ".."
import "../theme"
import QtQuick

Item {
    id: root

    property int selected: 0

    Constellation {
        anchors.fill: parent
        planet: true
        opacity: 0.7
    }

    HudLabel {
        x: 28
        y: 22
        text: 'DESTINATIONS'
        font.pixelSize: 30
        font.weight: Font.Light
        font.letterSpacing: 6
    }

    HudLabel {
        x: 30
        y: 72
        text: 'CHOOSE YOUR NEXT HORIZON'
        font.pixelSize: 11
        font.letterSpacing: 4
        color: Tokens.muted
    }

    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        spacing: 100

        Repeater {
            model: ShellState.worlds

            delegate: DestinationCard {
                required property var modelData
                required property int index

                destination: modelData
                variant: index
                selected: root.selected === index
                onChosen: root.selected = index
            }

        }

    }

    HudLabel {
        text: 'LMB  SELECT    /    DOUBLE CLICK  TRAVEL'
        font.pixelSize: 10
        font.letterSpacing: 2
        color: Tokens.muted

        anchors {
            bottom: parent.bottom
            left: parent.left
            margins: 28
        }

    }

}
