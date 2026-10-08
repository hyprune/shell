import QtQuick
import QtQuick.Shapes
import "../theme"
Item {
    id: root
    property bool allowOverride: true
    property int tool: 1
    property string subtype: ''
    property color tint: 'white'
    implicitWidth: 40; implicitHeight: 40
    readonly property string overrideSource: allowOverride && Tokens.skin.icons ? Tokens.skin.icons[['navigate','window','path','position'][tool-1]] || '' : ''
    Image { id:customGlyph; anchors.fill:parent; source:root.overrideSource; onSourceChanged: { if (!Tokens.reducedMotion) reveal.restart(); } NumberAnimation { id:reveal; target:parent; property:"opacity"; from:0;to:1;duration:420 } fillMode:Image.PreserveAspectFit; sourceSize.width:Math.ceil(width*Screen.devicePixelRatio); sourceSize.height:Math.ceil(height*Screen.devicePixelRatio); visible:source.toString()!=='' }
    Shape {
        visible: customGlyph.status !== Image.Ready
        width: 40; height: 40; scale: Math.min(root.width,root.height)/40; transformOrigin: Item.TopLeft
        ShapePath {
            strokeColor: root.tint; strokeWidth: Tokens.skin.stroke ? Tokens.skin.stroke.width || 1.8 : 1.8; fillColor: 'transparent'; capStyle: ShapePath.RoundCap; joinStyle: ShapePath.RoundJoin
            PathSvg { path: root.tool === 1 ? 'M20 4 L31 32 L20 26 L9 32 Z M20 15 L20 26' : root.tool === 2 ? (root.subtype === 'lock' ? 'M11 18 L29 18 L29 33 L11 33 Z M15 18 L15 11 Q20 2 25 11 L25 18 M20 24 L20 28' : 'M5 9 L35 9 L35 31 L5 31 Z M5 15 L35 15 M11 12 L13 12 M17 12 L19 12') : root.tool === 3 ? (root.subtype.indexOf('curve') >= 0 ? 'M5 31 C5 1 35 39 35 9 M3 29 L7 33 M33 7 L37 11' : root.subtype.indexOf('arc') >= 0 ? 'M5 31 Q20 -5 35 31 M3 29 L7 33 M33 29 L37 33' : 'M5 31 L19 12 L35 24 M3 29 L7 33 M17 10 L21 14 M33 22 L37 26') : root.subtype === 'rotate' ? 'M30 12 A14 14 0 1 0 33 24 M24 11 L32 11 L32 3' : root.subtype === 'scale' ? 'M7 22 L7 33 L18 33 L18 22 Z M18 22 L33 7 M24 7 L33 7 L33 16' : 'M20 4 L20 36 M4 20 L36 20 M15 9 L20 4 L25 9 M15 31 L20 36 L25 31 M9 15 L4 20 L9 25 M31 15 L36 20 L31 25' }
        }
    }
}
