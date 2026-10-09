import QtQuick
import Quickshell
import ".."
import "../theme"
Item {
    id: root
    property bool compact:false
    property bool dense:false
    readonly property bool condensed:compact && liveHints.visible
    readonly property bool minimal: Tokens.hudConcept === 'Minimal'
    readonly property bool technical: Tokens.hudConcept === 'Instrument'
    readonly property int tile: compact ? 40 : minimal ? 40 : technical ? 51 : 58
    readonly property int gridSize: tile*2+5
    readonly property int placeSize: dense ? 56 : gridSize
    // Visibility is inherited from feedbackRows: using the child's effective
    // visible value here would prevent a scale-only update from opening it.
    readonly property bool feedback: (HudData.carry.active || scaleFeedback.showing) && HudData.worldPrompts
    readonly property real detailsBottom: liveHints.visible ? liveHints.y+liveHints.implicitHeight+24 : HudData.placing ? placeSize+90 : minimal ? (HudData.climbing ? 174 : 155) : 203
    implicitHeight: detailsBottom+(feedback ? 52 : 0)
    property string displayedSubtype: HudData.subtype
    Connections {
        target: HudData
        function onSubtypeChanged() { root.displayedSubtype = HudData.subtype; if (!Tokens.reducedMotion) whoosh.restart(); }
    }
    Grid {
        visible: !HudData.placing
        columns: 2; spacing: 5
        opacity: HudData.freeCursor ? .55 : 1
        Repeater {
            model: 4
            HudTile {
                required property int index
                readonly property bool customIcon: !!(Tokens.skin.icons && Tokens.skin.icons[['navigate','window','path','position'][index]])
                width: root.tile; height: width
                color: HudData.tool === index+1 && !customIcon ? Tokens.hudAccent : Tokens.hudTile
                borderWidth: customIcon && HudData.tool === index+1 ? 3 : root.technical ? 1 : 0; borderColor: customIcon ? Tokens.hudAccent : '#95dce4e5'
                ToolGlyph { anchors.centerIn: parent; width: parent.width*.66; height: width; tool: index+1; tint: HudData.tool === index+1 ? '#112c36' : '#e8f6f3' }
                HudText { x: 3; y: 1; text: index+1; font.pixelSize: 8; opacity: .85 }
            }
        }
    }
    HudTile {
        objectName: 'hudPlacementTile'
        visible: HudData.placing; width:root.placeSize; height:width
        color:Tokens.hudAccent; opacity:HudData.freeCursor ? .55 : 1
        ToolGlyph { anchors.centerIn:parent; width:parent.width*.7; height:width; tool:5; tint:'#112c36' }
        HudText { x:root.dense ? 4 : 7; y:root.dense ? 2 : 4; text:'5'; font.pixelSize:root.dense ? 10 : 12; color:'#112c36'; shadowEnabled:false }
    }
    HudTile {
        objectName:'hudUnplacedBadge'
        visible:!HudData.placing && HudData.placement.count>0
        y:-30; height:25; width:Math.min(parent.width,badgeText.implicitWidth+24)
        color:Tokens.hudScrim; borderColor:Tokens.hudAccent; borderWidth:1
        HudText { id:badgeText; x:10; anchors.verticalCenter:parent.verticalCenter; width:parent.width-20; text:HudData.placement.count+' IN POCKET'; font.pixelSize:12; color:Tokens.hudAccent }
    }
    PlacementInfo {
        visible:HudData.placing; x:root.placeSize+(root.dense ? 8 : 18); width:parent.width-x; height:root.placeSize
        technical:root.technical; minimal:root.minimal; dense:root.dense; opacity:HudData.freeCursor ? .55 : 1
    }
    Item {
        id: subtypeScene
        visible: !HudData.placing
        opacity: HudData.freeCursor ? .55 : 1
        x: root.gridSize+18; width: parent.width-x; height: root.gridSize
        Rectangle { anchors.fill: parent; color: Qt.rgba(Tokens.hudScrim.r,Tokens.hudScrim.g,Tokens.hudScrim.b,.5); border.color: root.technical ? '#608dbfc8' : 'transparent' }
        Rectangle { width: 2; height: parent.height; color: Tokens.hudAccent }
        HudText { x: 14; y: 5; width: parent.width-24; text: HudData.toolName.toUpperCase(); font.pixelSize: 13; font.letterSpacing: 2; color: Tokens.hudMuted }
        Item {
            id: subtypeContent
            x: 14; y: 25; width: parent.width-24; height: parent.height-29
            ToolGlyph { allowOverride:false; width: root.minimal ? 33 : 46; height: width; anchors.verticalCenter: parent.verticalCenter; tool: HudData.tool; subtype: root.displayedSubtype; tint: Tokens.hudAccent }
            HudText { smallText:false; x: root.minimal ? 46 : 60; width: parent.width-x; anchors.verticalCenter: parent.verticalCenter; text: root.displayedSubtype === 'normal' ? 'EXPLORE' : root.displayedSubtype.toUpperCase(); font.pixelSize: root.minimal ? 24 : 32; font.letterSpacing: 1; maximumLineCount: 2; wrapMode: Text.Wrap }
        }
        ParallelAnimation {
            id: whoosh
            NumberAnimation { target: subtypeContent; property: 'x'; from: 47; to: 14; duration: 340; easing.type: Easing.OutCubic }
            NumberAnimation { target: subtypeContent; property: 'opacity'; from: .1; to: 1; duration: 220 }
        }
    }
    Rectangle {
        visible:!HudData.placing && !root.condensed
        y: root.gridSize+10; width: parent.width; height: root.technical ? 5 : 7; color: '#b013242d'
        Rectangle { width: parent.width*Math.max(0,Math.min(1,HudData.resourceValue)); height: parent.height; color: Tokens.hudAccent; Behavior on width { NumberAnimation { duration: 350 } } }
    }
    HudText { visible:!HudData.placing && !root.condensed; y: root.gridSize+23; width: parent.width*.65; text: HudData.resourceLabel; font.pixelSize: 12; font.letterSpacing: .9; color: Tokens.hudMuted }
    HudText { visible:!HudData.placing && !root.condensed; y: root.gridSize+23; width: parent.width*.35; anchors.right: parent.right; text: HudData.resourceText; horizontalAlignment: Text.AlignRight; font.pixelSize: 13; font.family: Tokens.mono }
    HudText { visible:!HudData.climbing && !HudData.placing && !root.condensed; y: root.gridSize+43; width: parent.width; text: HudData.stats; font.pixelSize: 14; font.family: Tokens.mono }
    HudText { y: root.gridSize+61; width: parent.width; objectName:"hudToolHint"; visible: text!=='' && !root.minimal && HudData.worldPrompts && !HudData.climbing && !HudData.placing && !liveHints.visible; text: Tokens.hudResource === 'ram' ? 'RAM unavailable · GPU budget shown' : HudData.activeWindow; font.pixelSize: 13; color: Tokens.hudMuted }
    Item {
        objectName: 'hudClimbPrompt'
        visible: HudData.climbing
        y:root.gridSize+43; width:parent.width; height:40
        HudTile { anchors.fill:parent; color:'#b813242d'; borderWidth:root.technical ? 1 : 0; borderColor:Tokens.hudAccent }
        // Original ladder indicator; no font/icon-package dependency.
        Item { x:7; width:18; height:26; y:7
            Rectangle { x:3; width:2; height:parent.height; color:Tokens.hudAccent }
            Rectangle { x:13; width:2; height:parent.height; color:Tokens.hudAccent }
            Repeater { model:3; Rectangle { required property int index; x:3; y:5+index*8; width:12; height:2; color:Tokens.hudAccent } }
        }
        HudText { objectName:'hudClimbText'; x:32; y:3; width:parent.width-x-8; text:HudData.climbPrompt; font.pixelSize:12; font.family:root.technical ? Tokens.mono : Tokens.hudFont; maximumLineCount:2; wrapMode:Text.Wrap }
    }
    ToolHints {
        id:liveHints; objectName:'hudToolHints'
        visible:HudData.worldPrompts && !HudData.climbing && actions.length>0
        y:HudData.placing ? root.placeSize+(root.dense ? 6 : 10) : root.condensed ? root.gridSize+10 : root.gridSize+65; width:parent.width; dense:root.dense
    }
    HudText {
        objectName:'hudGhostIndicator'; visible:HudData.placing && HudData.worldPrompts
        y:liveHints.visible ? liveHints.y+liveHints.implicitHeight+5 : root.placeSize+10; width:parent.width
        text:HudData.placement.count===0 ? 'POCKET EMPTY' : HudData.placement.ghost ? '◇ GHOST PREVIEW' : '◇ PREVIEW UNAVAILABLE'
        font.pixelSize:12;color:Tokens.hudAccent
    }
    Rectangle { x:0;y:feedbackRows.y-4; width:parent.width; height:feedbackRows.height+8; color:'#c013242d'; visible:root.feedback }
    Column {
        id:feedbackRows
        x:8;y:root.detailsBottom; width:parent.width-16; spacing:5
        visible:root.feedback
        HudText { objectName:'hudCarryOrientation'; visible:HudData.carry.active && HudData.worldPrompts; width:parent.width; text:HudData.carry.label+(HudData.carry.toggle ? ' · '+HudData.carry.toggle : ''); font.pixelSize:12; color:Tokens.hudAccent }
        HudText { id:scaleFeedback; objectName:'hudContentScale'; property var sample:null; property bool showing:false
            visible:showing && HudData.worldPrompts; width:parent.width; font.pixelSize:12; maximumLineCount:2; wrapMode:Text.Wrap
            text:sample ? (sample.reset ? 'RESET · ' : '')+'SCALE '+Math.round(sample.scale*100)+'%'+(sample.clientSize ? ' · '+sample.clientSize[0]+'×'+sample.clientSize[1]+' client' : '') : ''
            Connections { target:ShellState; function onContentFeedback(next) {
                scaleFeedback.sample=next;scaleFeedback.showing=true;scaleHide.restart();
            } }
            Connections { target:HudData; function onContentChanged() {
                if (!HudData.content) {scaleFeedback.showing=false;scaleFeedback.sample=null;}
            } }
            Timer { id:scaleHide; interval:2400; onTriggered:scaleFeedback.showing=false }
        }
    }

}
