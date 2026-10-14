import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../Objects.js" as Objects
import "../Npcs.js" as Npcs

// Director > Objects (RFC-0011 P1, IPC 0.22). Catalog: every source (World, Library, Mine)
// as cards with source and category filters and a search over names and tags; Add puts the
// object in the pocket and core selects tool 5. Placed: this world's authored and user
// instances with the configure panel. Keys: Up/Down move, Enter adds (Catalog) or edits
// (Placed), / searches, V switches the view, L lock, H hide or show, R reset, Delete removes;
// Left/Right still change the Director view and Esc leaves the menu.
// IPC 0.23: character entries spawn (NpcSpawn: choose a route, then settings) instead of
// going to the pocket; Characters lists this world's characters (NpcPanel); while a route is
// being drawn (npcs.drawing) a bar offers Done (paths.finish) and Cancel.
FocusScope {
    id: root
    objectName: 'directorObjects'
    property string source: 'all'
    property string category: ''
    property string query: ''
    property int cursor: 0          // catalog card under the keyboard cursor
    property string confirm: ''     // 'reset-all' | 'remove-all' waiting for a second press
    readonly property string view: ShellState.objectsView
    readonly property var entries: ShellState.objectCatalog
    readonly property var shown: Objects.filterCatalog(entries, {source: source, category: category, query: query})
    readonly property var cats: Objects.categories(entries)
    readonly property var objectsState: ShellState.objectsState
    // Characters have their own view (IPC 0.23); Placed lists the other objects.
    readonly property var instances: objectsState ? objectsState.instances.filter(i => i.character !== true) : []
    readonly property bool spawning: ShellState.spawnRef !== '' || ShellState.rebindId !== ''
    readonly property var views: ['catalog', 'placed'].concat(ShellState.npcsSupported ? ['characters'] : [])
    readonly property var selected: Objects.selectedInstance(instances, ShellState.selectedObject)
    readonly property bool hasUser: instances.some(i => i.source === 'user')
    readonly property bool hasAuthored: instances.some(i => i.source === 'authored')
    readonly property bool compact: height < 620

    function setView(next) {
        ShellState.objectsView = next;
        confirm = '';
        Qt.callLater(focusView);
    }
    function focusView() {
        if (spawning) spawnPanel.forceActiveFocus();
        else if (view === 'placed') placedList.forceActiveFocus();
        else if (view === 'characters') npcPanel.focusList();
        else grid.forceActiveFocus();
    }
    onSpawningChanged: Qt.callLater(focusView)
    onVisibleChanged: { if (visible && ShellState.director) Qt.callLater(focusView); }
    onShownChanged: cursor = Math.max(0, Math.min(cursor, shown.length - 1))
    onInstancesChanged: syncSelection()
    onViewChanged: syncSelection()
    Connections { target: ShellState; function onSelectedObjectChanged() { root.syncSelection(); } }
    // Placed always shows a configure panel when there is anything to configure.
    function syncSelection() {
        if (view === 'placed' && !selected && instances.length) ShellState.selectedObject = instances[0].id;
    }

    function add(entry) {
        if (Npcs.isCharacter(entry)) { if (Npcs.canSpawn(entry) && ShellState.npcsSupported) ShellState.startSpawn(entry.ref); return; }
        if (Objects.canAdd(entry) && ShellState.objectsCan('objects.pocket')) ShellState.pocketObject(entry.ref);
    }
    function moveCursor(key) {
        var next = Objects.gridMove(cursor, shown.length, grid.columns, key);
        if (next < 0) return;
        cursor = next;
        grid.positionViewAtIndex(next, GridView.Contain);
    }
    function selectAt(index) {
        if (index < 0 || index >= instances.length) return;
        ShellState.selectedObject = instances[index].id;
        placedList.positionViewAtIndex(index, ListView.Contain);
        confirm = '';
    }
    function run(actionId) {
        var request = Objects.sectionAction(selected, actionId);
        if (!request || !ShellState.objectsCan(request.method)) return;
        // Only the actions the panel offers for this instance (and not while locked).
        var section = Objects.panelSections(selected).find(s => s.id === (actionId === 'lock' ? 'lock' : 'remove'));
        if (!section || !section.visible) return;
        if (actionId !== 'lock' && !(section.actions || []).some(a => a.id === actionId && a.enabled)) return;
        ShellState.objectAction(request.method, request.params);
    }
    function confirmed(kind, method, params) {
        if (confirm === kind) { confirm = ''; ShellState.objectAction(method, params); }
        else { confirm = kind; confirmTimer.restart(); }
    }
    Timer { id: confirmTimer; interval: 6000; onTriggered: root.confirm = '' }

    Keys.onPressed: (event) => {
        if (!ShellState.objectsSupported || root.spawning) return;
        if (event.modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)) return;
        if (event.key === Qt.Key_V) { root.setView(root.views[(root.views.indexOf(root.view) + 1) % root.views.length]); event.accepted = true; }
        else if (root.view === 'catalog' && event.key === Qt.Key_Slash) { search.forceActiveFocus(); event.accepted = true; }
        else if (root.view === 'placed' && root.selected) {
            var map = {}; map[Qt.Key_L] = 'lock'; map[Qt.Key_H] = 'hide'; map[Qt.Key_R] = 'reset'; map[Qt.Key_Delete] = 'remove';
            if (map[event.key]) { root.run(map[event.key]); event.accepted = true; }
        }
    }

    HudLabel {
        anchors.centerIn: parent
        width: Math.min(parent.width - 40, 640)
        visible: !ShellState.objectsSupported
        text: 'Objects need core IPC 0.22.'
        color: Tokens.muted; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: root.compact ? 10 : 16
        visible: ShellState.objectsSupported

        // ---- View switch, feedback and usage ----
        RowLayout {
            Layout.fillWidth: true
            spacing: 16
            Segmented {
                objectName: 'objectsView'
                Layout.preferredWidth: ShellState.npcsSupported ? 450 : 300
                model: [{id: 'catalog', label: 'Catalog'}, {id: 'placed', label: 'Placed  ·  ' + root.instances.length}]
                       .concat(ShellState.npcsSupported ? [{id: 'characters', label: 'Characters  ·  ' + ShellState.characterInstances.length}] : [])
                current: root.view
                onPicked: (id) => root.setView(id)
            }
            HudLabel {
                objectName: 'objectsFeedback'
                Layout.fillWidth: true
                text: ShellState.objectFeedback ? ShellState.objectFeedback.text
                    : !ShellState.objectsControl ? 'Read only: this session has no objects.control grant.' : ''
                color: ShellState.objectFeedback && ShellState.objectFeedback.level === 'warning' ? Tokens.warning : ShellState.objectFeedback ? Tokens.positive : Tokens.muted
                font.pixelSize: 13
            }
            ColumnLayout {
                objectName: 'objectsUsage'
                Layout.maximumWidth: Math.max(240, root.width * .42)
                visible: !!root.objectsState
                spacing: 4
                HudLabel {
                    Layout.alignment: Qt.AlignRight
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignRight
                    text: 'MY OBJECTS IN THIS WORLD'
                    color: Tokens.gold; font.pixelSize: 10; font.letterSpacing: 1.5
                }
                HudLabel {
                    objectName: 'objectsUsageText'
                    Layout.alignment: Qt.AlignRight
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignRight
                    text: root.objectsState ? Objects.usageText(root.objectsState.usage, root.objectsState.limits) : ''
                    font.family: Tokens.mono; font.pixelSize: 11
                    color: Objects.usageRows(root.objectsState ? root.objectsState.usage : null, root.objectsState ? root.objectsState.limits : null)
                           .some(r => r.fraction >= 1) ? Tokens.warning : Tokens.muted
                }
            }
        }

        // ---- A route being drawn (paths.draw in progress) ----
        Rectangle {
            objectName: 'npcDrawing'
            Layout.fillWidth: true
            Layout.preferredHeight: 56
            visible: !!ShellState.npcDrawing
            radius: 3
            color: Tokens.raised
            border.color: Tokens.gold
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16; anchors.rightMargin: 8
                spacing: 12
                HudLabel { text: '✎'; color: Tokens.gold; font.pixelSize: 18 }
                HudLabel {
                    Layout.fillWidth: true
                    text: ShellState.drawingHint ? ShellState.drawingHint.title + '  ·  ' + ShellState.drawingHint.pathId + (ShellState.drawingHint.detail ? '  ·  ' + ShellState.drawingHint.detail : '') : ''
                    font.pixelSize: 14; elide: Text.ElideRight
                }
                ActionButton { objectName: 'npc-draw-done'; primary: true; text: 'Done'; enabled: ShellState.npcsCan('paths.finish'); onClicked: ShellState.finishDrawing() }
                ActionButton { objectName: 'npc-draw-cancel'; text: 'Cancel'; enabled: ShellState.npcsCan('paths.remove'); onClicked: ShellState.cancelDrawing() }
            }
        }

        // ---- Spawn / rebind (IPC 0.23) ----
        NpcSpawn {
            id: spawnPanel
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.spawning
        }

        // ---- Characters (IPC 0.23) ----
        NpcPanel {
            id: npcPanel
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.view === 'characters' && !root.spawning
        }

        // ---- Catalog ----
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.view === 'catalog' && !root.spawning
            spacing: root.compact ? 8 : 12

            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Segmented {
                    objectName: 'objectsSource'
                    Layout.preferredWidth: root.width < 1100 ? 300 : 380
                    model: Objects.SOURCES
                    current: root.source
                    onPicked: (id) => root.source = id
                }
                Choice {
                    objectName: 'objectsCategory'
                    Layout.preferredWidth: 200
                    model: ['All categories'].concat(root.cats.map(c => Objects.categoryLabel(c)))
                    currentIndex: root.category ? root.cats.indexOf(root.category) + 1 : 0
                    onActivated: (index) => root.category = index > 0 ? root.cats[index - 1] : ''
                }
                TextField {
                    id: search
                    objectName: 'objectsSearch'
                    Layout.fillWidth: true
                    Layout.minimumWidth: 120
                    implicitHeight: 40
                    placeholderText: 'Search names and tags  ·  /'
                    color: Tokens.text
                    placeholderTextColor: Tokens.muted
                    selectionColor: Tokens.accent
                    selectedTextColor: Tokens.ink
                    font.family: Tokens.sans; font.pixelSize: 14
                    leftPadding: 12; rightPadding: 12
                    onTextChanged: root.query = text
                    Keys.onDownPressed: grid.forceActiveFocus()
                    Keys.onReturnPressed: grid.forceActiveFocus()
                    Keys.onEnterPressed: grid.forceActiveFocus()
                    background: Rectangle { radius: Tokens.radius; color: Tokens.panel; border.width: parent.activeFocus ? 2 : 1; border.color: parent.activeFocus ? Tokens.gold : Tokens.line }
                }
                HudLabel {
                    objectName: 'objectsCount'
                    text: root.shown.length + ' / ' + root.entries.length
                    font.family: Tokens.mono; font.pixelSize: 12; color: Tokens.muted
                }
            }

            GridView {
                id: grid
                objectName: 'objectsCatalog'
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                focus: true
                readonly property int columns: Math.max(1, Math.floor(width / 270))
                cellWidth: Math.floor(width / columns)
                cellHeight: (root.compact ? 262 : 336) + 14
                model: root.shown
                currentIndex: root.cursor
                keyNavigationEnabled: false
                highlightFollowsCurrentItem: false
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar {}
                Keys.onUpPressed: root.moveCursor('previous')
                Keys.onDownPressed: root.moveCursor('next')
                Keys.onPressed: (event) => {
                    var key = {};
                    key[Qt.Key_PageUp] = 'rowUp'; key[Qt.Key_PageDown] = 'rowDown'; key[Qt.Key_Home] = 'home'; key[Qt.Key_End] = 'end';
                    if (key[event.key]) { root.moveCursor(key[event.key]); event.accepted = true; }
                }
                Keys.onReturnPressed: root.add(root.shown[root.cursor])
                Keys.onEnterPressed: root.add(root.shown[root.cursor])

                delegate: Item {
                    required property var modelData
                    required property int index
                    width: grid.cellWidth
                    height: grid.cellHeight
                    ObjectCard {
                        x: 0; y: 0
                        width: parent.width - 14
                        height: parent.height - 14
                        entry: parent.modelData
                        compact: root.compact
                        current: grid.activeFocus && parent.index === root.cursor
                        onPicked: { root.cursor = parent.index; grid.forceActiveFocus(); }
                        onAdd: root.add(parent.modelData)
                        onSpawn: root.add(parent.modelData)
                    }
                }

                HudLabel {
                    anchors.centerIn: parent
                    width: Math.min(parent.width - 40, 640)
                    visible: !root.shown.length
                    text: !root.entries.length
                          ? (ShellState.objectCatalogLoaded ? 'No objects yet. Put objects in your objects folder or install a library.' : 'Loading the catalog…')
                          : 'Nothing matches these filters.'
                    color: Tokens.muted; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter
                }
            }
        }

        // ---- Placed ----
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.view === 'placed' && !root.spawning
            spacing: 20

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

                    HudLabel { Layout.fillWidth: true; text: 'IN THIS WORLD  /  ' + root.instances.length; color: Tokens.gold; font.pixelSize: 11; font.letterSpacing: 2 }

                    ListView {
                        id: placedList
                        objectName: 'objectsPlaced'
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: root.instances
                        keyNavigationEnabled: false
                        highlightFollowsCurrentItem: false
                        boundsBehavior: Flickable.StopAtBounds
                        ScrollBar.vertical: ScrollBar {}
                        readonly property int selectedIndex: root.instances.findIndex(i => i.id === ShellState.selectedObject)
                        onSelectedIndexChanged: { if (selectedIndex >= 0) positionViewAtIndex(selectedIndex, ListView.Contain); }
                        Keys.onUpPressed: root.selectAt(Math.max(0, selectedIndex - 1))
                        Keys.onDownPressed: root.selectAt(Math.min(root.instances.length - 1, selectedIndex + 1))
                        Keys.onReturnPressed: configure.focusFirst()
                        Keys.onEnterPressed: configure.focusFirst()

                        delegate: Item {
                            id: row
                            required property var modelData
                            required property int index
                            readonly property bool selected: modelData.id === ShellState.selectedObject
                            readonly property string level: Objects.stateLevel(modelData)
                            objectName: 'placedRow:' + modelData.id
                            Accessible.role: Accessible.ListItem
                            Accessible.name: modelData.name
                            Accessible.description: Objects.sourceLabel(modelData.source) + ' · ' + Objects.stateText(modelData) + (modelData.locked ? ' · locked' : '') + ' · ID ' + modelData.id
                            Accessible.selected: selected
                            width: placedList.width - 8
                            height: 60

                            Rectangle {
                                anchors.fill: parent
                                anchors.topMargin: 2
                                radius: 3
                                color: row.selected ? Tokens.raised : 'transparent'
                                border.width: row.selected && placedList.activeFocus ? 2 : 0
                                border.color: Tokens.gold
                            }
                            Rectangle { x: 0; y: 10; width: 3; height: parent.height - 16; color: row.modelData.source === 'user' ? Tokens.gold : Tokens.accent; opacity: .8 }
                            Column {
                                x: 14; y: 9; width: parent.width - 22
                                spacing: 4
                                RowLayout {
                                    width: parent.width
                                    spacing: 8
                                    HudLabel { Layout.fillWidth: true; text: row.modelData.name; font.pixelSize: 15 }
                                    // A workspace screen (IPC 0.27): the workspace it shows.
                                    Rectangle {
                                        objectName: 'placedScreen'
                                        visible: screenText.text !== ''
                                        Layout.preferredWidth: screenText.implicitWidth
                                        Layout.preferredHeight: 18
                                        radius: 2
                                        color: 'transparent'
                                        border.color: Tokens.accent
                                        HudLabel { id: screenText; anchors.centerIn: parent; leftPadding: 6; rightPadding: 6; text: Objects.screenTag(row.modelData); font.pixelSize: 9; font.letterSpacing: 1.2; color: Tokens.accent }
                                    }
                                    Rectangle {
                                        objectName: 'placedLocked'
                                        visible: row.modelData.locked
                                        Layout.preferredWidth: lockText.implicitWidth
                                        Layout.preferredHeight: 18
                                        radius: 2
                                        color: 'transparent'
                                        border.color: Tokens.gold
                                        HudLabel { id: lockText; anchors.centerIn: parent; leftPadding: 6; rightPadding: 6; text: 'LOCKED'; font.pixelSize: 9; font.letterSpacing: 1.2; color: Tokens.gold }
                                    }
                                }
                                RowLayout {
                                    width: parent.width
                                    spacing: 8
                                    HudLabel {
                                        Layout.fillWidth: true
                                        text: Objects.sourceLabel(row.modelData.source) + '  ·  ' + Objects.stateText(row.modelData)
                                        font.pixelSize: 12
                                        color: row.level === 'warning' ? Tokens.warning : row.level === 'busy' ? Tokens.accent : Tokens.muted
                                    }
                                    // The instance id (machines read source com.hyprune.sources.<id>).
                                    HudLabel {
                                        objectName: 'placedId'
                                        Layout.maximumWidth: parent.width / 2
                                        text: row.modelData.id
                                        font.family: Tokens.mono; font.pixelSize: 11; color: Tokens.muted
                                    }
                                }
                            }
                            MouseArea {
                                anchors.fill: parent
                                onClicked: { placedList.forceActiveFocus(); root.selectAt(row.index); }
                                onDoubleClicked: { root.selectAt(row.index); configure.focusFirst(); }
                            }
                        }

                        HudLabel {
                            anchors.centerIn: parent
                            width: parent.width - 20
                            visible: !root.instances.length
                            text: 'No objects in this world yet. Add one from the Catalog.'
                            color: Tokens.muted; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: Tokens.line }
                    ActionButton {
                        objectName: 'objects-reset-all'
                        Layout.fillWidth: true
                        text: root.confirm === 'reset-all' ? 'Show and reset all? Press again' : 'Show and reset authored objects'
                        enabled: root.hasAuthored && ShellState.objectsCan('objects.reset')
                        onClicked: root.confirmed('reset-all', 'objects.reset', {all: true})
                    }
                    ActionButton {
                        objectName: 'objects-remove-all'
                        Layout.fillWidth: true
                        text: root.confirm === 'remove-all' ? 'Remove all of them? Press again' : 'Remove my objects'
                        enabled: root.hasUser && ShellState.objectsCan('objects.remove')
                        onClicked: root.confirmed('remove-all', 'objects.remove', {all: true})
                    }
                }
            }

            ScrollView {
                id: configureScroll
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                contentWidth: availableWidth

                ColumnLayout {
                    width: Math.min(configureScroll.availableWidth - 16, 980)
                    spacing: 14
                    HudLabel {
                        Layout.fillWidth: true
                        visible: !root.selected
                        text: root.instances.length ? 'Select an object to configure it.' : 'Objects you add appear here, with the world\'s own.'
                        color: Tokens.muted; font.pixelSize: 14
                    }
                    ObjectConfigure {
                        id: configure
                        Layout.fillWidth: true
                        visible: !!root.selected
                        instance: root.selected
                        entry: root.selected ? Objects.entryFor(root.entries, root.selected.ref) : null
                    }
                }
            }
        }
    }
}
