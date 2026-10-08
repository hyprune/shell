import ".."
import "../theme"
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell

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

                delegate: Column {
                    required property var modelData

                    Layout.fillWidth: true
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
            text: 'Core has not advertised any workspace surfaces.'
            color: Tokens.muted
        }

    }

}
