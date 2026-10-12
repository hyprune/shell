import QtQuick
import ".."
import "../theme"
import "../Npcs.js" as Npcs

// IPC 0.23: a character's choice list (npcs.interaction type choose). The bridge holds
// exclusive input while it is shown, so it takes the keyboard and the mouse: Up/Down and
// Enter, 1-8 pick directly, a click picks; Esc (or core's menu exit) ends the interaction
// with interaction.choose null. Styled like the HUD tiles; reduced motion is instant.
Item {
    id: root
    objectName: 'npcChoice'
    readonly property var interaction: ShellState.npcChoice
    readonly property var items: Npcs.choiceItems(interaction)
    readonly property string speaker: interaction ? ShellState.characterName(interaction.objectId) || interaction.label : ''
    readonly property bool technical: Tokens.hudConcept === 'Instrument'
    readonly property bool minimal: Tokens.hudConcept === 'Minimal'
    property int cursor: 0
    implicitWidth: 460
    implicitHeight: column.implicitHeight + 28
    onInteractionChanged: { cursor = 0; if (interaction) Qt.callLater(() => keys.forceActiveFocus()); }

    function pick(index) { if (index >= 0 && index < items.length) ShellState.chooseInteraction(items[index].id); }

    Item {
        id: keys
        focus: true
        Keys.onUpPressed: root.cursor = Npcs.choiceMove(root.cursor, root.items.length, 'previous')
        Keys.onDownPressed: root.cursor = Npcs.choiceMove(root.cursor, root.items.length, 'next')
        Keys.onTabPressed: root.cursor = Npcs.choiceMove(root.cursor, root.items.length, 'next')
        Keys.onReturnPressed: root.pick(root.cursor)
        Keys.onEnterPressed: root.pick(root.cursor)
        Keys.onEscapePressed: ShellState.chooseInteraction(null)
        Keys.onPressed: (event) => {
            var n = event.key - Qt.Key_1;
            if (n >= 0 && n < root.items.length) { root.pick(n); event.accepted = true; }
        }
    }

    HudTile {
        anchors.fill: parent
        color: root.minimal ? '#e013242d' : Qt.rgba(Tokens.hudScrim.r, Tokens.hudScrim.g, Tokens.hudScrim.b, .94)
        borderColor: Tokens.hudAccent
        borderWidth: root.technical ? 1 : 0
    }
    Rectangle { width: root.minimal ? 2 : 4; height: parent.height; color: Tokens.hudAccent }

    Column {
        id: column
        x: 20; y: 14
        width: parent.width - 36
        spacing: 6
        HudText {
            objectName: 'npcChoiceSpeaker'
            width: parent.width
            text: root.speaker.toUpperCase()
            font.pixelSize: 11; font.letterSpacing: 1.6; font.family: root.technical ? Tokens.mono : Tokens.hudFont
            color: Tokens.hudAccent; elide: Text.ElideRight
        }
        Repeater {
            model: root.items
            delegate: Item {
                id: option
                required property var modelData
                required property int index
                readonly property bool current: index === root.cursor
                objectName: 'npcChoice:' + modelData.id
                Accessible.role: Accessible.MenuItem
                Accessible.name: modelData.label
                Accessible.selected: current
                width: column.width
                height: 38
                Rectangle {
                    anchors.fill: parent
                    radius: root.minimal ? 0 : 3
                    color: option.current ? Qt.rgba(Tokens.hudAccent.r, Tokens.hudAccent.g, Tokens.hudAccent.b, .18) : 'transparent'
                    border.width: option.current ? 1 : 0
                    border.color: Tokens.hudAccent
                }
                HudText {
                    x: 10; anchors.verticalCenter: parent.verticalCenter
                    width: 24
                    text: option.modelData.key
                    font.pixelSize: 12; font.family: Tokens.mono
                    color: option.current ? Tokens.hudAccent : Tokens.hudMuted
                }
                HudText {
                    x: 38; anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - 48
                    text: option.modelData.label
                    font.pixelSize: 16; elide: Text.ElideRight
                }
                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    onEntered: root.cursor = option.index
                    onClicked: root.pick(option.index)
                }
            }
        }
        HudText {
            width: parent.width
            text: '↑↓ · Enter   1–' + Math.max(1, root.items.length) + '   Esc · leave'
            font.pixelSize: 11; font.family: Tokens.mono
            color: Tokens.hudMuted
        }
    }
}
