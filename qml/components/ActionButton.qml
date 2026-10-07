import "../theme"
import QtQuick
import QtQuick.Controls

Button {
    id: root

    property bool primary: false

    implicitHeight: 42
    implicitWidth: Math.max(120, contentItem.implicitWidth + 32)
    focusPolicy: Qt.StrongFocus

    contentItem: HudLabel {
        text: root.text
        color: root.enabled ? (root.primary ? Tokens.ink : Tokens.text) : Tokens.muted
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.pixelSize: 13
    }

    background: Rectangle {
        radius: 3
        color: root.enabled ? (root.primary ? Tokens.accent : (root.hovered ? Tokens.raised : Tokens.panel)) : 'transparent'
        border.width: root.activeFocus ? 2 : 1
        border.color: root.activeFocus ? Tokens.gold : (root.primary && root.enabled ? Tokens.accent : Tokens.line)
        opacity: root.enabled ? 1 : 0.55
    }

}
