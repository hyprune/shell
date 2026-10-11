import ".."
import "../theme"
import QtQuick
import QtQuick.Layouts
import Quickshell

Rectangle {
    id: root

    objectName: "surfaceCard"
    property var apps: []
    property var surface
    // IPC 0.20: in the pocket (editor.unplaced) = not drawn in the world.
    readonly property bool pocketed: surface.pocketed === true
    readonly property bool canPocket: surface.kind === 'window' && ShellState.available(pocketed ? 'surface.unpocket' : 'surface.pocket')
    readonly property var feedback: ShellState.surfaceFeedback && ShellState.surfaceFeedback.surfaceId === surface.id ? ShellState.surfaceFeedback : null

    implicitHeight: cardColumn.implicitHeight + 40
    radius: 3
    color: pocketed ? Tokens.ink : Tokens.panel
    border.color: hover.containsMouse || surface.focused ? Tokens.accent : pocketed ? Tokens.gold : Tokens.line

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
                visible: !root.pocketed
                text: root.surface.focused ? '● FOCUSED' : '○ AVAILABLE'
                font.pixelSize: 10
                color: Tokens.accent
            }

            Rectangle {
                visible: root.pocketed
                objectName: 'pocketBadge:' + root.surface.id
                implicitWidth: pocketBadge.implicitWidth + 16
                implicitHeight: pocketBadge.implicitHeight + 8
                radius: 2
                color: Tokens.gold
                HudLabel {
                    id: pocketBadge
                    anchors.centerIn: parent
                    text: 'IN POCKET'
                    font.family: Tokens.mono
                    font.pixelSize: 10
                    font.letterSpacing: 1.5
                    color: Tokens.ink
                }
            }

        }

        HudLabel {
            text: root.surface.title || 'Untitled surface'
            font.pixelSize: 22
            Layout.fillWidth: true
            elide: Text.ElideRight
            color: root.pocketed ? Tokens.muted : Tokens.text
        }

        HudLabel {
            visible: root.pocketed
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: 'Not placed in the world. Take it out to place it.'
            font.pixelSize: 13
            color: Tokens.muted
        }

        HudLabel {
            Layout.fillWidth: true
            text: root.surface.kind === 'workspace' ? (root.surface.desktop ? 'Native desktop workspace' : (ShellState.worlds.find(w => w.id === root.surface.worldId)?.name || 'World workspace')) : root.surface.logicalSize.join(' × ') + '  /  logical pixels' + (root.surface.appClass ? '  /  ' + root.surface.appClass : '')
            elide: Text.ElideRight
            font.family: Tokens.mono
            font.pixelSize: 11
            color: Tokens.muted
        }

        ColumnLayout {
            visible: root.apps.length > 0
            Layout.fillWidth: true
            spacing: 10
            Rectangle { Layout.fillWidth: true; height: 1; color: Tokens.line }
            Repeater {
                model: root.apps
                RowLayout {
                    required property var modelData
                    objectName: 'workspaceApp'
                    Layout.fillWidth: true
                    spacing: 10
                    Image { Layout.preferredWidth: 24; Layout.preferredHeight: 24; source: Quickshell.iconPath(modelData.icon, 'application-x-executable'); fillMode: Image.PreserveAspectFit }
                    ColumnLayout {
                        Layout.fillWidth: true; Layout.minimumWidth: 0; spacing: 3
                        HudLabel { Layout.fillWidth: true; text: modelData.title; elide: Text.ElideRight }
                        HudLabel { Layout.fillWidth: true; text: modelData.appClass; color: Tokens.muted; font.pixelSize: 10; elide: Text.ElideRight }
                    }
                }
            }
        }

        Item {
            Layout.fillHeight: true
        }

        HudLabel {
            visible: root.feedback !== null
            objectName: 'pocketFeedback:' + root.surface.id
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: root.feedback ? root.feedback.text : ''
            font.pixelSize: 13
            color: root.feedback && root.feedback.level === 'warning' ? Tokens.warning : Tokens.positive
        }

        ActionButton {
            visible: root.pocketed && root.canPocket
            objectName: 'unpocketButton:' + root.surface.id
            Layout.fillWidth: true
            primary: true
            text: 'Take out / place ↗'
            onClicked: ShellState.pocket(root.surface.id, false)
        }

        RowLayout {
            visible: root.surface.kind === 'window' && !root.pocketed && ShellState.available('surface.pull')
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
            visible: !root.pocketed && root.canPocket
            objectName: 'pocketButton:' + root.surface.id
            Layout.fillWidth: true
            text: 'Put in pocket'
            onClicked: ShellState.pocket(root.surface.id, true)
        }

        ActionButton {
            visible: !root.pocketed
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
