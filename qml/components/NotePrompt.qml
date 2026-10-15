import "../theme"
import ".."
import QtQuick

// IPC 0.17 debug capture note: one line, Enter saves (empty allowed), Esc (core's
// menu exit) saves nothing. The capture itself is already on disk. IPC 0.29: the same prompt
// labels a debug recording just stopped (Ctrl+R); Esc keeps its time-only name.
Rectangle {
    id: root

    implicitWidth: 560  // clears the HUD hint tiles at 1920 wide
    implicitHeight: 60
    radius: Tokens.radius
    color: Tokens.light ? '#f2eff3ed' : '#f20b1420'
    border.width: 1
    border.color: field.activeFocus ? Tokens.gold : Tokens.line

    Text {
        id: label
        anchors { left: parent.left; leftMargin: 16; verticalCenter: parent.verticalCenter }
        text: ShellState.noteRecording ? 'LABEL' : 'WHY?'
        color: Tokens.gold
        font { family: Tokens.mono; pixelSize: 13; letterSpacing: 1.5; bold: true }
    }

    TextInput {
        id: field
        objectName: 'capture-note-field'
        anchors { left: label.right; leftMargin: 14; right: hint.left; rightMargin: 14; verticalCenter: parent.verticalCenter }
        focus: true
        clip: true
        maximumLength: ShellState.noteRecording ? 120 : 1000
        color: Tokens.text
        selectionColor: Tokens.accent
        selectedTextColor: Tokens.ink
        font { family: Tokens.sans; pixelSize: 17 }
        text: ShellState.noteText
        onTextEdited: ShellState.noteText = text
        Keys.onReturnPressed: ShellState.submitNote()
        Keys.onEnterPressed: ShellState.submitNote()
        Keys.onEscapePressed: ShellState.dismissNote()
        Connections {
            target: ShellState
            function onNotePromptChanged() { if (ShellState.notePrompt) field.forceActiveFocus(); }
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            visible: !field.text
            text: ShellState.noteRecording ? 'Label this recording (Enter to skip)' : 'Why? (Enter to skip)'
            color: Tokens.muted
            font: field.font
        }
    }

    Text {
        id: hint
        anchors { right: parent.right; rightMargin: 16; verticalCenter: parent.verticalCenter }
        text: field.length > field.maximumLength - 100 ? (field.maximumLength - field.length) + ' left' : 'Enter · save   Esc · none'
        color: Tokens.muted
        font { family: Tokens.mono; pixelSize: 11 }
    }
}
