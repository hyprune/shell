import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../Objects.js" as Objects
import "../Npcs.js" as Npcs

// Director > Objects > Catalog: one catalog entry (IPC 0.22 objects.catalog). Thumbnail
// (or a cube), name, source badge, size, trait chips and triangles; entries that can't be
// placed are dimmed with core's reason, invalid ones list their errors. Add pockets it.
// Characters (IPC 0.23) are never pocketed: Spawn opens the route step instead.
Rectangle {
    id: card
    property var entry: null
    property bool current: false
    property bool compact: false
    signal add()
    signal spawn()
    signal picked()
    readonly property bool addable: Objects.canAdd(entry)
    readonly property bool character: Npcs.isCharacter(entry)
    readonly property bool spawnable: Npcs.canSpawn(entry) && ShellState.npcsSupported
    readonly property var note: !character ? Objects.entryNote(entry) : spawnable ? {level: '', lines: []}
                              : {level: entry.state === 'invalid' ? 'error' : 'muted', lines: [ShellState.npcsSupported ? Npcs.spawnNote(entry) : 'Characters need core IPC 0.23.']}
    readonly property real dim: addable || spawnable ? 1 : 0.55
    objectName: 'objectCard:' + (entry ? entry.ref : '')
    color: current ? Tokens.raised : Tokens.panel
    radius: Tokens.radius
    border.color: current ? Tokens.gold : Tokens.line
    border.width: current ? 2 : 1
    Accessible.role: Accessible.ListItem
    Accessible.name: entry ? entry.name : ''
    Accessible.description: entry ? Objects.sourceLabel(entry.source) + (addable ? '' : ' · ' + card.note.lines.join(' ')) : ''

    TapHandler { onTapped: card.picked(); onDoubleTapped: { card.picked(); if (card.spawnable) card.spawn(); else if (card.addable) card.add(); } }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: card.compact ? 4 : 6

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: card.compact ? 64 : 112
            Rectangle { anchors.fill: parent; radius: 2; color: Tokens.ink; opacity: Tokens.light ? .55 : .7 }
            Image {
                id: thumbnail
                objectName: 'objectThumbnail'
                anchors.fill: parent
                anchors.margins: 6
                opacity: card.dim
                asynchronous: true
                fillMode: Image.PreserveAspectFit
                sourceSize.width: Math.ceil(width * Screen.devicePixelRatio)
                sourceSize.height: Math.ceil(height * Screen.devicePixelRatio)
                source: card.entry && card.entry.thumbnail ? 'file://' + card.entry.thumbnail : ''
                visible: status === Image.Ready
            }
            CubeGlyph {
                anchors.centerIn: parent
                width: parent.height * .5; height: width
                visible: thumbnail.status !== Image.Ready
                opacity: card.dim
                tint: Tokens.muted
                stroke: 1.4
            }
            Rectangle {
                x: 6; y: 6
                width: sourceText.implicitWidth + 4; height: 20
                radius: 2
                color: card.entry && card.entry.source === 'user' ? Tokens.gold : card.entry && card.entry.source === 'library' ? (Tokens.light ? Tokens.mission : Tokens.violet) : Tokens.accent
                HudLabel {
                    id: sourceText
                    objectName: 'objectSource'
                    anchors.centerIn: parent
                    leftPadding: 6; rightPadding: 6
                    text: card.entry ? Objects.sourceLabel(card.entry.source).toUpperCase() : ''
                    font.pixelSize: 10; font.letterSpacing: 1.2; font.weight: Font.DemiBold
                    color: Tokens.ink
                }
            }
        }

        HudLabel {
            objectName: 'objectName'
            Layout.fillWidth: true
            text: card.entry ? card.entry.name : ''
            font.pixelSize: card.compact ? 14 : 16
            opacity: card.dim
        }

        HudLabel {
            Layout.fillWidth: true
            text: card.entry ? [Objects.categoryLabel(card.entry.category), Objects.screenChip(card.entry), Objects.sizeText(card.entry.bounds)].filter(v => v).join('  ·  ') : ''
            font.pixelSize: 12
            color: Tokens.muted
            opacity: card.dim
        }

        HudLabel {
            objectName: 'objectCost'
            Layout.fillWidth: true
            text: card.entry ? Objects.costText(card.entry) : ''
            font.family: Tokens.mono; font.pixelSize: 11
            color: Tokens.muted
            opacity: card.dim
        }

        Flow {
            Layout.fillWidth: true
            Layout.preferredHeight: 22
            clip: true
            spacing: 5
            opacity: card.dim
            Repeater {
                model: card.entry ? Objects.traitChips(card.entry.traits) : []
                delegate: Rectangle {
                    required property var modelData
                    height: 22
                    width: Math.min(card.width - 24, chipLabel.implicitWidth)
                    radius: 11
                    color: 'transparent'
                    border.color: Tokens.line
                    HudLabel {
                        id: chipLabel
                        anchors.fill: parent
                        leftPadding: 8; rightPadding: 8
                        verticalAlignment: Text.AlignVCenter
                        text: parent.modelData.glyph + ' ' + parent.modelData.label
                        font.pixelSize: 11
                        color: Tokens.text
                    }
                }
            }
        }

        HudLabel {
            objectName: 'objectNote'
            Layout.fillWidth: true
            Layout.preferredHeight: card.compact ? 16 : 32
            visible: card.note.lines.length > 0
            text: card.note.lines.join('\n')
            wrapMode: Text.Wrap
            maximumLineCount: card.compact ? 1 : 2
            font.pixelSize: 11
            color: card.note.level === 'error' ? Tokens.warning : Tokens.muted
        }

        Item { Layout.fillWidth: true; Layout.fillHeight: true }

        ActionButton {
            objectName: 'objectSpawn:' + (card.entry ? card.entry.ref : '')
            Accessible.name: card.entry ? 'Spawn ' + card.entry.name : 'Spawn'
            visible: card.character
            Layout.fillWidth: true
            implicitHeight: card.compact ? 32 : 38
            text: card.spawnable ? 'Spawn' : card.entry && card.entry.state === 'invalid' ? 'Invalid' : 'Can\'t spawn'
            primary: card.current && card.spawnable
            enabled: card.spawnable && ShellState.objectsCan('npcs.spawn')
            onClicked: card.spawn()
        }

        ActionButton {
            objectName: 'objectRepair:' + (card.entry ? card.entry.ref : '')
            visible: !!card.entry && card.entry.state === 'invalid' && /^(user|world)\//.test(card.entry.ref)
            Layout.fillWidth: true
            implicitHeight: card.compact ? 32 : 38
            text: ShellState.objectEditBusy && ShellState.objectEditJob.kind === 'repair' ? 'Repairing…' : 'Repair'
            enabled: !ShellState.objectEditBusy
            onClicked: ShellState.objectEditRun('repair', card.entry.ref)
        }
        ActionButton {
            visible: !card.character
            objectName: 'objectAdd:' + (card.entry ? card.entry.ref : '')
            Accessible.name: card.entry ? 'Add ' + card.entry.name + ' to the pocket' : 'Add'
            Layout.fillWidth: true
            implicitHeight: card.compact ? 32 : 38
            text: card.addable ? 'Add to pocket' : card.entry && card.entry.state === 'invalid' ? 'Invalid' : 'Can\'t place'
            primary: card.current && card.addable
            enabled: card.addable && ShellState.objectsCan('objects.pocket')
            onClicked: card.add()
        }
    }
}
