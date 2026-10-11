import QtQuick
import ".."
import "../theme"

// One RFC-0012 notification: a small toast under the tracker, or (banner: true) the
// top-centre quest-completed banner. Shows the head of its queue; reduced motion is instant.
Item {
    id: root
    property var toast: null
    property bool banner: false
    readonly property bool technical: Tokens.hudConcept === 'Instrument'
    readonly property bool minimal: Tokens.hudConcept === 'Minimal'
    readonly property color tone: !shown || shown.category !== 'focus' ? Tokens.hudQuest : shown.phase === 'break' ? Tokens.hudBreak : Tokens.hudAccent
    implicitHeight: column.implicitHeight + (banner ? 28 : 20)
    opacity: toast ? 1 : 0
    visible: opacity > 0
    Behavior on opacity { NumberAnimation { duration: Tokens.reducedMotion ? 0 : 200 } }
    // Keep the last text while fading out.
    property var shown: null
    onToastChanged: { if (toast) shown = toast; }

    HudTile {
        anchors.fill: parent
        color: root.minimal ? '#c013242d' : Qt.rgba(Tokens.hudScrim.r, Tokens.hudScrim.g, Tokens.hudScrim.b, .86)
        borderColor: root.banner || root.technical ? root.tone : 'transparent'
        borderWidth: root.banner || root.technical ? 1 : 0
    }
    Rectangle {
        visible: !root.banner
        anchors.right: parent.right; width: root.minimal ? 2 : 4; height: parent.height; color: root.tone
    }
    Rectangle { visible: root.banner; anchors.horizontalCenter: parent.horizontalCenter; y: -3; width: 80; height: 2; color: root.tone }
    Column {
        id: column
        x: root.banner ? 18 : 12; y: root.banner ? 14 : 10
        width: parent.width - (root.banner ? 36 : 26)
        spacing: 4
        HudText {
            width: parent.width
            horizontalAlignment: root.banner ? Text.AlignHCenter : Text.AlignLeft
            text: root.shown ? (root.banner ? root.shown.line : root.shown.title).toUpperCase() + (root.shown.count > 1 ? '  ×' + root.shown.count : '') : ''
            font.pixelSize: root.banner ? 11 : 10; font.letterSpacing: 1.6
            color: root.tone
        }
        HudText {
            objectName: root.banner ? 'hudQuestBannerTitle' : 'hudToastLine'
            width: parent.width
            horizontalAlignment: root.banner ? Text.AlignHCenter : Text.AlignLeft
            text: root.shown ? (root.banner ? root.shown.title : root.shown.line) : ''
            font.pixelSize: root.banner ? 20 : 14
            smallText: !root.banner
            maximumLineCount: 2; wrapMode: Text.Wrap
        }
        HudText {
            width: parent.width
            visible: text !== ''
            horizontalAlignment: root.banner ? Text.AlignHCenter : Text.AlignLeft
            text: root.shown ? root.shown.detail || '' : ''
            font.pixelSize: 12
            color: Tokens.hudMuted
            maximumLineCount: 2; wrapMode: Text.Wrap
        }
    }
}
