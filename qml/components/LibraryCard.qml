import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../Library.js" as Library

// Director > Library > Browse: one index entry (RFC-0015, `hyprune browse --json`). The verified
// cached thumbnail (or a placeholder), name, creator, type, the source label as the CLI words
// it, the declared licence with its source-kind wording, download size, and badges for
// installed, update available and "needs a newer Hyprune". All entry text is plain text.
Rectangle {
    id: card
    property var entry: null
    property bool current: false
    property bool compact: false
    signal act()
    signal picked()
    readonly property var action: Library.entryAction(entry)
    readonly property string tier: Library.tierOf(entry)
    readonly property real dim: action.kind === 'unavailable' ? 0.55 : 1
    objectName: 'libraryCard:' + (entry ? entry.sourceId + '/' + entry.id : '')
    color: current ? Tokens.raised : Tokens.panel
    radius: Tokens.radius
    border.color: current ? Tokens.gold : Tokens.line
    border.width: current ? 2 : 1
    Accessible.role: Accessible.ListItem
    Accessible.name: entry ? entry.name : ''
    Accessible.description: entry ? Library.tierLabel(entry) + ' · ' + Library.typeLabel(entry.type) + ' · ' + Library.entryBadges(entry).map(b => b.label).join(' · ') : ''

    TapHandler { onTapped: card.picked(); onDoubleTapped: { card.picked(); if (card.action.enabled) card.act(); } }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: card.compact ? 4 : 6

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: card.compact ? 72 : 124
            Rectangle { anchors.fill: parent; radius: 2; color: Tokens.ink; opacity: Tokens.light ? .55 : .7 }
            Image {
                id: thumbnail
                objectName: 'libraryThumbnail'
                anchors.fill: parent
                anchors.margins: 2
                opacity: card.dim
                asynchronous: true
                fillMode: Image.PreserveAspectCrop
                clip: true
                sourceSize.width: Math.ceil(width * Screen.devicePixelRatio)
                sourceSize.height: Math.ceil(height * Screen.devicePixelRatio)
                // Only the CLI's verified cache path, never a URL from the index.
                source: card.entry && card.entry.thumbnail && String(card.entry.thumbnail).charAt(0) === '/' ? 'file://' + card.entry.thumbnail : ''
                visible: status === Image.Ready
            }
            CubeGlyph {
                anchors.centerIn: parent
                width: parent.height * .45; height: width
                visible: thumbnail.status !== Image.Ready && card.entry && card.entry.type === 'library'
                opacity: card.dim
                tint: Tokens.muted
                stroke: 1.4
            }
            HudLabel {
                anchors.centerIn: parent
                visible: thumbnail.status !== Image.Ready && !(card.entry && card.entry.type === 'library')
                text: '◍'
                color: Tokens.muted
                opacity: card.dim
                font.pixelSize: parent.height * .4
            }
            Rectangle {
                objectName: 'libraryTier'
                x: 6; y: 6
                width: Math.min(parent.width - 12, tierText.implicitWidth + 4); height: 20
                radius: 2
                color: card.tier === 'official' ? Tokens.accent : card.tier === 'community' ? (Tokens.light ? Tokens.mission : Tokens.violet) : Tokens.gold
                HudLabel {
                    id: tierText
                    anchors.fill: parent
                    leftPadding: 6; rightPadding: 6
                    verticalAlignment: Text.AlignVCenter
                    text: Library.tierLabel(card.entry)
                    font.pixelSize: 10; font.letterSpacing: 0.6; font.weight: Font.DemiBold
                    color: Tokens.ink
                }
            }
            Rectangle {
                anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 6
                width: typeText.implicitWidth + 4; height: 18
                radius: 2
                color: Tokens.panel
                border.color: Tokens.line
                HudLabel {
                    id: typeText
                    anchors.centerIn: parent
                    leftPadding: 6; rightPadding: 6
                    text: card.entry ? Library.typeLabel(card.entry.type).toUpperCase() : ''
                    font.pixelSize: 9; font.letterSpacing: 1.2
                    color: Tokens.text
                }
            }
        }

        HudLabel {
            objectName: 'libraryName'
            Layout.fillWidth: true
            text: card.entry ? card.entry.name : ''
            font.pixelSize: card.compact ? 14 : 16
            opacity: card.dim
        }

        HudLabel {
            Layout.fillWidth: true
            text: card.entry ? [card.entry.creator ? 'by ' + card.entry.creator : '', card.entry.latest ? card.entry.latest.tag : ''].filter(v => v).join('  ·  ') : ''
            font.pixelSize: 12
            color: Tokens.muted
            opacity: card.dim
        }

        HudLabel {
            objectName: 'libraryLicence'
            Layout.fillWidth: true
            Layout.preferredHeight: 30
            text: card.entry ? Library.licenceText(card.entry.latest ? card.entry.latest.license : '', card.entry.licenceNote) : ''
            // The source-kind wording is part of the licence: two lines rather than elided.
            wrapMode: Text.Wrap
            maximumLineCount: 2
            font.pixelSize: 11
            color: Tokens.muted
            opacity: card.dim
        }

        HudLabel {
            objectName: 'librarySize'
            Layout.fillWidth: true
            text: card.entry && card.entry.latest && card.entry.latest.bytes ? Library.sizeText(card.entry.latest.bytes) + ' download' : ''
            font.family: Tokens.mono; font.pixelSize: 11
            color: Tokens.muted
            opacity: card.dim
        }

        Flow {
            Layout.fillWidth: true
            Layout.preferredHeight: 20
            clip: true
            spacing: 5
            Repeater {
                model: Library.entryBadges(card.entry)
                delegate: Rectangle {
                    required property var modelData
                    objectName: 'libraryBadge:' + modelData.id
                    height: 20
                    width: Math.min(card.width - 24, badgeLabel.implicitWidth)
                    radius: 2
                    color: 'transparent'
                    border.color: modelData.tone === 'warning' ? Tokens.warning : modelData.tone === 'positive' ? Tokens.positive : Tokens.accent
                    HudLabel {
                        id: badgeLabel
                        anchors.fill: parent
                        leftPadding: 7; rightPadding: 7
                        verticalAlignment: Text.AlignVCenter
                        text: parent.modelData.label
                        font.pixelSize: 10; font.letterSpacing: 0.4
                        color: parent.modelData.tone === 'warning' ? Tokens.warning : parent.modelData.tone === 'positive' ? Tokens.positive : Tokens.accent
                    }
                }
            }
        }

        Item { Layout.fillWidth: true; Layout.fillHeight: true }

        ActionButton {
            objectName: 'libraryAct:' + (card.entry ? card.entry.sourceId + '/' + card.entry.id : '')
            Accessible.name: card.entry ? card.action.label + ' ' + card.entry.name : card.action.label
            Layout.fillWidth: true
            implicitHeight: card.compact ? 32 : 38
            text: card.action.label
            primary: card.current && card.action.enabled
            enabled: card.action.enabled && !ShellState.libraryBusy
            onClicked: card.act()
        }
    }
}
