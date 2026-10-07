import ".."
import "../theme"
import QtQuick

Item {
    id: root

    property var vehicle: ShellState.presentation.vehicle || ({
        "active": false
    })

    width: 350
    height: 150
    visible: ShellState.dev && vehicle.active === true

    Seal {
        x: 0
        y: 15
        width: 75
        height: 75
        variant: 1
        tint: Tokens.accent
    }

    HudLabel {
        x: 100
        y: 0
        text: (root.vehicle.name || 'FLIGHT').toUpperCase()
        font.pixelSize: 12
        font.letterSpacing: 4
        color: Tokens.muted
    }

    HudLabel {
        x: 96
        y: 18
        text: Math.round(root.vehicle.speed || 0)
        font.pixelSize: 54
        font.weight: Font.Light
        font.letterSpacing: 3
    }

    HudLabel {
        x: 210
        y: 51
        text: 'm / s'
        font.pixelSize: 12
        font.letterSpacing: 2
        color: Tokens.muted
    }

    Rectangle {
        x: 100
        y: 91
        width: 220
        height: 2
        color: Tokens.line

        Rectangle {
            width: parent.width * (root.vehicle.charge || 0)
            height: 2
            color: Tokens.accent
        }

    }

    HudLabel {
        x: 100
        y: 110
        text: 'VEHICLE PREVIEW'
        font.pixelSize: 9
        font.letterSpacing: 3
        color: Tokens.muted
    }

}
