import QtQuick
import QtQuick.Controls
import "../theme"

ComboBox {
    id: root
    implicitHeight: 40
    implicitWidth: 220
    leftPadding: 12; rightPadding: 32
    font.family: Tokens.sans
    font.pixelSize: 13
    contentItem: HudLabel { text: root.displayText; verticalAlignment: Text.AlignVCenter; font.pixelSize: 13; color: root.enabled ? Tokens.text : Tokens.muted }
    indicator: HudLabel { x: root.width - 25; anchors.verticalCenter: parent.verticalCenter; text: '⌄'; color: Tokens.muted }
    background: Rectangle { radius: Tokens.radius; color: Tokens.panel; border.color: root.activeFocus ? Tokens.gold : root.hovered ? Tokens.accent : Tokens.line }
    delegate: ItemDelegate {
        required property var modelData
        required property int index
        width: root.width
        highlighted: root.highlightedIndex === index
        contentItem: HudLabel { text: modelData; font.pixelSize: 13 }
        background: Rectangle { color: parent.highlighted ? Tokens.raised : Tokens.panel }
    }
    popup: Popup {
        y: root.height + 4
        width: root.width
        implicitHeight: Math.min(contentItem.implicitHeight + 12, 300)
        padding: 6
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: root.popup.visible ? root.delegateModel : null
            currentIndex: root.highlightedIndex
            ScrollIndicator.vertical: ScrollIndicator {}
        }
        background: Rectangle { color: Tokens.panel; border.color: Tokens.line; radius: Tokens.radius }
    }
    ToolTip.visible: hovered && contentItem.truncated
    ToolTip.text: displayText
    ToolTip.delay: 500
}
