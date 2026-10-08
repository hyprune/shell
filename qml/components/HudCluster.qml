import QtQuick
import "../theme"
import "HudPerspective.js" as Perspective
Item {
    id: root
    property real edgeX: 0
    property real edgeY: 0
    property real curvatureScale: 1
    property bool scrim: false
    property bool shown: true
    readonly property real bend: Tokens.hudCurved ? Tokens.hudCurvature * curvatureScale : 0
    opacity: shown ? 1 : 0
    visible: opacity > 0
    Behavior on opacity { NumberAnimation { duration: Tokens.reducedMotion ? 0 : 360; easing.type: Easing.OutCubic } }
    // Native scene graph by default; small-text clusters can opt into a layer.
    transform: Matrix4x4 { matrix: Perspective.matrix(root.width,root.height,root.edgeX,root.edgeY,root.bend) }
    Rectangle { z:-1; visible:root.scrim; anchors.fill:parent; anchors.margins:-10; color:'#a008141d'; radius:3 }
}
