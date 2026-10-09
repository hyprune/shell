import QtQuick
import Quickshell
import ".."
import "../theme"
Item {
    id:root
    property bool technical:false
    property bool minimal:false
    readonly property bool compact:height<100
    readonly property var selected:HudData.placement.app
    Rectangle { anchors.fill:parent; color:Qt.rgba(Tokens.hudScrim.r,Tokens.hudScrim.g,Tokens.hudScrim.b,.78); border.color:root.technical ? Tokens.hudAccent : 'transparent' }
    Rectangle { width:2; height:parent.height; color:Tokens.hudAccent }
    HudText { objectName:'hudPlacementQueue'; x:12;y:5;width:parent.width-24; text:HudData.placement.count>0 ? (HudData.placement.index>=0 ? HudData.placement.index+1 : '—')+' / '+HudData.placement.count+' IN POCKET' : 'WINDOW PLACEMENT · POCKET EMPTY'; font.pixelSize:root.compact ? 10 : 12; color:Tokens.hudAccent }
    Image { x:12;y:31;width:root.compact ? 25 : 32;height:width; visible:!!root.selected; source:root.selected ? Quickshell.iconPath(root.selected.icon || '', 'application-x-executable') : ''; fillMode:Image.PreserveAspectFit }
    HudText { objectName:'hudPlacementTitle'; x:root.selected ? 55 : 12;y:28;width:parent.width-x-12; text:root.selected ? root.selected.title || 'Untitled window' : 'Pocket empty'; font.pixelSize:root.compact ? 15 : 20 }
    HudText { objectName:'hudPlacementClass'; x:root.selected ? 55 : 12;y:root.compact ? 48 : 56;width:parent.width-x-12; text:root.selected ? root.selected.appClass : 'Aim at a window to pocket it'; font.pixelSize:11;color:Tokens.hudMuted }
    HudText { objectName:'hudPlacementSize'; x:root.compact ? 55 : 12;y:root.compact ? 65 : 84;width:parent.width-x-12; text:HudData.placement.size ? HudData.placement.size[0]+'×'+HudData.placement.size[1]+' client' : ''; font.pixelSize:12;font.family:Tokens.mono;color:Tokens.hudMuted }
}
