import QtQuick
import "../theme"

// Scene-graph transforms preserve distance-field text: no offscreen texture,
// shader pass, or continuous animation. Qt also maps hit tests through these
// transforms; the production HUD's whole layer remains pointer-transparent.
Item {
    id: root
    property real edgeX: 0
    property real edgeY: 0
    property bool scrim: true
    property bool shown: true
    opacity: shown ? 1 : 0
    visible: opacity > 0
    Behavior on opacity { NumberAnimation { duration: Tokens.motion; easing.type: Easing.OutCubic } }
    readonly property real bend: Tokens.hudCurved ? Tokens.hudCurvature : 0
    transform: [
        Rotation { origin.x: root.width / 2; origin.y: root.height / 2; axis { x: 0; y: 1; z: 0 } angle: -root.edgeX * 12 * root.bend },
        Rotation { origin.x: root.width / 2; origin.y: root.height / 2; axis { x: 1; y: 0; z: 0 } angle: root.edgeY * 7 * root.bend }
    ]
    Rectangle {
        z: -1
        visible: root.scrim
        anchors.fill: parent
        anchors.margins: -12
        radius: 6
        // Alpha compositing naturally darkens bright stone and stays quiet over
        // dark worlds. A fixed lower luminance bound protects small text.
        gradient: Gradient {
            GradientStop { position: 0; color: '#df0a1420' }
            GradientStop { position: 1; color: '#b80a1420' }
        }
        border.color: '#253e536a'
    }
}
