import ".."
import "../theme"
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Flickable {
    id: root
    property int selected: 0
    clip: true
    contentWidth: width
    contentHeight: destinations.height
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: ScrollBar {}
    Column {
        id: destinations
        width: parent.width - 16
        spacing: 24
        HudLabel { width: parent.width; text: 'Destinations'; font.pixelSize: Tokens.title }
        HudLabel { width: parent.width; text: 'Choose your next horizon'; color: Tokens.muted; wrapMode: Text.Wrap }
        GridLayout {
            width: parent.width
            columns: Math.max(1, Math.floor(width / 350))
            columnSpacing: 24; rowSpacing: 24
            Repeater {
                model: ShellState.worlds
                DestinationCard {
                    required property var modelData
                    required property int index
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    Layout.preferredWidth: 1
                    compact: root.height < 450
                    destination: modelData
                    variant: index
                    selected: root.selected === index
                    onChosen: root.selected = index
                }
            }
        }
    }
}
