import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../Quests.js" as Quests

// Director > Quests: the focus session controls (RFC-0012). Pause, resume, skip and stop
// never warn or penalise. Keyboard reachable with Tab; F starts a session from a quest.
ColumnLayout {
    id: root
    readonly property var session: ShellState.focusState
    readonly property bool idle: !session || session.state === 'idle'
    readonly property bool running: !!session && (session.state === 'work' || session.state === 'break')
    property double remainingMs: 0
    function tick() { remainingMs = Quests.remaining(session, running ? ShellState.monotonicNow() : null); }
    onSessionChanged: tick()
    Timer { interval: 250; repeat: true; running: root.visible && root.running; triggeredOnStart: true; onTriggered: root.tick() }
    spacing: 8

    RowLayout {
        Layout.fillWidth: true
        HudLabel { text: 'FOCUS SESSION'; color: Tokens.gold; font.pixelSize: Tokens.caption; font.letterSpacing: 1.5; Layout.fillWidth: true }
        HudLabel {
            visible: !root.idle
            text: Quests.countdown(root.remainingMs)
            font.family: Tokens.mono; font.pixelSize: 15
            color: Tokens.text
        }
    }
    HudLabel {
        Layout.fillWidth: true
        text: root.idle ? 'Work intervals and breaks in cycles. Start one from a quest step (F), or a free session here.'
                        : Quests.phaseLabel(root.session) + '  ·  interval ' + root.session.cycle + ' of ' + root.session.cycles
                          + (root.session.target && root.session.target.label ? '  ·  ' + root.session.target.label : '')
        color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap
    }
    // What counts: any focused window, or windows on one workspace (default: the current one).
    RowLayout {
        Layout.fillWidth: true
        visible: root.idle
        spacing: 8
        Segmented {
            objectName: 'focus-target'
            Layout.fillWidth: true
            model: [{id: 'any', label: 'Any window'}, {id: 'workspace', label: 'Workspace'}]
            current: ShellState.focusTargetChoice.kind
            onPicked: (kind) => ShellState.focusTargetChoice = Object.assign({}, ShellState.focusTargetChoice, {kind: kind})
        }
        TextField {
            id: workspaceField
            objectName: 'focus-target-workspace'
            visible: ShellState.focusTargetChoice.kind === 'workspace'
            Layout.preferredWidth: 72
            implicitHeight: 42
            color: Tokens.text
            placeholderText: ShellState.currentWorkspace ? String(ShellState.currentWorkspace) : 'No.'
            placeholderTextColor: Tokens.muted
            font.family: Tokens.sans; font.pixelSize: 14
            horizontalAlignment: Text.AlignHCenter
            validator: IntValidator { bottom: 1; top: 2147483647 }
            text: ShellState.focusTargetChoice.workspaceId ? String(ShellState.focusTargetChoice.workspaceId) : ''
            onTextEdited: ShellState.focusTargetChoice = Object.assign({}, ShellState.focusTargetChoice, {workspaceId: Number(text) || 0})
            background: Rectangle { radius: Tokens.radius; color: Tokens.panel; border.width: parent.activeFocus ? 2 : 1; border.color: parent.activeFocus ? Tokens.gold : Tokens.line }
            ToolTip.text: 'Workspace number; empty = the current one'; ToolTip.visible: hovered
        }
    }
    Flow {
        Layout.fillWidth: true
        spacing: 8
        ActionButton {
            implicitWidth: Math.max(84, contentItem.implicitWidth + 34)
            objectName: 'focus-start'
            visible: root.idle
            text: 'Start focus session'
            enabled: ShellState.available('focus.start')
            onClicked: {
                var target = ShellState.focusTarget();
                if (target) ShellState.questAction('focus.start', {target: target});
                else { ShellState.questFeedback = 'Choose a workspace number for the focus session.'; ShellState.questFeedbackTimer.restart(); }
            }
        }
        ActionButton {
            implicitWidth: Math.max(84, contentItem.implicitWidth + 34)
            objectName: 'focus-pause'
            visible: root.running
            text: 'Pause'
            enabled: ShellState.available('focus.pause')
            onClicked: ShellState.questAction('focus.pause', {})
        }
        ActionButton {
            implicitWidth: Math.max(84, contentItem.implicitWidth + 34)
            objectName: 'focus-resume'
            visible: !root.idle && !root.running
            text: root.session && root.session.state === 'ready' ? (root.session.breakKind ? 'Start break' : 'Start next interval') : 'Resume'
            primary: true
            enabled: ShellState.available('focus.resume')
            onClicked: ShellState.questAction('focus.resume', {})
        }
        ActionButton {
            implicitWidth: Math.max(84, contentItem.implicitWidth + 34)
            objectName: 'focus-skip'
            visible: !root.idle
            text: root.session && Quests.phaseTone(root.session) === 'break' ? 'Skip break' : 'Skip'
            enabled: ShellState.available('focus.skip')
            onClicked: ShellState.questAction('focus.skip', {})
        }
        ActionButton {
            implicitWidth: Math.max(84, contentItem.implicitWidth + 34)
            objectName: 'focus-stop'
            visible: !root.idle
            text: 'Stop'
            enabled: ShellState.available('focus.stop')
            onClicked: ShellState.questAction('focus.stop', {})
        }
    }
}
