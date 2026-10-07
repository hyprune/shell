import ".."
import "../theme"
import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root

    property var surface

    implicitHeight: 220
    radius: 3
    color: Tokens.panel
    border.color: hover.containsMouse || surface.focused ? Tokens.accent : Tokens.line

    MouseArea {
        id: hover

        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 16

        RowLayout {
            Layout.fillWidth: true

            HudLabel {
                text: root.surface.kind.toUpperCase()
                font.family: Tokens.mono
                font.pixelSize: 11
                color: Tokens.gold
            }

            Item {
                Layout.fillWidth: true
            }

            HudLabel {
                text: root.surface.focused ? '● FOCUSED' : '○ AVAILABLE'
                font.pixelSize: 10
                color: Tokens.accent
            }

        }

        HudLabel {
            text: root.surface.title || 'Untitled surface'
            font.pixelSize: 22
            Layout.fillWidth: true
        }

        HudLabel {
            text: root.surface.kind === 'workspace' ? root.surface.worldId : root.surface.logicalSize.join(' × ') + '  /  logical pixels'
            font.family: Tokens.mono
            font.pixelSize: 11
            color: Tokens.muted
        }

        Item {
            Layout.fillHeight: true
        }

        ActionButton {
            text: root.surface.kind === 'workspace' ? 'Enter location ↗' : 'Request keyboard focus ↗'
            Layout.fillWidth: true
            enabled: ShellState.available(root.surface.kind === 'workspace' ? 'workspace.activate' : 'surface.focus')
            onClicked: root.surface.kind === 'workspace' ? ShellState.action('workspace.activate',{id:root.surface.id}) : ShellState.action('surface.focus', {
                "surfaceId": root.surface.id,
                "intent": 'keyboard'
            })
        }

    }

}
