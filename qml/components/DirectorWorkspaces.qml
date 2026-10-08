import ".."
import "../theme"
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Flickable {
    clip: true
    ScrollBar.vertical: ScrollBar {}
    boundsBehavior: Flickable.StopAtBounds
    contentWidth: width
    contentHeight: workspaceColumn.height

    Column {
        id: workspaceColumn

        width: parent.width
        spacing: 24

        HudLabel {
            width: parent.width
            wrapMode: Text.Wrap
            text: 'Make room for a different kind of work'
            font.pixelSize: 30
            font.weight: Font.Light
        }

        HudLabel {
            width: parent.width
            wrapMode: Text.Wrap
            text: 'Your real desktops and apps, with world locations where configured.'
            color: Tokens.muted
            font.pixelSize: 14
        }

        GridLayout {
            width: parent.width
            columns: Math.max(1, Math.floor((width + 20) / 390))
            columnSpacing: 20
            rowSpacing: 20

            Repeater {
                model: ShellState.workspaces

                delegate: SurfaceCard {
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    Layout.preferredWidth: 1
                    Layout.alignment: Qt.AlignTop
                    surface: modelData
                    apps: ShellState.state && ShellState.state.apps ? ShellState.state.apps.filter(app => app.workspaceId === modelData.id) : []
                }

            }

        }

        HudLabel {
            visible: !ShellState.workspaces.length
            text: 'No workspaces are currently available.'
            color: Tokens.muted
        }

    }

}
