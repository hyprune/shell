import QtQuick
import QtQuick.Controls
import "../theme"

Slider {
    id: root
    implicitHeight: 36
    background: Rectangle {
        x: root.leftPadding; y: root.topPadding + root.availableHeight / 2 - height / 2
        width: root.availableWidth; height: 3; radius: 1.5; color: Tokens.line
        Rectangle { width: root.visualPosition * parent.width; height: parent.height; color: root.enabled ? Tokens.accent : Tokens.muted }
    }
    handle: Rectangle {
        x: root.leftPadding + root.visualPosition * (root.availableWidth - width)
        y: root.topPadding + root.availableHeight / 2 - height / 2
        width: 16; height: 16; radius: 8
        color: root.enabled ? Tokens.accent : Tokens.muted
        border.color: root.activeFocus ? Tokens.gold : Tokens.panel
        border.width: 2
    }
}
