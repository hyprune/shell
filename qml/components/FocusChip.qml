import QtQuick
import QtQuick.Shapes
import ".."
import "../theme"
import "../Quests.js" as Quests

// Focus session timer chip (RFC-0012): a ring with the elapsed share of the phase, a quiet
// credit arc inside it (work only; never "you were away"), mm:ss remaining counted down
// locally from phaseEndsAtMs on core's monotonic clock, the phase label and cycle dots.
Item {
    id: root
    objectName: 'hudFocusChip'
    readonly property var session: ShellState.focusState
    readonly property bool technical: Tokens.hudConcept === 'Instrument'
    readonly property bool minimal: Tokens.hudConcept === 'Minimal'
    readonly property string tone: Quests.phaseTone(session)
    readonly property color toneColor: tone === 'break' ? Tokens.hudBreak : tone === 'work' ? Tokens.hudAccent : Tokens.hudMuted
    readonly property bool running: !!session && (session.state === 'work' || session.state === 'break')
    property double remainingMs: 0
    function tick() { remainingMs = Quests.remaining(session, running ? ShellState.monotonicNow() : null); }
    onSessionChanged: tick()
    Timer { interval: 250; repeat: true; running: root.visible && root.running; triggeredOnStart: true; onTriggered: root.tick() }
    readonly property real ring: Quests.ringProgress(session, remainingMs)
    readonly property real credit: Quests.creditProgress(session)
    readonly property var dots: Quests.cycleDots(session)
    implicitWidth: 248
    implicitHeight: 60

    Connections {
        target: ShellState
        function onFocusPulse(phase) { if (!Tokens.reducedMotion && root.visible) pulse.restart(); }
    }
    SequentialAnimation {
        id: pulse
        NumberAnimation { target: body; property: 'scale'; to: 1.06; duration: 140; easing.type: Easing.OutCubic }
        NumberAnimation { target: body; property: 'scale'; to: 1; duration: 320; easing.type: Easing.OutCubic }
    }

    Item {
        id: body
        anchors.fill: parent
        transformOrigin: Item.Right
        HudTile {
            anchors.fill: parent
            color: root.minimal ? '#b013242d' : Qt.rgba(Tokens.hudScrim.r, Tokens.hudScrim.g, Tokens.hudScrim.b, .82)
            borderColor: root.technical ? root.toneColor : 'transparent'
            borderWidth: root.technical ? 1 : 0
        }
        Rectangle { anchors.right: parent.right; width: root.minimal ? 2 : 4; height: parent.height; color: root.toneColor }
        Item {
            id: dial
            x: 9; anchors.verticalCenter: parent.verticalCenter
            width: 44; height: 44
            Rectangle { anchors.fill: parent; radius: width / 2; color: 'transparent'; border.color: '#6688a0b0'; border.width: 2 }
            Shape {
                anchors.fill: parent
                ShapePath {
                    strokeColor: root.toneColor; strokeWidth: 3; fillColor: 'transparent'; capStyle: ShapePath.FlatCap
                    PathAngleArc { centerX: 22; centerY: 22; radiusX: 21; radiusY: 21; startAngle: -90; sweepAngle: Math.max(0, Math.min(1, root.ring)) * 359.9 }
                }
            }
            // Credited work time: a thin, quiet inner arc.
            Shape {
                anchors.fill: parent
                visible: root.credit > 0
                opacity: .55
                ShapePath {
                    strokeColor: Tokens.hudWhite; strokeWidth: 2; fillColor: 'transparent'; capStyle: ShapePath.FlatCap
                    PathAngleArc { centerX: 22; centerY: 22; radiusX: 16; radiusY: 16; startAngle: -90; sweepAngle: Math.max(0, Math.min(1, root.credit)) * 359.9 }
                }
            }
            HudText {
                anchors.centerIn: parent
                text: root.session && root.session.state === 'paused' ? '❚❚' : root.session && root.session.cycle ? String(root.session.cycle) : ''
                font.pixelSize: root.session && root.session.state === 'paused' ? 10 : 13
                color: root.toneColor
            }
        }
        HudText {
            id: clock
            objectName: 'hudFocusTime'
            x: dial.x + dial.width + 12; y: 8
            width: parent.width - x - 14 - (dotsRow.visible ? dotsRow.width + 8 : 40)
            text: root.session && root.session.state !== 'idle' ? Quests.countdown(root.remainingMs) : ''
            font.family: Tokens.mono
            font.pixelSize: text.length > 5 ? 16 : 20
            smallText: false
        }
        HudText {
            objectName: 'hudFocusPhase'
            x: clock.x; y: 36
            width: Math.max(0, parent.width - x - 14)
            text: Quests.phaseLabel(root.session).toUpperCase()
            font.pixelSize: 11; font.letterSpacing: 1.2
            color: root.toneColor
        }
        // Cycle dots beside the time (eight at most; longer sessions show "3 / 12").
        HudText {
            visible: root.dots.length > 8
            anchors.right: parent.right; anchors.rightMargin: 14
            y: 14
            text: root.session ? root.session.cycle + ' / ' + root.session.cycles : ''
            font.family: Tokens.mono; font.pixelSize: 11
            color: root.toneColor
        }
        Row {
            id: dotsRow
            objectName: 'hudFocusDots'
            visible: root.dots.length <= 8
            anchors.right: parent.right; anchors.rightMargin: 14
            y: 17
            spacing: 4
            Repeater {
                model: root.dots
                Rectangle {
                    required property string modelData
                    width: 7; height: 7; radius: 3.5
                    color: modelData === 'done' ? root.toneColor : 'transparent'
                    border.width: 1
                    border.color: modelData === 'todo' ? '#90c5d2d2' : root.toneColor
                    Rectangle { visible: parent.modelData === 'current'; anchors.centerIn: parent; width: 3; height: 3; radius: 1.5; color: root.toneColor }
                }
            }
        }
    }
}
