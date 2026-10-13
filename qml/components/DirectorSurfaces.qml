import ".."
import "../theme"
import "../DirectorModel.js" as Model
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Flickable {
    id: page
    objectName: 'directorSurfaces'
    clip: true
    ScrollBar.vertical: ScrollBar {}
    boundsBehavior: Flickable.StopAtBounds
    contentWidth: width
    contentHeight: surfaceColumn.height

    // Pocketed windows (IPC 0.20 editor.unplaced) first, then windows placed in the world.
    // Rebuilt only when the cards change, not on every snapshot (keeps hover and focus).
    property var cards: ({pocketed: [], placed: []})
    function refresh() {
        var next = Model.surfaceCards(ShellState.state);
        if (JSON.stringify(next) !== JSON.stringify(cards)) cards = next;
    }
    Component.onCompleted: refresh()
    Connections { target: ShellState; function onStateChanged() { page.refresh(); } }
    readonly property int columns: Math.max(1, Math.floor((width + 20) / 520))

    component CardGrid: GridLayout {
        property alias model: cardRepeater.model
        Layout.fillWidth: true
        columnSpacing: 20
        rowSpacing: 20

        Repeater {
            id: cardRepeater

            delegate: SurfaceCard {
                required property var modelData

                surface: modelData
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.preferredWidth: 1
                Layout.maximumWidth: 760
                Layout.alignment: Qt.AlignTop
            }
        }
    }

    component SectionLabel: HudLabel {
        Layout.fillWidth: true
        font.family: Tokens.mono
        font.pixelSize: 11
        font.letterSpacing: 2
        color: Tokens.gold
    }

    ColumnLayout {
        id: surfaceColumn

        width: parent.width
        spacing: 24

        HudLabel {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: 'Windows, with a place in the world'
            font.pixelSize: 30
            font.weight: Font.Light
        }

        HudLabel {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: 'Choose a surface to request keyboard focus. Core decides whether it can safely activate it.'
                + (ShellState.available('surface.pocket') ? ' Put a window in the pocket to take it out of the world; take it out again to place it.' : '')
            color: Tokens.muted
            font.pixelSize: 14
        }

        ActionButton {
            text: 'Recall all windows ↗'
            enabled: ShellState.available('surfaces.recall')
            onClicked: ShellState.action('surfaces.recall', {})
        }

        SectionLabel {
            visible: page.cards.pocketed.length > 0
            objectName: 'pocketSection'
            text: 'IN THE POCKET  /  ' + page.cards.pocketed.length
        }

        CardGrid {
            visible: page.cards.pocketed.length > 0
            columns: page.columns
            model: page.cards.pocketed
        }

        SectionLabel {
            visible: page.cards.pocketed.length > 0 && page.cards.placed.length > 0
            Layout.topMargin: 8
            text: 'IN THE WORLD  /  ' + page.cards.placed.length
        }

        CardGrid {
            columns: page.columns
            model: page.cards.placed
        }

        HudLabel {
            visible: !page.cards.pocketed.length && !page.cards.placed.length
            text: 'No live surfaces in this session.'
            color: Tokens.muted
        }

    }

}
