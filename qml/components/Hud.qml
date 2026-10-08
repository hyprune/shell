import ".."
import "../theme"
import QtQuick

Item {
    id: root
    readonly property real inset: width < 1200 ? 30 : 54
    readonly property bool compact: width < 1200 || height < 700
    readonly property color foreground: '#f1f4fb'
    readonly property color secondary: '#bbcce0'
    readonly property var editor: ShellState.state ? ShellState.state.editor : null
    readonly property var interaction: ShellState.state ? ShellState.state.interaction : null
    readonly property string mode: editor ? editor.mode : interaction ? interaction.mode : 'world'

    HudCluster {
        x: root.inset; y: root.inset
        width: root.compact ? 160 : 210
        height: width + 28
        edgeX: -1; edgeY: -1
        MapView { width: parent.width; height: width; compact: true; clip: true; opacity: 0.9 }
        HudLabel {
            anchors.bottom: parent.bottom; width: parent.width
            text: ShellState.worldName.toUpperCase()
            color: root.foreground; font.pixelSize: 11; font.letterSpacing: 1
        }
    }
    HudCluster {
        anchors.top: parent.top; anchors.topMargin: root.inset
        anchors.horizontalCenter: parent.horizontalCenter
        width: Math.min(420, root.width - 670); height: 56
        visible: !root.compact && width >= 230
        edgeY: -1
        clip: true
        Repeater {
            model: 17
            delegate: Item {
                required property int index
                x: (index - 8) * 40 + parent.width / 2 - (ShellState.heading % 15) * 40 / 15
                width: 1; height: 24
                Rectangle { anchors.bottom: parent.bottom; width: 1; height: index % 3 === 0 ? 10 : 5; color: root.secondary }
                HudLabel {
                    anchors.horizontalCenter: parent.horizontalCenter; y: 32
                    text: { var d = (Math.floor(ShellState.heading / 15) * 15 + (index - 8) * 15 + 720) % 360; return d % 90 === 0 ? ['N', 'E', 'S', 'W'][d / 90] : d.toString(); }
                    color: root.secondary; font.pixelSize: 10
                }
            }
        }
        HudLabel { anchors.horizontalCenter: parent.horizontalCenter; text: Math.round(ShellState.heading) + '°'; color: root.foreground; font.pixelSize: 11 }
    }
    HudCluster {
        anchors.right: parent.right; anchors.rightMargin: root.inset
        y: root.inset
        width: root.compact ? 300 : 340; height: statusColumn.height
        edgeX: 1; edgeY: -1
        Column {
            id: statusColumn
            width: parent.width; spacing: 8
            HudLabel {
                width: parent.width
                text: ({world:'NAVIGATION',movement:'NAVIGATION',interactive:'APPLICATION INPUT',typing:'APPLICATION INPUT',focus:'FULLSCREEN',fullscreen:'FULLSCREEN',menu:'DIRECTOR'})[root.mode] || root.mode.toUpperCase()
                font.pixelSize: 14; font.letterSpacing: 2; horizontalAlignment: Text.AlignRight; color: root.foreground
            }
            HudLabel {
                width: parent.width
                text: ['world','movement'].indexOf(root.mode) >= 0 ? 'WORLD RECEIVES INPUT' : 'SUPER+TAB / BACK · RETURN'
                font.pixelSize: 10; font.letterSpacing: 0.8; horizontalAlignment: Text.AlignRight; color: root.secondary
            }
        }
    }
    HudCluster {
        x: root.inset; y: root.compact ? 264 : 330
        width: Math.min(400, root.width * 0.32); height: 160
        visible: ShellState.presentation.dev === true && !root.compact
        edgeX: -1
        MissionPanel { width: parent.width }
    }
    // Legacy protocols may still supply screen-projected markers. Core 0.6
    // owns all world-locked markers; never curve those with the screen HUD.
    Repeater {
        model: ['0.6','0.7'].indexOf(ShellState.protocol) >= 0 ? [] : ShellState.markers
        delegate: Item {
            required property var modelData
            x: Math.max(8, Math.min(root.width - width - 8, root.width * modelData.x - width / 2))
            y: Math.max(8, Math.min(root.height - height - 8, root.height * modelData.y))
            width: 220; height: 76
            Seal { width: 30; height: 30; anchors.horizontalCenter: parent.horizontalCenter; tint: root.foreground }
            Rectangle { y: 36; width: parent.width; height: 40; radius: 3; color: '#da0a1420' }
            HudLabel { y: 40; width: parent.width - 12; anchors.horizontalCenter: parent.horizontalCenter; text: modelData.name; horizontalAlignment: Text.AlignHCenter; color: root.foreground; font.pixelSize: 11 }
            HudLabel { y: 58; width: parent.width; text: Math.round(modelData.distance) + ' m'; horizontalAlignment: Text.AlignHCenter; color: root.secondary; font.pixelSize: 10 }
        }
    }
    HudCluster {
        x: root.inset; y: root.height - height - (root.compact ? 160 : 210)
        width: Math.min(root.width * 0.56, 650); height: zoneColumn.height
        shown: ShellState.zone !== ''
        edgeX: -1; edgeY: 0.5
        Column {
            id: zoneColumn
            width: parent.width; spacing: 10
            HudLabel { width: parent.width; text: 'SECTOR DISCOVERED'; color: root.secondary; font.pixelSize: 10; font.letterSpacing: 2 }
            HudLabel { width: parent.width; text: ShellState.zone; color: root.foreground; font.pixelSize: root.compact ? 24 : 36; maximumLineCount: 2; wrapMode: Text.Wrap }
            HudLabel { width: parent.width; text: ShellState.zoneSubtitle; color: root.secondary; font.pixelSize: 11 }
        }
    }
    HudCluster {
        x: root.inset; y: root.height - height - root.inset
        width: Math.min(750, root.width - root.inset * 2); height: inputColumn.height
        edgeX: -0.8; edgeY: 1
        HoldRing { anchors.verticalCenter: parent.verticalCenter }
        Column {
            id: inputColumn
            x: 54; width: parent.width - x; spacing: 9
            HudLabel {
                width: parent.width; font.pixelSize: 11; color: root.foreground
                text: root.mode.toUpperCase() + (root.interaction && root.interaction.noclip ? '  /  NOCLIP' : '') + '  /  ' + ShellState.pose.map(v => v.toFixed(1)).join(' · ') + ' m'
            }
            HudLabel {
                visible: !!root.interaction
                width: parent.width; font.pixelSize: 11; color: root.foreground
                wrapMode: Text.Wrap; maximumLineCount: 2
                text: root.editor ? ['NORMAL','WINDOW','PATH','POSITION','RESERVED'].map((name,i) => (root.editor.tool === i+1 ? '▸ ' : '') + (i+1) + ' ' + name + (root.editor.tool === i+1 ? ' · ' + root.editor.submode.toUpperCase() : '')).join('   ') : root.interaction ? root.interaction.tools.map((name,i) => (root.interaction.tool === i+1 ? '▸ ' : '') + (i+1) + ' ' + name.toUpperCase()).join('   ') : ''
            }
            HudLabel {
                width: parent.width; font.pixelSize: 10; color: root.secondary
                wrapMode: Text.Wrap
                text: ['0.6','0.7'].indexOf(ShellState.protocol) >= 0 ? 'HOLD TAB · MAP   /   E · USE   /   F · FOCUS   /   Q · SCOPE   /   F12 · DESKTOP' : 'HOLD TAB · OVERVIEW   /   F12 · DESKTOP'
            }
        }
    }
    HudCluster {
        anchors.right: parent.right; anchors.rightMargin: root.inset
        y: root.compact ? root.inset + 90 : root.height - height - 170
        width: Math.min(360, root.width * 0.34); height: noticeColumn.height
        shown: ShellState.notices.length > 0
        edgeX: 1; edgeY: root.compact ? -0.5 : 0.6
        Column {
            id: noticeColumn
            width: parent.width; spacing: 12
            Repeater {
                model: ShellState.notices.slice(-3)
                HudLabel {
                    required property var modelData
                    width: parent.width; text: modelData.message
                    font.pixelSize: 12; wrapMode: Text.Wrap; maximumLineCount: 3
                    color: modelData.level === 'info' ? root.secondary : '#efd49f'
                }
            }
        }
    }
}
