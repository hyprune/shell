import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../Library.js" as Library
import "../Objects.js" as Objects

// Director > Library (RFC-0015 phase 1): worlds and libraries from the official index, the
// community registry and custom sources, through the hyprune CLI ($HYPRUNE_CLI, else hyprune;
// no core IPC). Browse: cards with filters by source and type and a search over names,
// summaries and tags; Install and Update open the plan for confirmation (LibraryJob).
// Installed: every install with its current and previous tag, source, pin and newer tag, and
// Update, Roll back, Pin / Unpin and Remove. Sources: the list with Refresh, enable / disable
// and remove (custom), and Add source. Index text is plain text; nothing opens a link.
// Keys: V switches the view, / searches, Up/Down move, Enter installs or updates (Browse),
// U update, P pin or unpin (Installed), R refresh (Sources); Left/Right change the Director view.
FocusScope {
    id: root
    objectName: 'directorLibrary'
    property string source: 'all'
    property string type: 'all'
    property string query: ''
    property int cursor: 0               // Browse card under the keyboard cursor
    property string selected: ''         // Installed: the selected install id
    property string selectedSource: ''   // Sources: the selected source id
    property string confirm: ''          // 'remove:<id>' | 'source:<id>' waiting for a second press
    property string formUrl: ''
    property string formLabel: ''
    property string formHash: ''
    readonly property string view: ShellState.libraryView
    readonly property var entries: ShellState.libraryEntries
    readonly property var shown: Library.filterEntries(entries, {source: source, type: type, query: query})
    readonly property var choices: Library.sourceChoices(ShellState.librarySources, entries)
    readonly property var installs: ShellState.libraryInstalls
    readonly property var install: installs.find(i => i.id === selected) || null
    readonly property var form: Library.sourceForm(formUrl, formLabel, formHash)
    readonly property bool jobPanel: !!ShellState.libraryJob && ShellState.libraryJob.panel
    readonly property bool compact: height < 620

    function setView(next) {
        ShellState.libraryView = next;
        confirm = '';
        Qt.callLater(focusView);
    }
    function focusView() {
        if (jobPanel) jobView.forceActiveFocus();
        else if (view === 'installed') installedList.forceActiveFocus();
        else if (view === 'sources') sourcesList.forceActiveFocus();
        else grid.forceActiveFocus();
    }
    onJobPanelChanged: Qt.callLater(focusView)
    onVisibleChanged: { if (visible && ShellState.director) Qt.callLater(focusView); }
    onShownChanged: cursor = Math.max(0, Math.min(cursor, shown.length - 1))
    onInstallsChanged: { if (!install && installs.length) selected = installs[0].id; }

    function act(entry) {
        var a = Library.entryAction(entry);
        if (!a.enabled || ShellState.libraryBusy) return;
        ShellState.libraryPlan(a.kind === 'update' ? 'update' : 'install', entry);
    }
    function moveCursor(key) {
        var next = Objects.gridMove(cursor, shown.length, grid.columns, key);
        if (next < 0) return;
        cursor = next;
        grid.positionViewAtIndex(next, GridView.Contain);
    }
    function selectInstall(index) {
        if (index < 0 || index >= installs.length) return;
        selected = installs[index].id;
        installedList.positionViewAtIndex(index, ListView.Contain);
        confirm = '';
    }
    function runInstall(actionId) {
        var a = Library.installActions(install).find(x => x.id === actionId);
        if (!a || !a.enabled || ShellState.libraryBusy) return;
        if (actionId === 'update') ShellState.libraryPlan('update', install);
        else if (actionId === 'remove') confirmed('remove:' + install.id, () => ShellState.libraryInstallAction('remove', install));
        else ShellState.libraryInstallAction(actionId, install);
    }
    function confirmed(kind, run) {
        if (confirm === kind) { confirm = ''; run(); }
        else { confirm = kind; confirmTimer.restart(); }
    }
    Timer { id: confirmTimer; interval: 6000; onTriggered: root.confirm = '' }
    function addSource() {
        if (!form.ok || ShellState.libraryBusy) return;
        if (ShellState.librarySource('add', '', form.args)) { formUrl = ''; formLabel = ''; formHash = ''; urlField.text = ''; labelField.text = ''; hashField.text = ''; }
    }

    Keys.onPressed: (event) => {
        if (root.jobPanel) return;
        if (event.modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)) return;
        if (event.key === Qt.Key_V) { root.setView(Library.VIEWS[(Library.VIEWS.findIndex(v => v.id === root.view) + 1) % Library.VIEWS.length].id); event.accepted = true; }
        else if (root.view === 'browse' && event.key === Qt.Key_Slash) { search.forceActiveFocus(); event.accepted = true; }
        else if (root.view === 'installed' && root.install && event.key === Qt.Key_U) { root.runInstall('update'); event.accepted = true; }
        else if (root.view === 'installed' && root.install && event.key === Qt.Key_P) { root.runInstall(root.install.pinned ? 'unpin' : 'pin'); event.accepted = true; }
        else if (root.view === 'sources' && event.key === Qt.Key_R && !ShellState.libraryBusy) { ShellState.librarySource('refresh', root.selectedSource); event.accepted = true; }
    }

    component Caption: HudLabel { Layout.fillWidth: true; color: Tokens.gold; font.pixelSize: Tokens.caption; font.letterSpacing: 1.5 }
    component Field: TextField {
        Layout.fillWidth: true
        implicitHeight: 40
        color: Tokens.text
        placeholderTextColor: Tokens.muted
        selectionColor: Tokens.accent
        selectedTextColor: Tokens.ink
        font.family: Tokens.sans; font.pixelSize: 14
        leftPadding: 12; rightPadding: 12
        background: Rectangle { radius: Tokens.radius; color: Tokens.panel; border.width: parent.activeFocus ? 2 : 1; border.color: parent.activeFocus ? Tokens.gold : Tokens.line }
    }
    component Badge: Rectangle {
        property string label: ''
        property color tone: Tokens.accent
        Layout.preferredWidth: badgeText.implicitWidth
        Layout.preferredHeight: 18
        implicitWidth: badgeText.implicitWidth
        implicitHeight: 18
        radius: 2
        color: 'transparent'
        border.color: tone
        HudLabel { id: badgeText; anchors.centerIn: parent; leftPadding: 6; rightPadding: 6; text: parent.label; font.pixelSize: 9; font.letterSpacing: 1.2; color: parent.tone }
    }
    function toneColor(tone) {
        return tone === 'warning' ? Tokens.warning : tone === 'gold' ? Tokens.gold : tone === 'muted' ? Tokens.muted : tone === 'positive' ? Tokens.positive : Tokens.accent;
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: root.compact ? 10 : 16

        // ---- View switch and feedback ----
        RowLayout {
            Layout.fillWidth: true
            spacing: 16
            visible: !root.jobPanel
            Segmented {
                objectName: 'libraryView'
                Layout.preferredWidth: 450
                model: [{id: 'browse', label: 'Browse  ·  ' + root.entries.length}, {id: 'installed', label: 'Installed  ·  ' + root.installs.length},
                        {id: 'sources', label: 'Sources  ·  ' + ShellState.librarySources.length}]
                current: root.view
                onPicked: (id) => root.setView(id)
            }
            HudLabel {
                objectName: 'libraryFeedback'
                Layout.fillWidth: true
                text: ShellState.libraryReadError ? ShellState.libraryReadError
                    : ShellState.libraryBusy && ShellState.libraryJob ? 'Working: ' + ShellState.libraryJob.args.slice(0, 2).join(' ') + (ShellState.libraryJob.stage ? '  ·  ' + ShellState.libraryJob.stage : '') + '…'
                    : ShellState.libraryFeedback ? ShellState.libraryFeedback.text : ''
                color: ShellState.libraryReadError || (ShellState.libraryFeedback && ShellState.libraryFeedback.level === 'warning') ? Tokens.warning
                     : ShellState.libraryFeedback && !ShellState.libraryBusy ? Tokens.positive : Tokens.muted
                font.pixelSize: 13
            }
            ActionButton {
                objectName: 'library-refresh-all'
                text: 'Refresh sources'
                enabled: !ShellState.libraryBusy
                onClicked: ShellState.librarySource('refresh', '')
            }
        }

        // ---- Install / update job ----
        LibraryJob {
            id: jobView
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.jobPanel
        }

        // ---- Browse ----
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.view === 'browse' && !root.jobPanel
            spacing: root.compact ? 8 : 12

            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Segmented {
                    objectName: 'libraryType'
                    Layout.preferredWidth: root.width < 1100 ? 260 : 320
                    model: Library.TYPES
                    current: root.type
                    onPicked: (id) => root.type = id
                }
                Choice {
                    objectName: 'librarySource'
                    Layout.preferredWidth: root.width < 1100 ? 220 : 280
                    model: root.choices.map(c => c.label)
                    currentIndex: Math.max(0, root.choices.findIndex(c => c.id === root.source))
                    onActivated: (index) => root.source = root.choices[index].id
                }
                TextField {
                    id: search
                    objectName: 'librarySearch'
                    Layout.fillWidth: true
                    Layout.minimumWidth: 120
                    implicitHeight: 40
                    placeholderText: 'Search names, summaries and tags  ·  /'
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
                    objectName: 'libraryCount'
                    text: root.shown.length + ' / ' + root.entries.length
                    font.family: Tokens.mono; font.pixelSize: 12; color: Tokens.muted
                }
            }

            GridView {
                id: grid
                objectName: 'libraryBrowse'
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                focus: true
                readonly property int columns: Math.max(1, Math.floor(width / 290))
                cellWidth: Math.floor(width / columns)
                cellHeight: (root.compact ? 270 : 344) + 14
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
                Keys.onReturnPressed: root.act(root.shown[root.cursor])
                Keys.onEnterPressed: root.act(root.shown[root.cursor])

                delegate: Item {
                    required property var modelData
                    required property int index
                    width: grid.cellWidth
                    height: grid.cellHeight
                    LibraryCard {
                        x: 0; y: 0
                        width: parent.width - 14
                        height: parent.height - 14
                        entry: parent.modelData
                        compact: root.compact
                        current: grid.activeFocus && parent.index === root.cursor
                        onPicked: { root.cursor = parent.index; grid.forceActiveFocus(); }
                        onAct: root.act(parent.modelData)
                    }
                }

                HudLabel {
                    anchors.centerIn: parent
                    width: Math.min(parent.width - 40, 640)
                    visible: !root.shown.length
                    text: !root.entries.length
                          ? (ShellState.libraryLoaded ? 'No entries in the cached indexes. Refresh the sources, or add one under Sources.' : ShellState.libraryReadError ? '' : 'Reading the sources…')
                          : 'Nothing matches these filters.'
                    color: Tokens.muted; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter
                }
            }
        }

        // ---- Installed ----
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.view === 'installed' && !root.jobPanel
            spacing: 20

            Rectangle {
                Layout.preferredWidth: root.width < 1100 ? 320 : 420
                Layout.fillHeight: true
                color: Tokens.panel
                border.color: Tokens.line
                radius: 3

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 10
                    HudLabel { Layout.fillWidth: true; text: 'INSTALLED  /  ' + root.installs.length; color: Tokens.gold; font.pixelSize: 11; font.letterSpacing: 2 }

                    ListView {
                        id: installedList
                        objectName: 'libraryInstalled'
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: root.installs
                        keyNavigationEnabled: false
                        highlightFollowsCurrentItem: false
                        boundsBehavior: Flickable.StopAtBounds
                        ScrollBar.vertical: ScrollBar {}
                        readonly property int selectedIndex: root.installs.findIndex(i => i.id === root.selected)
                        Keys.onUpPressed: root.selectInstall(Math.max(0, selectedIndex - 1))
                        Keys.onDownPressed: root.selectInstall(Math.min(root.installs.length - 1, selectedIndex + 1))

                        delegate: Item {
                            id: row
                            required property var modelData
                            required property int index
                            readonly property bool current: modelData.id === root.selected
                            objectName: 'installRow:' + modelData.id
                            Accessible.role: Accessible.ListItem
                            Accessible.name: Library.installName(modelData, root.entries)
                            Accessible.description: Library.installSource(modelData) + ' · ' + (modelData.tag || modelData.version)
                            Accessible.selected: current
                            width: installedList.width - 8
                            height: 64

                            Rectangle {
                                anchors.fill: parent
                                anchors.topMargin: 2
                                radius: 3
                                color: row.current ? Tokens.raised : 'transparent'
                                border.width: row.current && installedList.activeFocus ? 2 : 0
                                border.color: Tokens.gold
                            }
                            Rectangle { x: 0; y: 10; width: 3; height: parent.height - 16; color: row.modelData.type === 'library' ? Tokens.violet : Tokens.accent; opacity: .8 }
                            Column {
                                x: 14; y: 9; width: parent.width - 22
                                spacing: 4
                                RowLayout {
                                    width: parent.width
                                    spacing: 6
                                    HudLabel { Layout.fillWidth: true; text: Library.installName(row.modelData, root.entries); font.pixelSize: 15 }
                                    Repeater {
                                        model: Library.installBadges(row.modelData)
                                        delegate: Badge { required property var modelData; objectName: 'installBadge:' + modelData.id; label: modelData.label; tone: root.toneColor(modelData.tone) }
                                    }
                                }
                                HudLabel {
                                    width: parent.width
                                    text: Library.typeLabel(row.modelData.type) + '  ·  ' + (row.modelData.tag || row.modelData.version) + '  ·  ' + Library.installSource(row.modelData)
                                    font.pixelSize: 12
                                    color: Tokens.muted
                                }
                            }
                            MouseArea { anchors.fill: parent; onClicked: { installedList.forceActiveFocus(); root.selectInstall(row.index); } }
                        }

                        HudLabel {
                            anchors.centerIn: parent
                            width: parent.width - 20
                            visible: !root.installs.length
                            text: ShellState.libraryLoaded ? 'Nothing installed yet. Install a world or library from Browse.' : ''
                            color: Tokens.muted; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter
                        }
                    }
                }
            }

            ScrollView {
                id: installScroll
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                contentWidth: availableWidth

                ColumnLayout {
                    objectName: 'libraryInstall'
                    width: Math.min(installScroll.availableWidth - 16, 980)
                    spacing: 12
                    visible: !!root.install
                    HudLabel { Layout.fillWidth: true; text: root.install ? Library.typeLabel(root.install.type).toUpperCase() + '  /  ' + root.install.id : ''; color: Tokens.gold; font.pixelSize: 11; font.letterSpacing: 1.8 }
                    HudLabel { Layout.fillWidth: true; text: root.install ? Library.installName(root.install, root.entries) : ''; font.pixelSize: 24; font.weight: Font.Light }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: 16
                        rowSpacing: 6
                        Repeater {
                            model: Library.installFacts(root.install)
                            delegate: HudLabel {
                                required property var modelData
                                required property int index
                                Layout.row: index; Layout.column: 0
                                Layout.preferredWidth: 110
                                text: modelData.label; color: Tokens.muted; font.pixelSize: 12
                            }
                        }
                        Repeater {
                            model: Library.installFacts(root.install)
                            delegate: HudLabel {
                                required property var modelData
                                required property int index
                                objectName: 'installFact:' + modelData.label
                                Layout.row: index; Layout.column: 1
                                Layout.fillWidth: true
                                text: modelData.value; font.pixelSize: 13
                                font.family: modelData.label === 'Folder' ? Tokens.mono : Tokens.sans
                                wrapMode: Text.WrapAnywhere
                            }
                        }
                    }
                    Rectangle { Layout.fillWidth: true; height: 1; color: Tokens.line }
                    HudLabel {
                        Layout.fillWidth: true
                        visible: !!root.install && root.install.managed === 'system'
                        text: 'Managed by the system configuration: update, roll back or remove it there.'
                        color: Tokens.muted; font.pixelSize: 13; wrapMode: Text.Wrap
                    }
                    HudLabel {
                        Layout.fillWidth: true
                        visible: !!root.install && root.install.pinned && !!root.install.newerTag
                        text: 'Pinned: updates skip it until you unpin it.'
                        color: Tokens.gold; font.pixelSize: 13; wrapMode: Text.Wrap
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 10
                        Repeater {
                            model: Library.installActions(root.install)
                            delegate: ActionButton {
                                required property var modelData
                                objectName: 'library-install-' + modelData.id
                                text: modelData.id === 'remove' && root.confirm === 'remove:' + (root.install ? root.install.id : '') ? 'Remove it? Press again' : modelData.label
                                primary: modelData.id === 'update' && modelData.enabled
                                enabled: modelData.enabled && !ShellState.libraryBusy
                                onClicked: root.runInstall(modelData.id)
                            }
                        }
                    }
                }
            }
        }

        // ---- Sources ----
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.view === 'sources' && !root.jobPanel
            spacing: 20

            ListView {
                id: sourcesList
                objectName: 'librarySources'
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 8
                model: ShellState.librarySources
                keyNavigationEnabled: false
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar {}
                readonly property int selectedIndex: ShellState.librarySources.findIndex(s => s.id === root.selectedSource)
                Keys.onUpPressed: { var i = Math.max(0, selectedIndex - 1); if (ShellState.librarySources[i]) root.selectedSource = ShellState.librarySources[i].id; }
                Keys.onDownPressed: { var i = Math.min(ShellState.librarySources.length - 1, selectedIndex + 1); if (ShellState.librarySources[i]) root.selectedSource = ShellState.librarySources[i].id; }

                delegate: Rectangle {
                    id: sourceRow
                    required property var modelData
                    readonly property bool current: modelData.id === root.selectedSource
                    readonly property var status: Library.sourceStatus(modelData)
                    objectName: 'sourceRow:' + modelData.id
                    width: sourcesList.width - 12
                    height: 92
                    radius: 3
                    color: current ? Tokens.raised : Tokens.panel
                    border.color: current && sourcesList.activeFocus ? Tokens.gold : Tokens.line
                    border.width: current && sourcesList.activeFocus ? 2 : 1
                    opacity: modelData.enabled ? 1 : 0.75
                    Accessible.role: Accessible.ListItem
                    Accessible.name: Library.tierLabel(modelData)
                    Accessible.description: Library.sourceKind(modelData) + ' · ' + status.text
                    MouseArea { anchors.fill: parent; onClicked: { root.selectedSource = sourceRow.modelData.id; sourcesList.forceActiveFocus(); } }
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 16; anchors.rightMargin: 12
                        spacing: 12
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                HudLabel { objectName: 'sourceLabel'; text: Library.tierLabel(sourceRow.modelData); font.pixelSize: 16; Layout.maximumWidth: sourceRow.width * .45 }
                                Badge { label: Library.sourceKind(sourceRow.modelData).toUpperCase(); tone: sourceRow.modelData.builtin ? Tokens.accent : Tokens.gold }
                                Badge { visible: !sourceRow.modelData.enabled; label: 'DISABLED'; tone: Tokens.muted }
                                Item { Layout.fillWidth: true }
                            }
                            HudLabel { Layout.fillWidth: true; text: Library.sourceLocation(sourceRow.modelData); font.family: Tokens.mono; font.pixelSize: 11; color: Tokens.muted; elide: Text.ElideMiddle }
                            HudLabel {
                                objectName: 'sourceStatus'
                                Layout.fillWidth: true
                                text: sourceRow.status.text
                                font.pixelSize: 12
                                color: sourceRow.status.level === 'warning' ? Tokens.warning : Tokens.muted
                            }
                        }
                        ActionButton {
                            objectName: 'source-refresh:' + sourceRow.modelData.id
                            text: 'Refresh'
                            implicitHeight: 36
                            enabled: sourceRow.modelData.enabled && !ShellState.libraryBusy
                            onClicked: ShellState.librarySource('refresh', sourceRow.modelData.id)
                        }
                        ActionButton {
                            objectName: 'source-toggle:' + sourceRow.modelData.id
                            text: sourceRow.modelData.enabled ? 'Disable' : 'Enable'
                            implicitHeight: 36
                            enabled: !ShellState.libraryBusy && !sourceRow.modelData.system
                            onClicked: ShellState.librarySource(sourceRow.modelData.enabled ? 'disable' : 'enable', sourceRow.modelData.id)
                        }
                        ActionButton {
                            objectName: 'source-remove:' + sourceRow.modelData.id
                            visible: Library.removable(sourceRow.modelData)
                            text: root.confirm === 'source:' + sourceRow.modelData.id ? 'Remove? Again' : 'Remove'
                            implicitHeight: 36
                            enabled: !ShellState.libraryBusy
                            onClicked: root.confirmed('source:' + sourceRow.modelData.id, () => ShellState.librarySource('remove', sourceRow.modelData.id))
                        }
                    }
                }

                HudLabel {
                    anchors.centerIn: parent
                    width: parent.width - 20
                    visible: !ShellState.librarySources.length
                    text: ShellState.libraryLoaded ? 'No sources.' : ''
                    color: Tokens.muted; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter
                }
            }

            Rectangle {
                objectName: 'librarySourceForm'
                Layout.preferredWidth: root.width < 1100 ? 340 : 440
                Layout.fillHeight: true
                color: Tokens.panel
                border.color: Tokens.line
                radius: 3

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 10
                    Caption { text: 'ADD SOURCE' }
                    HudLabel { Layout.fillWidth: true; text: 'An index URL, a GitHub repository or a package URL.'; color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap }
                    Field {
                        id: urlField
                        objectName: 'source-url'
                        placeholderText: 'https://…  or  github:owner/repo[/name]'
                        font.family: Tokens.mono; font.pixelSize: 13
                        onTextChanged: root.formUrl = text
                    }
                    Field {
                        id: labelField
                        objectName: 'source-label'
                        placeholderText: 'Label (optional, up to 48 characters)'
                        maximumLength: Library.LABEL_MAX
                        onTextChanged: root.formLabel = text
                    }
                    Field {
                        id: hashField
                        objectName: 'source-sha256'
                        visible: root.form.needsHash
                        placeholderText: 'sha256 of the archive (64 hex digits)'
                        font.family: Tokens.mono; font.pixelSize: 12
                        maximumLength: 64
                        onTextChanged: root.formHash = text
                    }
                    HudLabel {
                        objectName: 'source-preview'
                        Layout.fillWidth: true
                        visible: root.form.ok
                        text: 'Shown as  Custom: ' + (root.formLabel.trim() || (root.formUrl.indexOf('github:') === 0 ? root.formUrl.slice(7).split('/').slice(0, 2).join('/') : 'the index name or host'))
                        font.pixelSize: 12; color: Tokens.text; wrapMode: Text.Wrap
                    }
                    HudLabel {
                        objectName: 'source-error'
                        Layout.fillWidth: true
                        visible: text !== ''
                        text: root.form.error
                        color: Tokens.warning; font.pixelSize: 12; wrapMode: Text.Wrap
                    }
                    Rectangle {
                        objectName: 'source-notice'
                        Layout.fillWidth: true
                        Layout.preferredHeight: noticeText.implicitHeight + 20
                        radius: 3
                        color: 'transparent'
                        border.color: Tokens.gold
                        HudLabel {
                            id: noticeText
                            x: 12; y: 10; width: parent.width - 24
                            text: Library.CUSTOM_NOTICE
                            wrapMode: Text.Wrap; font.pixelSize: 12; color: Tokens.gold
                        }
                    }
                    ActionButton {
                        objectName: 'source-add'
                        Layout.fillWidth: true
                        primary: root.form.ok
                        text: 'Add source'
                        enabled: root.form.ok && !ShellState.libraryBusy
                        onClicked: root.addSource()
                    }
                    Item { Layout.fillHeight: true }
                    HudLabel {
                        Layout.fillWidth: true
                        text: 'Removing or disabling a source keeps what you installed from it; those installs get no updates until it returns.'
                        color: Tokens.muted; font.pixelSize: 11; wrapMode: Text.Wrap
                    }
                }
            }
        }
    }
}
