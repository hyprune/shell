import QtQuick
import QtQuick.Shapes
import "../theme"
Item {
    id:root
    property color color: Tokens.hudTile
    property color borderColor: 'transparent'
    property real borderWidth: 0
    Rectangle { anchors.fill:parent; visible:Tokens.hudCorners!=='bevel'; color:root.color;radius:Tokens.hudCorners==='round' ? 9 : 0;border.color:root.borderColor;border.width:root.borderWidth }
    Shape { anchors.fill:parent; visible:Tokens.hudCorners==='bevel'
        ShapePath { fillColor:root.color;strokeColor:root.borderColor;strokeWidth:root.borderWidth
            PathSvg {path:'M7 0 H'+root.width+' V'+(root.height-7)+' L'+(root.width-7)+' '+root.height+' H0 V7 Z'}
        }
    }
}
