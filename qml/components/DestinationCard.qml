import ".."
import "../theme"
import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    property var destination
    property int variant: 0
    property bool selected: false
    property bool compact: false
    signal chosen()
    implicitHeight: content.implicitHeight + 40
    color: selected ? Tokens.raised : Tokens.panel
    radius: Tokens.radius
    border.color: selected ? Tokens.accent : Tokens.line
    TapHandler { onTapped: root.chosen() }
    ColumnLayout {
        id: content
        anchors.fill: parent; anchors.margins: 20
        spacing: root.compact ? 10 : 20
        HudLabel {
            Layout.fillWidth: true
            text: root.destination.name
            horizontalAlignment: Text.AlignHCenter
            font.pixelSize: 24
            maximumLineCount: 2
            wrapMode: Text.Wrap
        }
        Seal { Layout.alignment: Qt.AlignHCenter; width: root.compact ? 48 : 120; height: width; variant: root.variant; tint: Tokens.accent }
        HudLabel {
            Layout.fillWidth: true
            Layout.preferredHeight: root.compact ? 36 : 64
            text: root.destination.description || 'An explorable desktop world.'
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            maximumLineCount: 3
            color: Tokens.muted
        }
        ActionButton {
            Layout.fillWidth: true
            text: 'Travel to destination ↗'
            primary: root.selected
            enabled: ShellState.available('world.load')
            onClicked: ShellState.action('world.load', {worldId:root.destination.id})
        }
    }
}
