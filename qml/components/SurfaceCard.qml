import ".."
import "../theme"
import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root

    property var surface

    implicitHeight: cardColumn.implicitHeight + 40
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
        id: cardColumn
        anchors.fill: parent
        anchors.margins: 20
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
            Layout.fillWidth: true
            text: root.surface.kind === 'workspace' ? (root.surface.desktop ? 'Native desktop workspace' : (ShellState.worlds.find(w => w.id === root.surface.worldId)?.name || 'World workspace')) : root.surface.logicalSize.join(' × ') + '  /  logical pixels'
            font.family: Tokens.mono
            font.pixelSize: 11
            color: Tokens.muted
        }

        Item {
            Layout.fillHeight: true
        }

        RowLayout {
            visible: root.surface.kind === 'window' && ShellState.available('surface.pull')
            Layout.fillWidth: true
            ActionButton {
                Layout.fillWidth: true; Layout.minimumWidth: 0; Layout.preferredWidth: 1
                text: 'Pull out'
                onClicked: ShellState.action('surface.pull', {surfaceId:root.surface.id})
            }
            ActionButton {
                Layout.fillWidth: true; Layout.minimumWidth: 0; Layout.preferredWidth: 1
                text: 'Place at home'
                onClicked: ShellState.action('surface.place', {surfaceId:root.surface.id})
            }
            ActionButton {
                Layout.fillWidth: true; Layout.minimumWidth: 0; Layout.preferredWidth: 1
                text: 'Return'
                onClicked: ShellState.action('surface.return', {surfaceId:root.surface.id})
            }
        }

        ActionButton {
            text: root.surface.kind === 'workspace' ? (root.surface.desktop ? 'Open desktop ↗' : 'Enter location ↗') : 'Request keyboard focus ↗'
            Layout.fillWidth: true
            enabled: ShellState.available(root.surface.kind === 'workspace' && !root.surface.desktop ? 'workspace.activate' : 'surface.focus')
            onClicked: root.surface.kind === 'workspace' && !root.surface.desktop ? ShellState.action('workspace.activate',{id:root.surface.id}) : ShellState.action('surface.focus', {
                "surfaceId": root.surface.surfaceId || root.surface.id,
                "intent": 'keyboard'
            })
        }

    }

}
