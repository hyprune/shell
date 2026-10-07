import ".."
import "../theme"
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

RowLayout {
    id: root

    readonly property var selected: ShellState.places.find((p) => {
        return p.id === ShellState.selectedPlace;
    }) || (ShellState.places.length ? ShellState.places[0] : null)

    spacing: 28

    Rectangle {
        Layout.fillWidth: true
        Layout.fillHeight: true
        color: Tokens.panel
        border.color: Tokens.line
        radius: 3
        clip: true

        MapView {
            anchors.fill: parent
            selected: root.selected
            onSelectedPoint: (point) => {
                ShellState.selectedPlace = point.id;
                ShellState.waypoint(point);
            }
            onTravelRequested: (point) => {
                return ShellState.travel(point);
            }
        }

        HudLabel {
            text: '01    ORBITAL SURVEY'
            font.family: Tokens.mono
            font.pixelSize: 11
            color: Tokens.accent
            font.letterSpacing: 1.5

            anchors {
                top: parent.top
                left: parent.left
                margins: 24
            }

        }

    }

    ColumnLayout {
        Layout.preferredWidth: 300
        Layout.minimumWidth: 300
        Layout.maximumWidth: 300
        Layout.fillHeight: true
        spacing: 20

        HudLabel {
            text: 'LOCATION INDEX'
            color: Tokens.gold
            font.pixelSize: 11
            font.letterSpacing: 2
        }

        HudLabel {
            text: root.selected ? root.selected.name.replace(/\b\w/g, (c) => {
                return c.toUpperCase();
            }) : 'Explore the world'
            font.pixelSize: 29
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }

        HudLabel {
            text: 'A quiet coordinate in your desktop universe. Choose a spawn on the chart to inspect its position.'
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            color: Tokens.muted
            font.pixelSize: 14
            lineHeight: 1.5
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Tokens.line
        }

        HudLabel {
            text: root.selected ? root.selected.position.map((v) => {
                return v.toFixed(1);
            }).join('  /  ') + ' m' : '—'
            font.family: Tokens.mono
            font.pixelSize: 12
            color: Tokens.accent
        }

        HudLabel {
            text: 'SPAWN  /  ' + (root.selected ? root.selected.id : '—')
            font.family: Tokens.mono
            font.pixelSize: 11
            color: Tokens.muted
            Layout.fillWidth: true
        }

        Item {
            Layout.fillHeight: true
        }

        HudLabel {
            text: ShellState.available('travel.start') ? 'Click · set waypoint\nDouble click · jump to location' : ShellState.available('camera.set') ? 'Click · set waypoint\nDouble click · travel preview' : 'Select · inspect location\nDouble click · travel unavailable'
            color: Tokens.muted
            font.pixelSize: 12
            lineHeight: 1.7
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }

        ActionButton {
            text: ShellState.available('waypoint.set') ? 'Set waypoint ◇' : 'Set waypoint · unavailable'
            enabled: root.selected !== null && ShellState.available('waypoint.set')
            Layout.fillWidth: true
            onClicked: ShellState.waypoint(root.selected)
        }

        ActionButton {
            text: 'Arrive at spawn ↗'
            primary: true
            Layout.fillWidth: true
            enabled: root.selected !== null && ShellState.world !== null && ShellState.available('world.load')
            onClicked: ShellState.action('world.load', {
                "worldId": ShellState.world.id,
                "spawnId": root.selected.id
            })
        }

    }

}
