import QtQuick
import Quickshell
import ".."
import "../theme"
Item {
    id:root
    property bool technical:false
    property bool minimal:false
    // Dense: one short card for small logical viewports; class and size share a row.
    property bool dense:false
    readonly property bool compact:height<100
    readonly property int pad:dense ? 9 : 12
    readonly property var selected:HudData.placement.app
    // Measured separately: binding the size label to its own implicitWidth loops.
    TextMetrics { id:sizeMetrics; font:sizeText.font; text:sizeText.text }
    Rectangle { anchors.fill:parent; color:Qt.rgba(Tokens.hudScrim.r,Tokens.hudScrim.g,Tokens.hudScrim.b,.78); border.color:root.technical ? Tokens.hudAccent : 'transparent' }
    Rectangle { width:2; height:parent.height; color:Tokens.hudAccent }
    HudText { objectName:'hudPlacementQueue'; x:root.pad;y:root.dense ? 2 : 5;width:parent.width-2*root.pad; text:HudData.placement.count>0 ? (HudData.placement.index>=0 ? HudData.placement.index+1 : '—')+' / '+HudData.placement.count+' IN POCKET' : 'WINDOW PLACEMENT · POCKET EMPTY'; font.pixelSize:root.compact ? 10 : 12; color:Tokens.hudAccent }
    Image { x:root.pad;y:root.dense ? 20 : 31;width:root.dense ? 18 : root.compact ? 25 : 32;height:width; visible:!!root.selected; source:root.selected ? Quickshell.iconPath(root.selected.icon || '', 'application-x-executable') : ''; fillMode:Image.PreserveAspectFit }
    HudText { objectName:'hudPlacementTitle'; x:root.selected ? (root.dense ? 33 : 55) : root.pad;y:root.dense ? 15 : 28;width:parent.width-x-root.pad; text:root.selected ? root.selected.title || 'Untitled window' : 'Pocket empty'; font.pixelSize:root.dense ? 14 : root.compact ? 15 : 20 }
    HudText { objectName:'hudPlacementClass'; x:root.selected ? (root.dense ? 33 : 55) : root.pad;y:root.dense ? 36 : root.compact ? 48 : 56;width:parent.width-x-root.pad-(root.dense && sizeText.text ? sizeText.width+6 : 0); text:root.selected ? root.selected.appClass : 'Aim at a window to pocket it'; font.pixelSize:11;color:Tokens.hudMuted }
    HudText { id:sizeText; objectName:'hudPlacementSize'; x:root.dense ? parent.width-width-root.pad : root.compact ? 55 : 12;y:root.dense ? 37 : root.compact ? 65 : 84;width:root.dense ? Math.ceil(sizeMetrics.advanceWidth)+rightPadding+2 : parent.width-(root.compact ? 67 : 24); text:HudData.placement.size ? HudData.placement.size[0]+'×'+HudData.placement.size[1]+' client' : ''; font.pixelSize:root.dense ? 10 : 12;font.family:Tokens.mono;color:Tokens.hudMuted }
}
