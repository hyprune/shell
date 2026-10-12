import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../Npcs.js" as Npcs

// Director > Objects > Characters (IPC 0.23): this world's characters, authored and the
// player's own (objects.instances with character true), with route, activity and state.
// Disable / Enable works on both, Rebind route and Remove on the player's own. The motion
// setting (graphics npc_motion) and why characters are paused sit on top. Keys: Up/Down
// select, D disables or enables, B rebinds, Delete removes.
FocusScope {
    id: root
    objectName: 'npcPanel'
    readonly property var npcs: ShellState.npcsState
    readonly property var instances: ShellState.characterInstances
    readonly property var rows: Npcs.characterRows(instances, ShellState.pathList)
    readonly property var selected: Npcs.selectedCharacter(instances, ShellState.selectedCharacter)
    readonly property bool hasUser: instances.some(i => i.source === 'user')
    property bool confirmRemoveAll: false

    function focusList() { list.forceActiveFocus(); }
    function syncSelection() { if (!selected && rows.length) ShellState.selectedCharacter = rows[0].id; }
    onRowsChanged: syncSelection()
    onVisibleChanged: { if (visible) { syncSelection(); Qt.callLater(focusList); } }
    function selectAt(index) {
        if (index < 0 || index >= rows.length) return;
        ShellState.selectedCharacter = rows[index].id;
        list.positionViewAtIndex(index, ListView.Contain);
    }
    function run(actionId) {
        if (!selected) return;
        var action = Npcs.characterActions(selected).find(a => a.id === actionId);
        if (!action || !action.visible || !ShellState.npcsCan(action.method)) return;
        if (actionId === 'rebind') { ShellState.startRebind(selected.id); return; }
        var request = Npcs.characterRequest(selected, actionId);
        if (request) ShellState.npcAction(request.method, request.params);
    }
    Timer { id: confirmTimer; interval: 6000; onTriggered: root.confirmRemoveAll = false }

    Keys.onPressed: (event) => {
        if (event.modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)) return;
        var map = {}; map[Qt.Key_D] = 'disable'; map[Qt.Key_B] = 'rebind'; map[Qt.Key_Delete] = 'remove';
        if (map[event.key]) { root.run(map[event.key]); event.accepted = true; }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 14

        // ---- Motion setting and effective state ----
        RowLayout {
            Layout.fillWidth: true
            spacing: 14
            HudLabel { text: 'MOTION'; color: Tokens.gold; font.pixelSize: Tokens.caption; font.letterSpacing: 1.5 }
            Segmented {
                objectName: 'npcMotion'
                Layout.preferredWidth: 360
                model: Npcs.MOTIONS
                current: root.npcs ? root.npcs.motion : ''
                enabled: ShellState.available('graphics.set')
                onPicked: (id) => ShellState.setNpcMotion(id)
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                HudLabel {
                    objectName: 'npcState'
                    Layout.fillWidth: true
                    text: Npcs.stateText(root.npcs)
                    color: Npcs.stateLevel(root.npcs) === 'warning' ? Tokens.warning : Npcs.stateLevel(root.npcs) === 'ok' ? Tokens.positive : Tokens.muted
                    font.pixelSize: 14; elide: Text.ElideRight
                }
                HudLabel {
                    Layout.fillWidth: true
                    text: root.npcs ? Npcs.MOTION_NOTES[root.npcs.motion] || '' : ''
                    color: Tokens.muted; font.pixelSize: 12; elide: Text.ElideRight
                }
            }
            HudLabel {
                objectName: 'npcUsage'
                text: Npcs.usageText(root.npcs)
                color: Npcs.userFull(root.npcs) ? Tokens.warning : Tokens.muted
                font.family: Tokens.mono; font.pixelSize: 11
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 20

            // ---- Characters in this world ----
            Rectangle {
                Layout.preferredWidth: root.width < 1100 ? 300 : 380
                Layout.fillHeight: true
                color: Tokens.panel
                border.color: Tokens.line
                radius: 3

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 10
                    HudLabel { Layout.fillWidth: true; text: 'CHARACTERS  /  ' + root.rows.length; color: Tokens.gold; font.pixelSize: 11; font.letterSpacing: 2 }
                    ListView {
                        id: list
                        objectName: 'npcList'
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        focus: true
                        model: root.rows
                        keyNavigationEnabled: false
                        highlightFollowsCurrentItem: false
                        boundsBehavior: Flickable.StopAtBounds
                        ScrollBar.vertical: ScrollBar {}
                        readonly property int selectedIndex: root.rows.findIndex(r => r.id === ShellState.selectedCharacter)
                        Keys.onUpPressed: root.selectAt(Math.max(0, selectedIndex - 1))
                        Keys.onDownPressed: root.selectAt(Math.min(root.rows.length - 1, selectedIndex + 1))
                        delegate: Item {
                            id: row
                            required property var modelData
                            required property int index
                            readonly property bool current: modelData.id === ShellState.selectedCharacter
                            objectName: 'npcRow:' + modelData.id
                            Accessible.role: Accessible.ListItem
                            Accessible.name: modelData.name
                            Accessible.description: modelData.sourceLabel + ' · ' + modelData.place + ' · ' + modelData.activity
                            Accessible.selected: current
                            width: list.width - 8
                            height: 78
                            Rectangle {
                                anchors.fill: parent
                                anchors.topMargin: 2
                                radius: 3
                                color: row.current ? Tokens.raised : 'transparent'
                                border.width: row.current && list.activeFocus ? 2 : 0
                                border.color: Tokens.gold
                            }
                            Rectangle { x: 0; y: 10; width: 3; height: parent.height - 16; color: row.modelData.user ? Tokens.gold : Tokens.accent; opacity: .8 }
                            Column {
                                x: 14; y: 9; width: parent.width - 22
                                spacing: 3
                                RowLayout {
                                    width: parent.width
                                    spacing: 8
                                    HudLabel { Layout.fillWidth: true; text: '☺  ' + row.modelData.name; font.pixelSize: 15; elide: Text.ElideRight; opacity: row.modelData.disabled ? .6 : 1 }
                                    HudLabel { text: row.modelData.sourceLabel.toUpperCase(); color: row.modelData.user ? Tokens.gold : Tokens.accent; font.pixelSize: 9; font.letterSpacing: 1.2 }
                                }
                                HudLabel { width: parent.width; text: row.modelData.place; font.pixelSize: 12; color: Tokens.muted; elide: Text.ElideRight }
                                HudLabel {
                                    width: parent.width
                                    text: row.modelData.activity
                                    font.pixelSize: 12
                                    color: row.modelData.level === 'warning' ? Tokens.warning : row.modelData.level === 'ok' ? Tokens.positive : Tokens.muted
                                }
                            }
                            MouseArea { anchors.fill: parent; onClicked: { list.forceActiveFocus(); root.selectAt(row.index); } }
                        }
                        HudLabel {
                            anchors.centerIn: parent
                            width: parent.width - 20
                            visible: !root.rows.length
                            text: 'No characters in this world yet. Spawn one from the Catalog.'
                            color: Tokens.muted; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter
                        }
                    }
                    Rectangle { Layout.fillWidth: true; height: 1; color: Tokens.line }
                    ActionButton {
                        objectName: 'npcs-remove-all'
                        Layout.fillWidth: true
                        text: root.confirmRemoveAll ? 'Remove all of them? Press again' : 'Remove my characters'
                        enabled: root.hasUser && ShellState.npcsCan('npcs.remove')
                        onClicked: {
                            if (root.confirmRemoveAll) { root.confirmRemoveAll = false; ShellState.npcAction('npcs.remove', {all: true}); }
                            else { root.confirmRemoveAll = true; confirmTimer.restart(); }
                        }
                    }
                }
            }

            // ---- The selected character ----
            ColumnLayout {
                objectName: 'npcDetail'
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.maximumWidth: 900
                spacing: 12
                visible: !!root.selected
                HudLabel {
                    Layout.fillWidth: true
                    text: root.selected ? [Npcs.sourceLabel(root.selected.source), Npcs.activityText(root.selected)].join('  ·  ').toUpperCase() : ''
                    color: root.selected && Npcs.activityLevel(root.selected) === 'warning' ? Tokens.warning : Tokens.gold
                    font.pixelSize: 11; font.letterSpacing: 1.8
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    Rectangle {
                        visible: !!(root.selected && root.selected.accent)
                        width: 22; height: 22; radius: 11
                        color: root.selected && root.selected.accent ? Npcs.hexFromAccent(root.selected.accent) : 'transparent'
                        border.color: Tokens.line
                    }
                    HudLabel { objectName: 'npcTitle'; Layout.fillWidth: true; text: root.selected ? root.selected.name : ''; font.pixelSize: Tokens.title; font.weight: Font.Light; elide: Text.ElideRight }
                }
                HudLabel {
                    Layout.fillWidth: true
                    text: root.selected ? [root.selected.ref || root.selected.id, root.selected.areaId ? 'area ' + root.selected.areaId : ''].filter(v => v).join('  ·  ') : ''
                    font.family: Tokens.mono; font.pixelSize: 12; color: Tokens.muted; elide: Text.ElideRight
                }
                Rectangle { Layout.fillWidth: true; height: 1; color: Tokens.line }
                HudLabel { Layout.fillWidth: true; text: 'ROUTE'; color: Tokens.gold; font.pixelSize: Tokens.caption; font.letterSpacing: 1.5 }
                HudLabel {
                    objectName: 'npcPlace'
                    Layout.fillWidth: true
                    text: Npcs.placeText(root.selected, ShellState.pathList)
                    font.pixelSize: 15; wrapMode: Text.Wrap
                }
                HudLabel {
                    Layout.fillWidth: true
                    visible: !!(root.selected && root.selected.state === 'suspended')
                    text: (function () {
                        var p = root.selected ? Npcs.pathFor(ShellState.pathList, root.selected.path) : null;
                        return 'Its route is not walkable' + (p && p.problems.length ? ': ' + p.problems[0] : '.') + ' Fix or rebind the route.';
                    })()
                    color: Tokens.warning; font.pixelSize: 13; wrapMode: Text.Wrap
                }
                Rectangle { Layout.fillWidth: true; height: 1; color: Tokens.line }
                Flow {
                    Layout.fillWidth: true
                    spacing: 8
                    Repeater {
                        model: Npcs.characterActions(root.selected).filter(a => a.visible)
                        delegate: ActionButton {
                            required property var modelData
                            objectName: 'npc-' + modelData.id
                            text: modelData.label + (modelData.id === 'disable' ? ' · D' : modelData.id === 'rebind' ? ' · B' : ' · Del')
                            enabled: ShellState.npcsCan(modelData.method)
                            onClicked: root.run(modelData.id)
                        }
                    }
                }
                HudLabel {
                    Layout.fillWidth: true
                    text: !root.selected ? '' : root.selected.source === 'user'
                          ? 'Disabled characters are not drawn and keep their route. Rebind picks another route or draws a new one. Remove deletes it from this world.'
                          : 'Characters the world places are never deleted: disable hides one until you enable it again.'
                    color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap
                }
                Item { Layout.fillHeight: true }
            }
            HudLabel {
                Layout.fillWidth: true
                visible: !root.selected
                text: root.rows.length ? 'Select a character.' : ''
                color: Tokens.muted; font.pixelSize: 14
            }
        }
    }
}
