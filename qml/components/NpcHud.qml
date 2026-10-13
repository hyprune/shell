import QtQuick
import ".."
import "../theme"
import "../Npcs.js" as Npcs

// IPC 0.23 character prompts on the HUD (passive: no input region). Under the reticle: the
// aimed character's prompt ("E  Talk", or "E  Talk to <name>" with several interactions), with
// a short note when characters stand still under the user's settings (Npcs.pauseNote).
// Bottom centre: the caption of a running say interaction (core also draws a world-locked
// caption; this one stays compact, subtitle style) and, while a route is being drawn
// (npcs.drawing), the drawing hint. Follows the HUD concept and world style; reduced motion
// shows and hides instantly.
Item {
    id: root
    objectName: 'hudNpc'
    property real leftLimit: 0             // right edge of the tool deck: captions start after it
    property real inset: 56
    readonly property bool technical: Tokens.hudConcept === 'Instrument'
    readonly property bool minimal: Tokens.hudConcept === 'Minimal'
    readonly property var npcs: ShellState.npcsState
    readonly property var interaction: npcs ? npcs.interaction : null
    readonly property var prompt: !interaction && !ShellState.npcChoice ? Npcs.aimedPrompt(npcs ? npcs.aimed : null, npcs) : null
    readonly property var caption: Npcs.caption(interaction, interaction ? ShellState.characterName(interaction.objectId) : '')
    readonly property var drawing: ShellState.drawingHint
    readonly property color tileColor: minimal ? '#c013242d' : Qt.rgba(Tokens.hudScrim.r, Tokens.hudScrim.g, Tokens.hudScrim.b, .86)
    readonly property string font: technical ? Tokens.mono : Tokens.hudFont

    // ---- Aimed prompt, just under the reticle ----
    Item {
        id: promptBox
        objectName: 'hudNpcPrompt'
        readonly property var shown: root.prompt
        anchors.horizontalCenter: parent.horizontalCenter
        y: Math.round(root.height / 2 + 44)
        width: Math.min(root.width - 40, keyCap.width + Math.max(promptText.implicitWidth, promptNote.implicitWidth) + 40)
        height: promptNote.text ? 56 : 40
        opacity: shown ? 1 : 0
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: Tokens.reducedMotion ? 0 : 140 } }
        property var last: null
        onShownChanged: { if (shown) last = shown; }
        HudTile { anchors.fill: parent; color: root.tileColor; borderColor: root.technical ? Tokens.hudAccent : 'transparent'; borderWidth: root.technical ? 1 : 0 }
        Rectangle {
            id: keyCap
            x: 8; anchors.verticalCenter: parent.verticalCenter
            width: 26; height: 26; radius: root.minimal ? 2 : 4
            color: 'transparent'
            border.width: 1.5; border.color: Tokens.hudAccent
            HudText { anchors.centerIn: parent; text: promptBox.last ? promptBox.last.key : Npcs.INTERACT_KEY; font.pixelSize: 13; font.family: root.font; color: Tokens.hudAccent }
        }
        HudText {
            id: promptText
            objectName: 'hudNpcPromptText'
            x: keyCap.x + keyCap.width + 12
            width: parent.width - x - 14
            y: promptNote.text ? 6 : Math.round((parent.height - height) / 2)
            text: promptBox.last ? promptBox.last.text : ''
            font.pixelSize: 15; font.family: root.font
            elide: Text.ElideRight
        }
        // Why it stands still (posed still, reduced motion) and where that is set.
        HudText {
            id: promptNote
            objectName: 'hudNpcPromptNote'
            x: promptText.x
            width: promptText.width
            y: parent.height - height - 7
            visible: text !== ''
            text: promptBox.last && promptBox.last.note ? promptBox.last.note : ''
            font.pixelSize: 12; font.family: root.font
            color: Tokens.gold
            elide: Text.ElideRight
        }
    }

    // ---- Bottom centre: drawing hint over the caption ----
    // Centred under the world view, moved right (and narrowed) where it would meet the tool deck.
    Column {
        id: bottom
        readonly property real wanted: Math.min(680, root.width * .46)
        x: Math.max((root.width - wanted) / 2, root.leftLimit)
        width: Math.max(240, Math.min(wanted, root.width - root.inset - x))
        spacing: 10
        y: Math.min(root.height * .82, root.height - root.inset - 56) - height

        Item {
            id: drawBox
            objectName: 'hudNpcDrawing'
            width: parent.width
            height: drawColumn.implicitHeight + 18
            opacity: root.drawing ? 1 : 0
            visible: opacity > 0
            Behavior on opacity { NumberAnimation { duration: Tokens.reducedMotion ? 0 : 160 } }
            property var last: null
            Connections { target: root; function onDrawingChanged() { if (root.drawing) drawBox.last = root.drawing; } }
            Component.onCompleted: last = root.drawing
            HudTile { anchors.fill: parent; color: root.tileColor; borderColor: Tokens.hudAccent; borderWidth: root.technical ? 1 : 0 }
            Rectangle { width: root.minimal ? 2 : 4; height: parent.height; color: Tokens.hudAccent }
            Column {
                id: drawColumn
                x: 16; y: 9; width: parent.width - 30
                spacing: 3
                HudText {
                    width: parent.width
                    text: drawBox.last ? ('✎  ' + drawBox.last.title).toUpperCase() : ''
                    font.pixelSize: 11; font.letterSpacing: 1.6; font.family: root.font
                    color: Tokens.hudAccent
                }
                HudText {
                    objectName: 'hudNpcDrawingText'
                    width: parent.width
                    text: drawBox.last ? drawBox.last.line : ''
                    font.pixelSize: 13; wrapMode: Text.Wrap; maximumLineCount: 2
                }
                HudText {
                    width: parent.width
                    visible: text !== ''
                    text: drawBox.last ? drawBox.last.detail : ''
                    font.pixelSize: 12; color: Tokens.hudMuted; wrapMode: Text.Wrap; maximumLineCount: 2
                }
            }
        }

        Item {
            id: captionBox
            objectName: 'hudNpcCaption'
            width: parent.width
            height: captionColumn.implicitHeight + 22
            opacity: root.caption ? 1 : 0
            visible: opacity > 0
            Behavior on opacity { NumberAnimation { duration: Tokens.reducedMotion ? 0 : 160 } }
            property var last: null
            Connections { target: root; function onCaptionChanged() { if (root.caption) captionBox.last = root.caption; } }
            Component.onCompleted: last = root.caption
            HudTile { anchors.fill: parent; color: root.tileColor; borderColor: root.technical ? Tokens.hudAccent : 'transparent'; borderWidth: root.technical ? 1 : 0 }
            Column {
                id: captionColumn
                x: 18; y: 11; width: parent.width - 36
                spacing: 5
                Item {
                    width: parent.width
                    height: speaker.implicitHeight
                    HudText {
                        id: speaker
                        objectName: 'hudNpcSpeaker'
                        width: parent.width - hint.implicitWidth - 16
                        text: captionBox.last ? captionBox.last.speaker.toUpperCase() + (captionBox.last.progress ? '   ' + captionBox.last.progress : '') : ''
                        font.pixelSize: 11; font.letterSpacing: 1.6; font.family: root.font
                        color: Tokens.hudAccent; elide: Text.ElideRight
                    }
                    HudText {
                        id: hint
                        objectName: 'hudNpcCaptionHint'
                        anchors.right: parent.right
                        text: captionBox.last ? captionBox.last.hint : ''
                        font.pixelSize: 11; font.family: Tokens.mono
                        color: Tokens.hudMuted
                    }
                }
                HudText {
                    objectName: 'hudNpcLine'
                    width: parent.width
                    text: captionBox.last ? captionBox.last.line : ''
                    font.pixelSize: 17; font.family: root.technical ? Tokens.sans : Tokens.hudFont
                    smallText: false
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.Wrap; maximumLineCount: 3
                }
            }
        }
    }
}
