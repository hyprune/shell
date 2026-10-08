import ".."
import "../theme"
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Flickable {
    clip: true
    ScrollBar.vertical: ScrollBar {}
    boundsBehavior: Flickable.StopAtBounds
    contentWidth: width
    contentHeight: surfaceColumn.height

    Column {
        id: surfaceColumn

        width: parent.width
        spacing: 24

        HudLabel {
            width: parent.width
            wrapMode: Text.Wrap
            text: 'Windows, with a place in the world'
            font.pixelSize: 30
            font.weight: Font.Light
        }

        HudLabel {
            width: parent.width
            wrapMode: Text.Wrap
            text: 'Choose a surface to request keyboard focus. Core decides whether it can safely activate it.'
            color: Tokens.muted
            font.pixelSize: 14
        }

        ActionButton {
            text: 'Recall all windows ↗'
            enabled: ShellState.available('surfaces.recall')
            onClicked: ShellState.action('surfaces.recall', {})
        }

        GridLayout {
            width: parent.width
            columns: Math.max(1, Math.floor((width + 20) / 390))
            columnSpacing: 20
            rowSpacing: 20

            Repeater {
                model: ShellState.surfaces.filter((s) => {
                    return s.kind !== 'workspace';
                })

                delegate: SurfaceCard {
                    required property var modelData

                    surface: modelData
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    Layout.preferredWidth: 1
                    Layout.alignment: Qt.AlignTop
                }

            }

        }

        HudLabel {
            visible: !ShellState.surfaces.length
            text: 'No live surfaces in this session.'
            color: Tokens.muted
        }

    }

}
