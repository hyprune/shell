import QtQuick
import QtQuick.Controls
import "../theme"

Slider {
    id: root
    implicitHeight: 36
    // Settings that reconfigure the renderer (target FPS, power cap, scale): settled once,
    // on release or settleMs after the last key step, instead of on every step of a drag.
    // target: the value from state; it is not pushed into the handle while it is dragged or
    // settling (a state poll mid-drag used to snap the handle back).
    signal settled(real value)
    property int settleMs: 300
    property var target: undefined
    readonly property bool settling: pressed || settle.running
    Binding on value { value: Number(root.target); when: root.target !== undefined && !root.settling }
    property bool unsettled: false // moved since the last settled()
    function settle_() { settle.stop(); if (unsettled) { unsettled = false; settled(value); } }
    Timer { id: settle; interval: root.settleMs; onTriggered: if (!root.pressed) root.settle_() }
    onMoved: { unsettled = true; settle.restart(); }
    onPressedChanged: if (!pressed) settle_()
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
