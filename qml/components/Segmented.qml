import "../theme"
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// A segmented control. model: [{id, label, selectable (default true)}]; `current` is the
// active segment id (may name a non-selectable one, shown active but not clickable).
Rectangle {
    id: root

    property var model: []
    property string current: ''
    signal picked(string id)

    implicitHeight: 42
    implicitWidth: 240
    radius: 3
    color: 'transparent'
    border.color: Tokens.line
    opacity: enabled ? 1 : 0.55

    RowLayout {
        anchors.fill: parent
        anchors.margins: 3
        spacing: 3

        Repeater {
            model: root.model

            delegate: Button {
                id: segment

                required property var modelData
                readonly property bool active: root.current === modelData.id
                readonly property bool selectable: modelData.selectable !== false

                objectName: 'segment:' + modelData.id
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumWidth: 0
                Layout.preferredWidth: 1
                enabled: root.enabled && selectable
                focusPolicy: selectable ? Qt.StrongFocus : Qt.NoFocus
                Accessible.checkable: selectable
                Accessible.checked: active
                onClicked: { if (!active) root.picked(modelData.id); }

                contentItem: HudLabel {
                    text: segment.modelData.label
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: 13
                    font.italic: segment.active && !segment.selectable
                    color: segment.active ? Tokens.ink : (segment.selectable && root.enabled ? Tokens.text : Tokens.muted)
                    elide: Text.ElideRight
                }

                background: Rectangle {
                    radius: 2
                    color: segment.active ? (segment.selectable ? Tokens.accent : Tokens.gold) : (segment.hovered && segment.enabled ? Tokens.raised : 'transparent')
                    border.width: segment.activeFocus ? 2 : 0
                    border.color: Tokens.gold
                }
            }
        }
    }
}
