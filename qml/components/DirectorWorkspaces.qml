import ".."
import "../theme"
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Flickable {
    clip: true
    contentHeight: workspaceColumn.height

    Column {
        id: workspaceColumn

        width: parent.width
        spacing: 24

        HudLabel {
            text: 'Make room for a different kind of work'
            font.pixelSize: 30
            font.weight: Font.Light
        }

        HudLabel {
            text: 'Core-owned workspace locations. Switching workspace opens its world through the same warp lifecycle.'
            color: Tokens.muted
            font.pixelSize: 14
        }

        GridLayout {
            width: parent.width
            columns: 3
            columnSpacing: 20
            rowSpacing: 20

            Repeater {
                model: ShellState.workspaces

                delegate: SurfaceCard {
                    required property var modelData

                    surface: modelData
                    Layout.fillWidth: true
                }

            }

        }

        HudLabel {
            visible: !ShellState.workspaces.length
            text: 'Core has not advertised any workspace surfaces.'
            color: Tokens.muted
        }

    }

}
