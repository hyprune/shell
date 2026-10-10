import QtQuick
import QtQuick.Layouts
import ".."
import "../theme"
import "../PlayerSettings.js" as Player
Column {
    id:root
    spacing:5
    readonly property bool technical:Tokens.hudConcept==='Instrument'
    // Dense keeps binding and label on one row; bindings wrap rather than elide.
    property bool dense:false
    readonly property var actions:HudData.hints.actions || []
    // IPC 0.19: the primary action can't land (beyond reach or invalid target).
    readonly property bool primaryBlocked:Player.reticleBlocked(ShellState.state)
    readonly property string text:actions.map(a=>(a.bindings.length ? a.bindings.join(' / ') : 'Unbound')+' · '+a.label).join(' | ')
    HudText { visible:HudData.hints.context!==''; width:parent.width; text:HudData.hints.context; color:Tokens.hudAccent; font.pixelSize:11; font.letterSpacing:.7 }
    GridLayout {
        width:parent.width; columns:2; columnSpacing:root.dense ? 6 : 8; rowSpacing:root.dense ? 4 : 6; uniformCellWidths:true
        Repeater {
            model:root.actions
            Item {
                required property var modelData
                objectName:'hudToolAction'
                Layout.fillWidth:true; Layout.minimumWidth:0
                opacity:root.primaryBlocked && modelData.slot==='primary' ? .45 : 1
                readonly property string bindingText:modelData.bindings.length ? modelData.bindings.join(' / ') : 'Unbound'
                // One row only when both fit whole; otherwise stack (never split a chord).
                readonly property bool oneRow:root.dense && bindingMetrics.advanceWidth+labelMetrics.advanceWidth+26 <= width
                TextMetrics { id:bindingMetrics; font:denseBinding.font; text:bindingText }
                TextMetrics { id:labelMetrics; font:denseLabel.font; text:modelData.label }
                implicitHeight:oneRow ? denseLabels.height+6 : actionLabels.height+(root.dense ? 6 : 10)
                Rectangle { anchors.fill:parent; color:'#c013242d'; border.width:root.technical ? 1 : 0; border.color:'#558dbfc8' }
                Column {
                    id:actionLabels; visible:!oneRow; x:root.dense ? 6 : 8;y:root.dense ? 3 : 5;width:parent.width-2*x; spacing:root.dense ? 0 : 2
                    HudText { width:parent.width; text:bindingText; font.pixelSize:10; font.family:Tokens.mono; color:Tokens.hudAccent }
                    HudText { width:parent.width; text:modelData.label; font.pixelSize:12; maximumLineCount:2; wrapMode:Text.Wrap }
                }
                Item {
                    id:denseLabels; visible:oneRow; x:6;y:3;width:parent.width-12; height:Math.max(denseBinding.height,denseLabel.height)
                    HudText { id:denseBinding; y:2; width:Math.ceil(bindingMetrics.advanceWidth)+rightPadding+2; text:bindingText; font.pixelSize:10; font.family:Tokens.mono; color:Tokens.hudAccent }
                    HudText { id:denseLabel; x:denseBinding.width+4; width:parent.width-x; text:modelData.label; font.pixelSize:12 }
                }
            }
        }
    }
}
