import ".."
import "../theme"
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    readonly property var tabs: ['Map', 'Quests', 'Objects', 'Places', 'Surfaces', 'Workspaces', 'Help', "What's new", "Settings", "Performance"]

    focus: true
    Keys.onEscapePressed: ShellState.close()
    Keys.onLeftPressed: ShellState.tab = Math.max(0, ShellState.tab - 1)
    Keys.onRightPressed: ShellState.tab = Math.min(root.tabs.length - 1, ShellState.tab + 1)

    Constellation {
        anchors.fill: parent
        opacity: 0.65
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: root.width < 1100 ? 16 : 28
        spacing: root.height < 700 ? 12 : 24

        RowLayout {
            Layout.fillWidth: true

            // Placeholder of zero height so the mark never drives the row height.
            // The ink, not the box, starts on the content edge and spans from the
            // caption's cap height to the world name's baseline; the rest of the
            // box is the master's own clear space.
            Item {
                id: headerMarkSlot
                Layout.preferredHeight: 0
                Layout.alignment: Qt.AlignTop
                Layout.preferredWidth: headerMark.size - headerMark.inkLeft - headerMark.inkRight + 16
                TextMetrics { id: captionCap; font: headerCaption.font; text: 'H' }
                BrandMark {
                    id: headerMark
                    objectName: 'brandMark:director'
                    readonly property real inkStart: headerTitle.y + headerCaption.y + headerCaption.baselineOffset - captionCap.tightBoundingRect.height
                    readonly property real inkEnd: headerTitle.y + headerName.y + headerName.baselineOffset
                    size: Math.round(sizeForInkHeight(inkEnd - inkStart))
                    color: Tokens.accent
                    x: -inkLeft
                    y: inkStart - inkTop - headerMarkSlot.y
                }
            }

            ColumnLayout {
                id: headerTitle
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                spacing: 8

                HudLabel {
                    id: headerCaption
                    Layout.fillWidth: true
                    text: 'HYPRUNE / OVERVIEW'
                    color: Tokens.accent
                    font.pixelSize: 12
                    font.letterSpacing: 1.8
                }

                HudLabel {
                    id: headerName
                    Layout.fillWidth: true
                    text: ShellState.worldName.toUpperCase()
                    font.pixelSize: root.width < 1100 ? 24 : 34
                    font.weight: Font.Light
                    font.letterSpacing: 5
                }

            }

            Item {
                Layout.fillWidth: true
            }

            ColumnLayout {
                visible: root.width >= 1200
                Layout.maximumWidth: 220
                spacing: 7

                HudLabel {
                    text: '●  SHELL RECEIVES INPUT'
                    color: Tokens.accent
                    font.family: Tokens.mono
                    font.pixelSize: 11
                }

                HudLabel {
                    text: ShellState.output + '   /   LIVE'
                    color: Tokens.muted
                    font.family: Tokens.mono
                    font.pixelSize: 11
                    Layout.alignment: Qt.AlignRight
                }

            }

            ActionButton {
                text: 'Return to desktop ↗'
                enabled: ShellState.available('runtime.exit')
                onClicked: ShellState.action('runtime.exit', {
                })
            }

            ActionButton {
                text: 'Close  ·  Esc'
                onClicked: ShellState.close()
            }

        }

        RowLayout {
            spacing: 8
            Layout.fillWidth: true

            Repeater {
                model: root.tabs

                delegate: Button {
                    id: tabButton

                    required property string modelData
                    required property int index

                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    Layout.preferredWidth: 1
                    implicitHeight: 44
                    leftPadding: 6; rightPadding: 6
                    ToolTip.visible: hovered && contentItem.truncated
                    ToolTip.text: modelData
                    ToolTip.delay: 500
                    onClicked: ShellState.tab = index

                    contentItem: HudLabel {
                        text: tabButton.modelData.toUpperCase()
                        font.pixelSize: 13
                        font.letterSpacing: root.width < 1100 ? 0.5 : 2
                        color: ShellState.tab === tabButton.index ? Tokens.text : Tokens.muted
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }

                    background: Item {
                        Rectangle {
                            anchors.bottom: parent.bottom
                            width: parent.width
                            height: 2
                            color: Tokens.accent
                            visible: ShellState.tab === tabButton.index
                        }

                        Rectangle {
                            anchors.fill: parent
                            color: 'transparent'
                            border.color: tabButton.activeFocus ? Tokens.gold : 'transparent'
                            border.width: 1
                        }

                    }

                }

            }

            Item {
                Layout.fillWidth: true
            }

            HudLabel {
                visible: root.width >= 1100
                text: ('0' + (ShellState.tab + 1)).slice(-2) + ' / ' + ('0' + root.tabs.length).slice(-2)
                font.family: Tokens.mono
                color: Tokens.muted
                font.pixelSize: 12
            }

        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Tokens.line
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            // Concrete page geometry avoids Qt 6.11 StackLayout's recursive
            // size-hint cache walking Repeater-owned/deleted layout children.
            DirectorMap { anchors.fill: parent; visible: ShellState.tab === ShellState.tabMap }
            DirectorQuests { anchors.fill: parent; visible: ShellState.tab === ShellState.tabQuests }
            DirectorObjects { anchors.fill: parent; visible: ShellState.tab === ShellState.tabObjects }
            DirectorPlaces { anchors.fill: parent; visible: ShellState.tab === 3 }
            DirectorSurfaces { anchors.fill: parent; visible: ShellState.tab === 4 }
            DirectorWorkspaces { anchors.fill: parent; visible: ShellState.tab === 5 }
            DirectorHelp { anchors.fill: parent; visible: ShellState.tab === 6 }
            DirectorNews { anchors.fill: parent; visible: ShellState.tab === 7 }
            DirectorPerformance { anchors.fill: parent; visible: ShellState.tab === ShellState.tabPerformance }
            DirectorSettings { anchors.fill: parent; visible: ShellState.tab === ShellState.tabSettings }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Tokens.line
        }

        RowLayout {
            Layout.fillWidth: true

            HudLabel {
                Layout.fillWidth: true
                text: ShellState.presentation.dev ? 'MOCK SESSION  /  ' + ShellState.protocol + '  /  PRESENTATION PREVIEW' : 'WORLD SESSION'
                font.family: Tokens.mono
                font.pixelSize: 10
                color: Tokens.muted
                font.letterSpacing: 1
            }

            Item {
                Layout.fillWidth: true
            }

            HudLabel {
                text: ShellState.tab === ShellState.tabQuests && ShellState.questsSupported
                      ? '↑ ↓  Move    Enter  Open    T  Track    Space  Done    F  Focus    N  New    ← →  Views    Esc  Close'
                      : ShellState.tab === ShellState.tabObjects && ShellState.objectsSupported
                      ? (ShellState.objectsView === 'placed' ? '↑ ↓  Move    Enter  Edit    L  Lock    H  Hide    R  Reset    Del  Remove    V  View    Esc  Close'
                                                              : '↑ ↓  Move    Enter  Add    /  Search    V  Placed    ← →  Views    Esc  Close')
                      : '← →  Views      Tab  Focus      Esc  Close'
                font.family: Tokens.mono
                font.pixelSize: 11
                color: Tokens.muted
            }

        }

    }

    Rectangle {
        anchors.top: parent.top
        anchors.left: parent.left
        width: 80
        height: 3
        color: Tokens.accent
    }

}
