import QtQuick
import QtQuick.Layouts
import ".."
import "../theme"
import "../Assistants.js" as Assistants

// RFC-0016 pairing: an assistant (an MCP client running `hyprune mcp`) asks to build. Shown at
// the top of the Director while the request waits: Allow once, Always allow or Deny. No answer
// in 120 s is a denial (core's).
Rectangle {
    id: card
    objectName: 'assistantPrompt'
    readonly property var request: ShellState.pairRequest
    visible: !!request
    implicitHeight: visible ? column.implicitHeight + 28 : 0
    radius: Tokens.radius
    color: Tokens.raised
    border.width: 2
    border.color: Tokens.gold
    ColumnLayout {
        id: column
        anchors.fill: parent
        anchors.margins: 14
        spacing: 8
        RowLayout {
            Layout.fillWidth: true
            HudLabel { objectName: 'assistantPromptTitle'; Layout.fillWidth: true; text: Assistants.promptTitle(card.request); font.pixelSize: 17; color: Tokens.text; elide: Text.ElideRight }
            HudLabel { text: Assistants.secondsLeft(card.request) + ' s'; font.pixelSize: 12; color: Tokens.muted }
        }
        HudLabel { Layout.fillWidth: true; text: Assistants.promptText(card.request); font.pixelSize: 12; color: Tokens.muted; wrapMode: Text.Wrap }
        RowLayout {
            spacing: 10
            Repeater {
                model: Assistants.DECISIONS
                ActionButton {
                    required property var modelData
                    objectName: 'assistant-' + modelData.id
                    text: modelData.label
                    primary: modelData.id === 'once'
                    onClicked: ShellState.assistantAnswer(modelData.id)
                }
            }
        }
    }
}
