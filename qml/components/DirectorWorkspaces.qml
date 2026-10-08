import ".."
import "../theme"
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell

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

                delegate: Column {
                    required property var modelData

                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    Layout.preferredWidth: 1
                    Layout.alignment: Qt.AlignTop
                    spacing: 10
                    SurfaceCard { width: parent.width; surface: parent.modelData }
                    Repeater {
                        model: ShellState.state && ShellState.state.apps ? ShellState.state.apps.filter((app) => app.workspaceId === modelData.id) : []
                        delegate: Row {
                            required property var modelData
                            width: parent.width
                            spacing: 10
                            Image { width: 24; height: 24; source: Quickshell.iconPath(modelData.icon, "application-x-executable"); fillMode: Image.PreserveAspectFit }
                            Column {
                                width: parent.width - 34
                                HudLabel { width: parent.width; text: modelData.title; elide: Text.ElideRight }
                                HudLabel { width: parent.width; text: modelData.appClass; color: Tokens.muted; font.pixelSize: 10; elide: Text.ElideRight }
                            }
                        }
                    }
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
