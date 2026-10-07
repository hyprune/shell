import ".."
import "../theme"
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

RowLayout {
    spacing: 56

    ColumnLayout {
        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: 20

        HudLabel {
            text: 'A desktop worth exploring.'
            font.pixelSize: 36
            font.weight: Font.Light
        }

        HudLabel {
            text: 'M0  /  FIRST SIGNAL'
            color: Tokens.gold
            font.pixelSize: 11
            font.letterSpacing: 2
        }

        HudLabel {
            text: 'A small shell. A shared contract.\nRoom for another way to work.'
            font.pixelSize: 23
            color: Tokens.muted
            lineHeight: 1.6
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }

        Item {
            Layout.fillHeight: true
        }

        HudLabel {
            text: 'HYPRUNE    •    OCTOBER 2026'
            font.family: Tokens.mono
            font.pixelSize: 11
            color: Tokens.accent
            font.letterSpacing: 1.5
        }

        HudLabel {
            text: 'Original interface and schematic graphics. MIT licensed.\nBuilt for alternative shells to have equal footing.'
            font.pixelSize: 12
            color: Tokens.muted
            lineHeight: 1.7
        }

    }

    ColumnLayout {
        Layout.preferredWidth: 550
        Layout.minimumWidth: 550
        Layout.maximumWidth: 550
        Layout.fillHeight: true
        spacing: 30

        Repeater {
            model: [['01', 'A continuous signal', 'Framed IPC, atomic snapshots, revision-safe deltas and a fresh connection after failure.'], ['02', 'Your monitor, your input', 'Connection-owned output leases. Pointer input belongs to the world until the overview is accepted by core.'], ['03', 'An open design language', 'A compass, a local chart and quiet notices. Shared tokens and small components make another look possible.'], ['04', 'A jump to somewhere new', 'A destination card, star streaks and confirmed arrival. Preview runs against the mock; native travel uses the new 0.2 contract.']]

            delegate: RowLayout {
                required property var modelData

                Layout.fillWidth: true
                spacing: 24

                HudLabel {
                    text: modelData[0]
                    font.family: Tokens.mono
                    font.pixelSize: 24
                    color: Tokens.accent
                    Layout.alignment: Qt.AlignTop
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 9

                    HudLabel {
                        text: modelData[1]
                        font.pixelSize: 20
                    }

                    HudLabel {
                        text: modelData[2]
                        font.pixelSize: 14
                        color: Tokens.muted
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        lineHeight: 1.5
                    }

                }

            }

        }

        Item {
            Layout.fillHeight: true
        }

    }

}
