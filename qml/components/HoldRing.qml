import QtQuick
import QtQuick.Shapes
import ".."
import "../theme"
import "../Quests.js" as Quests

// The Director hold ring (keymap.holds, action menu). A TAB tap reveals markers
// (RFC-0012), so the fill waits ShellState.holdRingDelayMs after the hold started and
// then fills the remaining time: a tap never flashes it. Reduced motion: the same
// delay, then a static ring without the fill animation.
Item {
    id: root
    property real progress: 0
    property bool filling: false
    property double received: 0
    property var hold: ShellState.menuHold
    function updateHold() {
        fill.stop(); wait.stop();
        received = Date.now();
        var view = Quests.holdView(hold, 0, ShellState.holdRingDelayMs);
        if (!hold || !view.visible) {
            progress = 0; filling = false;
            if (hold && view.waitMs > 0) { wait.interval = Math.max(1, Math.ceil(view.waitMs)); wait.start(); }
            return;
        }
        begin(view);
    }
    function begin(view) {
        filling = true;
        if (ShellState.holdStats.lastStartedAtMs !== hold.startedAtMs)  // one count per hold
            ShellState.holdStats = Object.assign({}, ShellState.holdStats, {shown: ShellState.holdStats.shown + 1, lastStartedAtMs: hold.startedAtMs,
                lastDelayMs: Math.round(hold.durationMs - hold.remainingMs + (Date.now() - received))});
        if (Tokens.reducedMotion) { progress = 1; return; }
        progress = view.progress;
        if (view.fillMs > 0) { fill.from = progress; fill.duration = view.fillMs; fill.start(); }
    }
    onHoldChanged: updateHold()
    Component.onCompleted: updateHold()
    Timer { id: wait; onTriggered: { if (root.hold) root.begin(Quests.holdView(root.hold, Date.now() - root.received, ShellState.holdRingDelayMs)); } }
    NumberAnimation { id: fill; target: root; property: 'progress'; to: 1; easing.type: Easing.Linear }
    width: 40; height: 40
    Rectangle { anchors.fill: parent; radius: width / 2; color: 'transparent'; border.color: '#52667d'; border.width: 1 }
    Shape {
        anchors.fill: parent
        visible: root.filling
        opacity: Tokens.reducedMotion ? 0.7 : 1
        ShapePath {
            strokeColor: '#e2edff'; strokeWidth: 2; fillColor: 'transparent'; capStyle: ShapePath.RoundCap
            PathAngleArc { centerX: root.width / 2; centerY: root.height / 2; radiusX: root.width / 2 - 1; radiusY: root.height / 2 - 1; startAngle: -90; sweepAngle: Math.max(0, Math.min(1, root.progress)) * 359.9 }
        }
    }
    HudLabel { anchors.centerIn: parent; text: 'TAB'; font.pixelSize: 10; color: '#e2edff' }
}
