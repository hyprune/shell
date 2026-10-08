import QtQuick
import QtQuick.Shapes
import ".."

Item {
    id: root
    property real progress: 0
    property var hold: ShellState.menuHold
    function updateHold() {
        fill.stop();
        progress = hold ? hold.progress : 0;
        if (hold && hold.remainingMs > 0) {
            fill.from = progress;
            fill.duration = hold.remainingMs;
            fill.start();
        }
    }
    onHoldChanged: updateHold()
    Component.onCompleted: updateHold()
    NumberAnimation { id: fill; target: root; property: 'progress'; to: 1; easing.type: Easing.Linear }
    width: 40; height: 40
    Rectangle { anchors.fill: parent; radius: width / 2; color: 'transparent'; border.color: '#52667d'; border.width: 1 }
    Shape {
        anchors.fill: parent
        ShapePath {
            strokeColor: '#e2edff'; strokeWidth: 2; fillColor: 'transparent'; capStyle: ShapePath.RoundCap
            PathAngleArc { centerX: root.width / 2; centerY: root.height / 2; radiusX: root.width / 2 - 1; radiusY: root.height / 2 - 1; startAngle: -90; sweepAngle: Math.max(0, Math.min(1, root.progress)) * 359.9 }
        }
    }
    HudLabel { anchors.centerIn: parent; text: 'TAB'; font.pixelSize: 10; color: '#e2edff' }
}
