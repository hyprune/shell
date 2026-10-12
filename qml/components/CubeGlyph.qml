import QtQuick
import QtQuick.Shapes
import "../theme"
// An object (RFC-0011): an outlined cube. Pocketed objects in the tool 5 HUD and catalog
// cards without a thumbnail.
Item {
    id: root
    property color tint: 'white'
    property real stroke: 1.8
    implicitWidth: 40; implicitHeight: 40
    Shape {
        width: 40; height: 40; scale: Math.min(root.width, root.height) / 40; transformOrigin: Item.TopLeft
        ShapePath {
            strokeColor: root.tint; strokeWidth: root.stroke; fillColor: 'transparent'; capStyle: ShapePath.RoundCap; joinStyle: ShapePath.RoundJoin
            PathSvg { path: 'M20 4 L35 12 L35 28 L20 36 L5 28 L5 12 Z M5 12 L20 20 L35 12 M20 20 L20 36' }
        }
    }
}
