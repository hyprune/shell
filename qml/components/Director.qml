import ".."
import "../theme"
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    readonly property var tabs: ['Map', 'Places', 'Surfaces', 'Workspaces', 'Help', "What's new", "Settings"]

    focus: true
    Keys.onEscapePressed: ShellState.close()
    Keys.onLeftPressed: ShellState.tab = Math.max(0, ShellState.tab - 1)
    Keys.onRightPressed: ShellState.tab = Math.min(6, ShellState.tab + 1)

    Constellation {
        anchors.fill: parent
        opacity: 0.65
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 36
        spacing: 24

        RowLayout {
            Layout.fillWidth: true

            ColumnLayout {
                spacing: 10

                HudLabel {
                    text: 'H Y P R U N E   /   O V E R V I E W'
                    color: Tokens.accent
                    font.pixelSize: 12
                    font.letterSpacing: 1.8
                }

                HudLabel {
                    text: ShellState.worldName.toUpperCase()
                    font.pixelSize: 34
                    font.weight: Font.Light
                    font.letterSpacing: 5
                }

            }

            Item {
                Layout.fillWidth: true
            }

            ColumnLayout {
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

                    implicitWidth: Math.max(150, contentItem.implicitWidth + 36)
                    implicitHeight: 50
                    onClicked: ShellState.tab = index

                    contentItem: HudLabel {
                        text: tabButton.modelData.toUpperCase()
                        font.pixelSize: 13
                        font.letterSpacing: 3
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
                text: '0' + (ShellState.tab + 1) + ' / 07'
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

        StackLayout {
            currentIndex: ShellState.tab
            Layout.fillWidth: true
            Layout.fillHeight: true

            DirectorMap {
            }

            DirectorPlaces {
            }

            DirectorSurfaces {
            }

            DirectorWorkspaces {
            }

            DirectorHelp {
            }

            DirectorNews {
            }
            DirectorSettings {}

        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Tokens.line
        }

        RowLayout {
            Layout.fillWidth: true

            HudLabel {
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
                text: '← →  Views      Tab  Focus      Esc  Close'
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
