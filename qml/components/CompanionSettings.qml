import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../Companion.js" as Companion

// Settings > Companion (IPC 0.25 draft, RFC-0010 companions amendment): None or one of the
// installed companion-capable characters (thumbnails from the catalog), Follow / Stay and
// (IPC 0.26) Walk / Run.
// Putting it on a route is tool 3 (or carrying it to a path) in the world.
ColumnLayout {
    id: root
    objectName: 'companionSettings'
    readonly property var companion: ShellState.companionState
    readonly property string chosen: Companion.chosen(companion)
    readonly property bool editable: ShellState.objectsCan('companion.set')
    spacing: 12
    onVisibleChanged: { if (visible) ShellState.refreshCatalog(); }

    HudLabel { objectName: 'companionStatus'; Layout.fillWidth: true; text: ShellState.companionStatus; wrapMode: Text.Wrap }
    RowLayout {
        Layout.fillWidth: true
        visible: !!root.chosen
        HudLabel { text: 'Mode'; Layout.preferredWidth: 140 }
        Segmented {
            objectName: 'companionMode'
            Layout.preferredWidth: 240
            enabled: ShellState.objectsCan('companion.mode') && root.companion && root.companion.state === 'active'
            model: Companion.MODES
            current: root.companion ? root.companion.mode : ''
            onPicked: (id) => ShellState.companionMode(id)
        }
        HudLabel {
            Layout.fillWidth: true
            visible: !!root.companion && root.companion.mode === 'route'
            text: 'On a route: Follow brings it back.'
            color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap
        }
    }
    RowLayout {
        Layout.fillWidth: true
        visible: !!root.chosen && ShellState.companionPaceSupported
        HudLabel { text: 'Pace'; Layout.preferredWidth: 140 }
        Segmented {
            objectName: 'companionPace'
            Layout.preferredWidth: 240
            enabled: ShellState.objectsCan('companion.mode') && !!Companion.paceParams(root.companion, 'walk')
            model: Companion.PACES
            current: root.companion && root.companion.pace ? root.companion.pace : 'walk'
            onPicked: (id) => ShellState.companionPace(id)
        }
        HudLabel {
            Layout.fillWidth: true
            text: 'How it keeps up while following.'
            color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap
        }
    }
    HudLabel { text: 'CHOOSE'; color: Tokens.gold; font.pixelSize: Tokens.caption; font.letterSpacing: 1.5; Layout.fillWidth: true }
    HudLabel {
        Layout.fillWidth: true
        visible: ShellState.objectCatalogLoaded && ShellState.companionChoices.length === 0
        text: 'No installed character can be a companion yet. Install a character library from Objects.'
        color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap
    }
    Flow {
        Layout.fillWidth: true
        spacing: 12
        Repeater {
            model: [{ref: '', name: 'None', thumbnail: '', capable: true, reason: '', source: ''}].concat(ShellState.companionChoices)
            delegate: Button {
                id: tile
                required property var modelData
                objectName: 'companionChoice:' + (modelData.ref || 'none')
                width: 168; height: 196
                enabled: root.editable && modelData.capable
                checked: modelData.ref === root.chosen
                Accessible.name: modelData.name + (checked ? ', chosen' : '')
                ToolTip.text: modelData.reason; ToolTip.visible: hovered && !modelData.capable && modelData.reason !== ''
                onClicked: { if (!checked) ShellState.chooseCompanion(modelData.ref); }
                background: Rectangle {
                    radius: 3
                    color: tile.hovered && tile.enabled ? Tokens.raised : Tokens.ink
                    opacity: Tokens.light ? .55 : .7
                    border.width: tile.checked ? 2 : 1
                    border.color: tile.checked ? Tokens.accent : Tokens.line
                }
                contentItem: ColumnLayout {
                    spacing: 6
                    opacity: tile.enabled || tile.checked ? 1 : .5
                    Item {
                        Layout.fillWidth: true; Layout.preferredHeight: 128
                        Image {
                            id: thumb
                            anchors.fill: parent; anchors.margins: 4
                            asynchronous: true; fillMode: Image.PreserveAspectFit
                            sourceSize.width: Math.ceil(width * Screen.devicePixelRatio)
                            sourceSize.height: Math.ceil(height * Screen.devicePixelRatio)
                            source: tile.modelData.thumbnail ? 'file://' + tile.modelData.thumbnail : ''
                            visible: status === Image.Ready
                        }
                        CubeGlyph {
                            anchors.centerIn: parent; width: parent.height * .45; height: width
                            visible: thumb.status !== Image.Ready && tile.modelData.ref !== ''
                            tint: Tokens.muted; stroke: 1.4
                        }
                        HudLabel {
                            anchors.centerIn: parent
                            visible: tile.modelData.ref === ''
                            text: '—'; font.pixelSize: Tokens.title; color: Tokens.muted
                        }
                    }
                    HudLabel { Layout.fillWidth: true; text: tile.modelData.name; elide: Text.ElideRight; horizontalAlignment: Text.AlignHCenter }
                    HudLabel {
                        Layout.fillWidth: true
                        text: !tile.modelData.capable ? tile.modelData.reason : tile.checked ? 'Chosen' : ''
                        color: tile.checked ? Tokens.accent : Tokens.muted
                        font.pixelSize: 11; elide: Text.ElideRight; horizontalAlignment: Text.AlignHCenter
                    }
                }
            }
        }
    }
    HudLabel {
        Layout.fillWidth: true
        text: 'Your companion follows you through every world. In a world: E on it for Talk, Stay or Follow; tool 3 puts it on a route you draw; Super+drag sets it down on a path or a spot.'
        color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap
    }
}
