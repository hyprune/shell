import QtQuick
import "../theme"
Item {
    id:root
    readonly property bool technical: Tokens.hudConcept === 'Instrument'
    readonly property bool minimal: Tokens.hudConcept === 'Minimal'
    implicitWidth: caption.implicitWidth+30
    HudTile {
        anchors.fill:parent
        color:root.minimal ? '#b013242d' : Tokens.hudScrim
        borderColor:root.technical ? Tokens.hudAccent : 'transparent'
        borderWidth:root.technical ? 1 : 0
    }
    Rectangle { width:root.minimal ? 2 : 4; height:parent.height; color:Tokens.hudAccent }
    HudText {
        id:caption; objectName:'hudCursorText'
        x:14; width:parent.width-24; anchors.verticalCenter:parent.verticalCenter
        text:'CURSOR · Back / Super+Tab to return'
        font.family:root.technical ? Tokens.mono : Tokens.hudFont
        font.pixelSize:12; font.letterSpacing:root.minimal ? 0 : .4
    }
}
