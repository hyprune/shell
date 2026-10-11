import ".."
import "../theme"
import QtQuick
import "../Quests.js" as Quests
Item {
    id: root
    readonly property real holdProgress: holdRing.progress
    readonly property bool holdFilling: holdRing.filling
    readonly property bool minimal: Tokens.hudConcept === 'Minimal'
    readonly property bool technical: Tokens.hudConcept === 'Instrument'
    readonly property bool compact: width < 1200 || height < 700
    readonly property real inset: compact ? 26 : 56
    // Short logical viewports (1080p @ 2x, 1440p @ 2x) stack the Placement deck tightly.
    readonly property bool denseDeck: compact || height < 800
    readonly property string mode: HudData.freeCursor ? 'cursor' : HudData.editor ? HudData.editor.mode : 'world'
    property string contrastProbe: 'normal'
    Rectangle {
        // Mask only the measured labels; nearby zone text must not enter it.
        z: root.contrastProbe === 'mask' ? 1 : -1000; anchors.fill: parent
        visible: root.contrastProbe === 'mask' || root.contrastProbe.indexOf('white') === 0
        color: root.contrastProbe === 'mask' ? '#000000' : '#ffffff'
    }
    Item {
        z:2
        x: root.inset; y: root.inset; width: root.compact ? 126 : root.minimal ? 116 : root.technical ? 190 : 178; height: width+26
        HudCluster {
            width:parent.width; height:width; edgeX:-1; edgeY:-1
            Radar { id:localRadar; anchors.fill:parent; visible:root.contrastProbe !== 'mask' }
        }
        // Small captions stay upright while the radar retains its glass plane.
        HudStatusText { objectName:'hudRadarCaption'; probeMode:root.contrastProbe; anchors.bottom:parent.bottom; width:parent.width; text: root.technical ? Math.round(ShellState.heading)+'° / '+Math.round(localRadar.range)+' m' : ShellState.worldName.toUpperCase(); font.pixelSize:12; font.letterSpacing:1 }
    }
    HudCluster {
        anchors.horizontalCenter:parent.horizontalCenter; y: root.inset; width: Math.min(510,root.width*.38); height:70; edgeY:-1
        Compass { anchors.fill:parent }
    }
    HudCluster {
        z:2
        anchors.right:parent.right; anchors.rightMargin:root.inset-24; y:root.inset-24; width: (root.compact ? 230 : 310)+48; height:120
        edgeX:1; edgeY:-1
        curvatureScale: .35
        // Rasterise this small text cluster before projecting it, at twice its
        // physical output size (including the HUD's own scale on large screens).
        layer.enabled: bend > 0
        layer.textureSize: Qt.size(Math.ceil(width*2*root.scale*Screen.devicePixelRatio), Math.ceil(height*2*root.scale*Screen.devicePixelRatio))
        layer.smooth: true
        layer.mipmap: true
        Item { x:24; y:24; width:parent.width-48; height:72
            HudStatusText { objectName:'hudNavigation'; probeMode:root.contrastProbe; width:parent.width; horizontalAlignment:Text.AlignRight; text: root.mode === 'world' ? 'NAVIGATION' : root.mode.toUpperCase(); font.pixelSize: root.technical ? 17 : 14; font.letterSpacing:2 }
            HudStatusText { objectName:'hudInputStatus'; probeMode:root.contrastProbe; y:29; width:parent.width; horizontalAlignment:Text.AlignRight; text: HudData.freeCursor ? 'NATIVE POINTER' : root.technical ? ShellState.pose.map(v=>v.toFixed(1)).join(' / ')+' m' : root.mode === 'world' ? 'WORLD RECEIVES INPUT' : 'SUPER+TAB · RETURN'; font.pixelSize:12; font.family:root.technical ? Tokens.mono : Tokens.sans }
            HudStatusText { y:49; probeMode:root.contrastProbe; width:parent.width; horizontalAlignment:Text.AlignRight; visible:root.technical; text:HudData.stats; font.pixelSize:12 }
        }
    }
    // RFC-0012 (IPC 0.21): quest tracker, focus timer chip and toasts under the status.
    HudCluster {
        objectName: 'hudQuestColumn'
        z: 2
        anchors.right: parent.right; anchors.rightMargin: root.inset
        y: root.inset + (root.technical ? 92 : 84)
        width: root.compact ? 236 : 300; height: questColumn.height
        edgeX: 1; edgeY: -.6
        curvatureScale: .35
        shown: questColumn.height > 0
        Column {
            id: questColumn
            width: parent.width
            spacing: 10
            QuestTracker { width: parent.width; height: implicitHeight }
            FocusChip { anchors.right: parent.right; width: Math.min(parent.width, implicitWidth); height: implicitHeight; visible: Quests.chipVisible(ShellState.focusState, true, null) }
            QuestToast { width: parent.width; height: implicitHeight; toast: ShellState.toasts.length ? ShellState.toasts[0] : null }
        }
    }
    QuestToast {
        objectName: 'hudQuestBanner'
        banner: true
        anchors.horizontalCenter: parent.horizontalCenter
        y: root.inset + 84
        width: Math.min(520, root.width * .6); height: implicitHeight
        toast: ShellState.banners.length ? ShellState.banners[0] : null
    }
    HudCluster {
        id: deck; objectName: 'hudToolDeck'
        x:root.inset; y:root.height-height-root.inset-46
        width: Math.min(root.width*(toolDeck.dense ? .44 : .55),root.minimal ? 460 : root.technical ? 620 : 590); height: toolDeck.implicitHeight
        edgeX:-1; edgeY:1
        ToolDeck { id:toolDeck; anchors.fill:parent; compact:root.compact; dense:HudData.placing && root.denseDeck }
    }
    HudCluster {
        x:root.inset; y:deck.y-height-30; width:Math.min(640,root.width*.65); height:zoneColumn.height
        edgeX:-1; edgeY:.5; shown:ShellState.zone !== '' && (!root.compact || deck.y-zoneColumn.height-30>root.inset+172)
        Column { id:zoneColumn; width:parent.width; spacing:12
            HudText { smallText:false; width:parent.width; text:ShellState.zone.toUpperCase(); font.pixelSize:root.compact ? 25 : 35; font.letterSpacing:5; maximumLineCount:root.compact ? 1 : 2; wrapMode:root.compact ? Text.NoWrap : Text.Wrap }
            HudText { width:parent.width; text:ShellState.zoneSubtitle.toUpperCase(); font.pixelSize:12; font.letterSpacing:3; color:Tokens.hudMuted }
        }
    }
    HudCluster {
        x:root.inset; y:root.height-root.inset-36; width:Math.min(680,root.width-root.inset*2); height:36; edgeX:-1;edgeY:1
        HoldRing { id:holdRing; width:32;height:32; visible:HudData.worldPrompts }
        HudText { objectName:'hudWorldHints'; visible:HudData.worldPrompts; x:44;y:9;width:parent.width-x;text:(ShellState.markersState ? 'TAP · MARKERS    ' : '')+(root.minimal || HudData.climbing ? 'HOLD · DIRECTOR' : 'HOLD · DIRECTOR    E · USE    F · FOCUS    Q · SCOPE'); font.pixelSize:12; font.letterSpacing:.5; color:Tokens.hudMuted }
        HudModeChip { objectName:'hudCursorChip'; visible:HudData.freeCursor; width:Math.min(parent.width,implicitWidth); height:36 }
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
