import ".."
import "../theme"
import QtQuick
Item {
    id: root
    readonly property real holdProgress: holdRing.progress
    readonly property bool minimal: Tokens.hudConcept === 'Minimal'
    readonly property bool technical: Tokens.hudConcept === 'Instrument'
    readonly property bool compact: width < 1200 || height < 700
    readonly property real inset: compact ? 26 : 56
    readonly property string mode: HudData.editor ? HudData.editor.mode : 'world'
    HudCluster {
        x: root.inset; y: root.inset; width: root.compact ? 126 : root.minimal ? 116 : root.technical ? 190 : 178; height: width+26
        edgeX:-1; edgeY:-1
        Radar { id:localRadar; width:parent.width; height:width }
        HudText { anchors.bottom:parent.bottom; width:parent.width; text: root.technical ? Math.round(ShellState.heading)+'° / '+Math.round(localRadar.range)+' m' : ShellState.worldName.toUpperCase(); font.pixelSize:12; font.letterSpacing:1 }
    }
    HudCluster {
        anchors.horizontalCenter:parent.horizontalCenter; y: root.inset; width: Math.min(510,root.width*.38); height:70; edgeY:-1
        Compass { anchors.fill:parent }
    }
    HudCluster {
        anchors.right:parent.right; anchors.rightMargin:root.inset; y:root.inset; width: root.compact ? 230 : 310; height:72
        edgeX:1; edgeY:-1
        HudText { width:parent.width; horizontalAlignment:Text.AlignRight; text: root.mode === 'world' ? 'NAVIGATION' : root.mode.toUpperCase(); font.pixelSize: root.technical ? 17 : 14; font.letterSpacing:2 }
        HudText { y:29; width:parent.width; horizontalAlignment:Text.AlignRight; text: root.technical ? ShellState.pose.map(v=>v.toFixed(1)).join(' / ')+' m' : root.mode === 'world' ? 'WORLD RECEIVES INPUT' : 'SUPER+TAB · RETURN'; color:Tokens.hudMuted; font.pixelSize:12; font.family:root.technical ? Tokens.mono : Tokens.sans }
        HudText { y:49; width:parent.width; horizontalAlignment:Text.AlignRight; visible:root.technical; text:HudData.stats; font.pixelSize:12; color:Tokens.hudMuted }
    }
    HudCluster {
        id: deck
        x:root.inset; y:root.height-height-root.inset-46
        width: Math.min(root.width*.55,root.minimal ? 460 : root.technical ? 620 : 590); height: toolDeck.implicitHeight
        edgeX:-1; edgeY:1
        ToolDeck { id:toolDeck; anchors.fill:parent }
    }
    HudCluster {
        x:root.inset; y:deck.y-height-30; width:Math.min(640,root.width*.65); height:zoneColumn.height
        edgeX:-1; edgeY:.5; shown:ShellState.zone !== ''
        Column { id:zoneColumn; width:parent.width; spacing:12
            HudText { width:parent.width; text:ShellState.zone.toUpperCase(); font.pixelSize:root.compact ? 25 : 35; font.letterSpacing:5; maximumLineCount:root.compact ? 1 : 2; wrapMode:root.compact ? Text.NoWrap : Text.Wrap }
            HudText { width:parent.width; text:ShellState.zoneSubtitle.toUpperCase(); font.pixelSize:12; font.letterSpacing:3; color:Tokens.hudMuted }
        }
    }
    HudCluster {
        x:root.inset; y:root.height-root.inset-36; width:Math.min(680,root.width-root.inset*2); height:36; edgeX:-1;edgeY:1
        HoldRing { id:holdRing; width:32;height:32 }
        HudText { x:44;y:9;width:parent.width-x;text:root.minimal ? 'HOLD · DIRECTOR' : 'HOLD · DIRECTOR    E · USE    F · FOCUS    Q · SCOPE'; font.pixelSize:12; font.letterSpacing:.5; color:Tokens.hudMuted }
    }
    Item {
        anchors.horizontalCenter:parent.horizontalCenter; y:root.compact ? 110 : root.height*.29; width:Math.min(520,root.width*.7);height:49
        opacity:ShellState.banner ? 1 : 0
        Behavior on opacity { NumberAnimation { duration:Tokens.reducedMotion ? 0 : 240 } }
        Rectangle { anchors.fill:parent; color:'#5808121a'; border.width:1; border.color:Tokens.hudAccent }
        Rectangle { anchors.horizontalCenter:parent.horizontalCenter; width:80;y:-3;height:2;color:Tokens.hudAccent }
        HudText { anchors.fill:parent; anchors.margins:12; text:ShellState.banner; horizontalAlignment:Text.AlignHCenter; verticalAlignment:Text.AlignVCenter;font.pixelSize:13;font.letterSpacing:3;color:Tokens.hudAccent }
    }
    HudCluster {
        anchors.right:parent.right; anchors.rightMargin:root.inset; y:root.height-height-root.inset-54;width:Math.min(340,root.width*.28);height:noticeColumn.height;edgeX:1;edgeY:1;shown:ShellState.notices.length>0
        Column { id:noticeColumn; width:parent.width; spacing:12
            Repeater { model:ShellState.notices.slice(-2); HudText { required property var modelData; width:parent.width;text:modelData.message;maximumLineCount:3;wrapMode:Text.Wrap;font.pixelSize:12;color:modelData.level === 'info' ? Tokens.hudMuted : Tokens.hudAccent } }
        }
    }
}
