import QtQuick
import QtQuick.Layouts
import ".."
import "../theme"
Column {
    id:root
    spacing:5
    readonly property bool technical:Tokens.hudConcept==='Instrument'
    readonly property var actions:HudData.hints.actions || []
    readonly property string text:actions.map(a=>(a.bindings.length ? a.bindings.join(' / ') : 'Unbound')+' · '+a.label).join(' | ')
    HudText { visible:HudData.hints.context!==''; width:parent.width; text:HudData.hints.context; color:Tokens.hudAccent; font.pixelSize:11; font.letterSpacing:.7 }
    GridLayout {
        width:parent.width; columns:2; columnSpacing:8; rowSpacing:6; uniformCellWidths:true
        Repeater {
            model:root.actions
            Item {
                required property var modelData
                objectName:'hudToolAction'
                Layout.fillWidth:true; Layout.minimumWidth:0
                implicitHeight:actionLabels.height+10
                Rectangle { anchors.fill:parent; color:'#c013242d'; border.width:root.technical ? 1 : 0; border.color:'#558dbfc8' }
                Column {
                    id:actionLabels; x:8;y:5;width:parent.width-16; spacing:2
                    HudText { width:parent.width; text:modelData.bindings.length ? modelData.bindings.join(' / ') : 'Unbound'; font.pixelSize:10; font.family:Tokens.mono; color:Tokens.hudAccent }
                    HudText { width:parent.width; text:modelData.label; font.pixelSize:12; maximumLineCount:2; wrapMode:Text.Wrap }
                }
            }
        }
    }
}
