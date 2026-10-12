import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../Objects.js" as Objects
import "../Npcs.js" as Npcs

// Director > Objects: spawning a character from the catalog (IPC 0.23 npcs.spawn), or
// rebinding a user character (npcs.bind). Left: "Choose route" (Stand here, this world's
// routes from paths.list with core's walkability, Draw a new route). Right: optional settings
// (speed, start phase, direction, accent colour) and, for a user route, its stops (saved with
// paths.set). Keys: Up/Down choose, Enter confirms, Esc goes back.
FocusScope {
    id: root
    objectName: 'npcSpawn'
    readonly property bool rebinding: ShellState.rebindId !== ''
    readonly property var entry: Objects.entryFor(ShellState.objectCatalog, ShellState.spawnRef)
    readonly property var instance: Npcs.selectedCharacter(ShellState.characterInstances, ShellState.rebindId)
    readonly property string subject: rebinding ? (instance ? instance.name : '') : (entry ? entry.name : '')
    readonly property var routes: Npcs.routeOptions(ShellState.pathList)
    readonly property var rows: (rebinding ? [] : [{kind: 'stand', label: 'Stand here', note: 'In front of you, facing you.', enabled: true, sourceLabel: ''}])
        .concat(routes.map(r => Object.assign({kind: 'route'}, r)))
        .concat([{kind: 'draw', label: 'Draw a new route', note: 'Closes the Director: click points with tool 3.', enabled: true, sourceLabel: ''}])
    property int cursor: rebinding ? 0 : Math.min(1, rows.length - 1)
    readonly property var row: rows[Math.max(0, Math.min(cursor, rows.length - 1))] || null
    readonly property var choice: row ? (row.kind === 'route' ? {kind: 'route', path: row.ref} : {kind: row.kind}) : null
    readonly property var record: row && row.kind === 'route' ? Npcs.pathFor(ShellState.pathList, row.ref) : null
    readonly property bool onRoute: !!row && row.kind !== 'stand'
    readonly property bool full: !rebinding && Npcs.userFull(ShellState.npcsState)
    // Settings (defaults leave the params out).
    property real speed: 1
    property real phase: 0
    property bool reverse: false
    property string accent: ''
    property var stops: []
    property string stopsFor: ''
    readonly property var settings: ({speed: speed, phase: phase, reverse: reverse, accent: accent})
    readonly property var request: rebinding ? Npcs.bindRequest(instance, choice, settings) : Npcs.spawnRequest(ShellState.spawnRef, choice, settings)
    readonly property bool ready: !!request && !!row && row.enabled && !full && ShellState.npcsCan(request.method)

    function reset() {
        speed = 1; phase = 0; reverse = false; stops = []; stopsFor = '';
        accent = rebinding && instance && instance.accent ? Npcs.hexFromAccent(instance.accent) : '';
        cursor = rebinding ? Math.max(0, rows.findIndex(r => r.kind === 'route' && instance && r.ref === instance.path)) : Math.min(1, rows.length - 1);
    }
    onVisibleChanged: { if (visible) { reset(); Qt.callLater(() => list.forceActiveFocus()); } }
    onRecordChanged: {
        var key = record ? record.ref + '#' + JSON.stringify(record.stops) : '';
        if (key !== stopsFor) { stopsFor = key; stops = Npcs.stopDrafts(record); }
    }
    function move(key) {
        var next = Npcs.choiceMove(cursor, rows.length, key === 'down' ? 'next' : 'previous');
        if (key === 'down' && cursor === rows.length - 1) next = cursor;
        if (key === 'up' && cursor === 0) next = 0;
        cursor = next;
        list.positionViewAtIndex(cursor, ListView.Contain);
    }
    function confirm() { if (ready) ShellState.npcAction(request.method, request.params); }
    function setStop(index, patch) { var next = stops.slice(); next[index] = Object.assign({}, next[index], patch); stops = next; }
    function saveStops() {
        var made = Npcs.stopsRequest(record, stops);
        if (made.error) ShellState.sayObjects(made.error, 'warning');
        else ShellState.npcAction(made.method, made.params);
    }

    Keys.onEscapePressed: ShellState.closeSpawn()

    component Caption: HudLabel { Layout.fillWidth: true; color: Tokens.gold; font.pixelSize: Tokens.caption; font.letterSpacing: 1.5 }
    component Note: HudLabel { Layout.fillWidth: true; color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap }

    Rectangle { anchors.fill: parent; color: Tokens.panel; border.color: Tokens.line; radius: 3 }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 14

        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                HudLabel { Layout.fillWidth: true; text: (root.rebinding ? 'REBIND ROUTE' : 'SPAWN A CHARACTER'); color: Tokens.gold; font.pixelSize: 11; font.letterSpacing: 1.8 }
                HudLabel { objectName: 'npcSpawnTitle'; Layout.fillWidth: true; text: root.subject; font.pixelSize: 24; font.weight: Font.Light; elide: Text.ElideRight }
            }
            HudLabel {
                objectName: 'npcSpawnUsage'
                text: Npcs.usageText(ShellState.npcsState)
                color: root.full ? Tokens.warning : Tokens.muted
                font.family: Tokens.mono; font.pixelSize: 11
            }
            ActionButton { objectName: 'npc-spawn-back'; text: 'Back  ·  Esc'; onClicked: ShellState.closeSpawn() }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 20

            // ---- 1  Choose route ----
            ColumnLayout {
                Layout.preferredWidth: root.width < 1100 ? 330 : 430
                Layout.fillHeight: true
                spacing: 8
                Caption { text: '1  CHOOSE ROUTE' }
                ListView {
                    id: list
                    objectName: 'npcRoutes'
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    focus: true
                    model: root.rows
                    spacing: 4
                    keyNavigationEnabled: false
                    highlightFollowsCurrentItem: false
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.vertical: ScrollBar {}
                    Keys.onUpPressed: root.move('up')
                    Keys.onDownPressed: root.move('down')
                    Keys.onReturnPressed: root.confirm()
                    Keys.onEnterPressed: root.confirm()
                    delegate: Item {
                        id: option
                        required property var modelData
                        required property int index
                        readonly property bool current: index === root.cursor
                        objectName: 'npcRoute:' + (modelData.kind === 'route' ? modelData.ref : modelData.kind)
                        Accessible.role: Accessible.ListItem
                        Accessible.name: modelData.label
                        Accessible.description: modelData.note || ''
                        Accessible.selected: current
                        width: list.width - 8
                        height: 58
                        opacity: modelData.enabled ? 1 : 0.6
                        Rectangle {
                            anchors.fill: parent
                            radius: 3
                            color: option.current ? Tokens.raised : 'transparent'
                            border.width: option.current ? (list.activeFocus ? 2 : 1) : 0
                            border.color: Tokens.gold
                        }
                        HudLabel {
                            x: 10; y: 9
                            width: 28
                            text: option.modelData.kind === 'stand' ? '◎' : option.modelData.kind === 'draw' ? '✎' : option.modelData.closed ? '↻' : '⤳'
                            color: option.modelData.enabled ? Tokens.accent : Tokens.muted
                            font.pixelSize: 16
                        }
                        Column {
                            x: 40; y: 8; width: parent.width - 52
                            spacing: 3
                            RowLayout {
                                width: parent.width
                                spacing: 8
                                HudLabel { Layout.fillWidth: true; text: option.modelData.label; font.pixelSize: 15; elide: Text.ElideRight }
                                HudLabel {
                                    visible: option.modelData.sourceLabel !== ''
                                    text: option.modelData.sourceLabel.toUpperCase()
                                    color: option.modelData.source === 'user' ? Tokens.gold : Tokens.accent
                                    font.pixelSize: 9; font.letterSpacing: 1.2
                                }
                            }
                            HudLabel {
                                width: parent.width
                                text: option.modelData.note || (option.modelData.kind === 'route' ? option.modelData.points + ' points' + (option.modelData.closed ? ' · loop' : '') : '')
                                color: option.modelData.level === 'warning' ? Tokens.warning : Tokens.muted
                                font.pixelSize: 12; elide: Text.ElideRight
                            }
                        }
                        MouseArea { anchors.fill: parent; onClicked: { root.cursor = option.index; list.forceActiveFocus(); } onDoubleClicked: { root.cursor = option.index; root.confirm(); } }
                    }
                    HudLabel {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        visible: ShellState.pathsLoaded && !root.routes.length
                        text: 'This world has no routes yet: draw one.'
                        color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap
                    }
                }
            }

            Rectangle { Layout.fillHeight: true; width: 1; color: Tokens.line }

            // ---- 2  Settings ----
            ScrollView {
                id: settingsScroll
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                contentWidth: availableWidth
                ColumnLayout {
                    width: Math.min(settingsScroll.availableWidth - 12, 760)
                    spacing: 10
                    Caption { text: '2  SETTINGS  ·  OPTIONAL' }
                    RowLayout {
                        Layout.fillWidth: true
                        HudLabel { text: 'Speed'; Layout.preferredWidth: 120 }
                        SettingSlider { id: speedSlider; objectName: 'npc-speed'; Layout.fillWidth: true; from: Npcs.SPEED_MIN; to: Npcs.SPEED_MAX; stepSize: 0.05; value: root.speed; onMoved: root.speed = Math.round(value * 100) / 100 }
                        HudLabel { Layout.preferredWidth: 70; text: '× ' + root.speed.toFixed(2); horizontalAlignment: Text.AlignRight; font.family: Tokens.mono; font.pixelSize: 12 }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        visible: root.onRoute
                        HudLabel { text: 'Start at'; Layout.preferredWidth: 120 }
                        SettingSlider { objectName: 'npc-phase'; Layout.fillWidth: true; from: 0; to: 0.95; stepSize: 0.05; value: root.phase; onMoved: root.phase = Math.round(value * 100) / 100 }
                        HudLabel { Layout.preferredWidth: 70; text: Math.round(root.phase * 100) + ' %'; horizontalAlignment: Text.AlignRight; font.family: Tokens.mono; font.pixelSize: 12 }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        visible: root.onRoute && !(root.row && root.row.kind === 'draw')
                        HudLabel { text: 'Direction'; Layout.preferredWidth: 120 }
                        Segmented {
                            objectName: 'npc-direction'
                            Layout.preferredWidth: 260
                            model: [{id: 'forward', label: 'Forward'}, {id: 'reverse', label: 'Reverse'}]
                            current: root.reverse ? 'reverse' : 'forward'
                            onPicked: (id) => root.reverse = id === 'reverse'
                        }
                        Item { Layout.fillWidth: true }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        HudLabel { text: 'Accent'; Layout.preferredWidth: 120 }
                        Flow {
                            Layout.fillWidth: true
                            spacing: 6
                            Repeater {
                                model: [''].concat(Npcs.ACCENTS)
                                delegate: Rectangle {
                                    required property var modelData
                                    objectName: 'npc-accent:' + (modelData || 'none')
                                    width: 30; height: 30; radius: 15
                                    color: modelData || 'transparent'
                                    border.width: root.accent === modelData ? 3 : 1
                                    border.color: root.accent === modelData ? Tokens.gold : Tokens.line
                                    Accessible.role: Accessible.RadioButton
                                    Accessible.name: modelData ? 'Accent ' + modelData : 'Asset colour'
                                    Accessible.checked: root.accent === modelData
                                    HudLabel { anchors.centerIn: parent; visible: !parent.modelData; text: '∅'; color: Tokens.muted; font.pixelSize: 13 }
                                    MouseArea { anchors.fill: parent; onClicked: root.accent = parent.modelData }
                                }
                            }
                        }
                    }
                    Note { text: root.accent ? 'Recolours the character\'s accent material.' : 'No accent: the character keeps its own colours.' }

                    // Stops on a user route: per point, wait, a gesture or a seat.
                    Rectangle { Layout.fillWidth: true; height: 1; color: Tokens.line; visible: Npcs.editableRoute(root.record) }
                    ColumnLayout {
                        objectName: 'npcStops'
                        Layout.fillWidth: true
                        visible: Npcs.editableRoute(root.record)
                        spacing: 6
                        Caption { text: 'STOPS ON ' + (root.record ? Npcs.pathLabel(root.record).toUpperCase() : '') }
                        Note { text: 'Where the character pauses: seconds at a point, with a gesture or on a seat (a seat id, an object id or object/anchor). Saved to the route.' }
                        Repeater {
                            model: root.stops
                            delegate: RowLayout {
                                id: stopRow
                                required property var modelData
                                required property int index
                                objectName: 'npcStop:' + modelData.point
                                Layout.fillWidth: true
                                spacing: 8
                                HudLabel { text: 'Point'; color: Tokens.muted; font.pixelSize: 12 }
                                TextField {
                                    objectName: 'npc-stop-point'
                                    implicitWidth: 64; implicitHeight: 36
                                    text: String(stopRow.modelData.point)
                                    color: Tokens.text; font.family: Tokens.mono; font.pixelSize: 13
                                    inputMethodHints: Qt.ImhDigitsOnly
                                    Accessible.name: 'Route point of this stop (0 to ' + (root.record ? root.record.points.length - 1 : 0) + ')'
                                    onEditingFinished: root.setStop(stopRow.index, {point: text})
                                    background: Rectangle { radius: Tokens.radius; color: Tokens.panel; border.width: parent.activeFocus ? 2 : 1; border.color: parent.activeFocus ? Tokens.gold : Tokens.line }
                                }
                                TextField {
                                    objectName: 'npc-stop-seconds'
                                    implicitWidth: 74; implicitHeight: 36
                                    text: String(stopRow.modelData.seconds)
                                    color: Tokens.text; font.family: Tokens.mono; font.pixelSize: 13
                                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                                    Accessible.name: 'Seconds at point ' + stopRow.modelData.point
                                    onEditingFinished: root.setStop(stopRow.index, {seconds: text})
                                    background: Rectangle { radius: Tokens.radius; color: Tokens.panel; border.width: parent.activeFocus ? 2 : 1; border.color: parent.activeFocus ? Tokens.gold : Tokens.line }
                                }
                                HudLabel { text: 's'; color: Tokens.muted; font.pixelSize: 12 }
                                Choice {
                                    objectName: 'npc-stop-kind'
                                    implicitWidth: 130
                                    model: ['Wait', 'Gesture', 'Seat'].concat(stopRow.modelData.kind === 'face' ? ['Face'] : [])
                                    currentIndex: ['wait', 'clip', 'seat', 'face'].indexOf(stopRow.modelData.kind)
                                    onActivated: (i) => root.setStop(stopRow.index, {kind: ['wait', 'clip', 'seat', 'face'][i]})
                                }
                                Choice {
                                    visible: stopRow.modelData.kind === 'clip'
                                    implicitWidth: 150
                                    model: Npcs.CLIPS.map(c => c.label)
                                    currentIndex: Math.max(0, Npcs.CLIPS.findIndex(c => c.id === stopRow.modelData.clip))
                                    onActivated: (i) => root.setStop(stopRow.index, {clip: Npcs.CLIPS[i].id})
                                }
                                TextField {
                                    visible: stopRow.modelData.kind === 'seat'
                                    objectName: 'npc-stop-seat'
                                    Layout.fillWidth: true
                                    implicitHeight: 36
                                    text: stopRow.modelData.seat
                                    placeholderText: 'seat id'
                                    color: Tokens.text; placeholderTextColor: Tokens.muted; font.pixelSize: 13
                                    maximumLength: 192
                                    onEditingFinished: root.setStop(stopRow.index, {seat: text})
                                    background: Rectangle { radius: Tokens.radius; color: Tokens.panel; border.width: parent.activeFocus ? 2 : 1; border.color: parent.activeFocus ? Tokens.gold : Tokens.line }
                                }
                                Item { Layout.fillWidth: true; visible: stopRow.modelData.kind !== 'seat' }
                                ActionButton {
                                    implicitWidth: 44
                                    text: '×'
                                    Accessible.name: 'Remove the stop at point ' + stopRow.modelData.point
                                    onClicked: root.stops = root.stops.filter((s, i) => i !== stopRow.index)
                                }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            ActionButton {
                                objectName: 'npc-stop-add'
                                text: 'Add stop'
                                enabled: Npcs.nextStopPoint(root.record, root.stops) >= 0 && root.stops.length < Npcs.STOPS_MAX
                                onClicked: root.stops = Npcs.addStop(root.record, root.stops)
                            }
                            ActionButton {
                                objectName: 'npc-stops-save'
                                text: 'Save stops'
                                enabled: ShellState.npcsCan('paths.set')
                                onClicked: root.saveStops()
                            }
                            Item { Layout.fillWidth: true }
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            HudLabel {
                objectName: 'npcSpawnNote'
                Layout.fillWidth: true
                text: root.full ? 'Your characters in this world are at the limit (' + Npcs.usageText(ShellState.npcsState) + ').'
                    : root.row && !root.row.enabled ? root.row.note
                    : root.row && root.row.kind === 'draw' ? 'Tool 3 opens with a fresh route. Leave tool 3 or press Done to finish.' : ''
                color: root.full || (root.row && !root.row.enabled) ? Tokens.warning : Tokens.muted
                font.pixelSize: 13; wrapMode: Text.Wrap
            }
            ActionButton {
                objectName: 'npc-spawn-confirm'
                primary: true
                text: !root.row ? 'Spawn' : root.row.kind === 'draw' ? 'Draw a new route  ·  Enter'
                    : root.row.kind === 'stand' ? 'Spawn here  ·  Enter'
                    : (root.rebinding ? 'Bind to route  ·  Enter' : 'Spawn on route  ·  Enter')
                enabled: root.ready
                onClicked: root.confirm()
            }
        }
    }
}
