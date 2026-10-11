import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../Quests.js" as Quests

// Director > Quests (RFC-0012, IPC 0.21). List (left) grouped Active (tracked first),
// Available, Completed and Failed or abandoned; details (right) from quests.get; the
// personal quest form; focus session controls. Keys: arrows move, Enter opens, T track,
// Space mark done, F start a focus session, N new quest; Esc still leaves the menu.
FocusScope {
    id: root
    objectName: 'directorQuests'
    property var expanded: ({})          // group id -> bool, overrides the default collapse
    readonly property var groups: Quests.groupQuests(ShellState.questList)
    readonly property var rowList: Quests.rows(groups, expanded)
    property int current: -1
    property bool editing: false
    property var editRef: null
    property string confirmDelete: ''
    readonly property var detail: ShellState.questDetail
    readonly property var actions: Quests.questActions(detail)
    readonly property var ref: detail ? detail.questRef : ShellState.questRef(ShellState.selectedQuest)
    readonly property var ctx: ({markers: ShellState.markersState, places: ShellState.places,
                                 zones: ShellState.state && ShellState.state.location ? ShellState.state.location.zones : [],
                                 worldId: ShellState.state && ShellState.state.world ? ShellState.state.world.id : ''})
    // Tracking follows core's state (current) rather than the last quests.get answer.
    readonly property bool isTracked: !!detail && Quests.sameRef(ShellState.questsState ? ShellState.questsState.tracked : null, detail.questRef)
    readonly property bool focusIdle: !ShellState.focusState || ShellState.focusState.state === 'idle'

    function syncCurrent() {
        var at = rowList.findIndex(r => r.type === 'quest' && r.key === ShellState.selectedQuest);
        if (at >= 0) { current = at; return; }
        if (!ShellState.selectedQuest) {
            var first = rowList.findIndex(r => r.type === 'quest');
            if (first >= 0 && !editing) { current = first; ShellState.selectQuest(rowList[first].key); return; }
        }
        current = Math.min(current, rowList.length - 1);
    }
    onRowListChanged: syncCurrent()
    Connections {
        target: ShellState
        function onSelectedQuestChanged() { root.confirmDelete = ''; root.syncCurrent(); }
        function onQuestActionDone(method, params, result) {
            if (root.editing && (method === 'quests.create' || method === 'quests.update')) { root.editing = false; list.forceActiveFocus(); }
        }
        function onQuestActionFailed(method, params, message) {
            if (method === 'quests.create' || method === 'quests.update') form.busy = false;
        }
    }
    onVisibleChanged: { if (visible && ShellState.director) Qt.callLater(() => { if (!root.editing) list.forceActiveFocus(); }); }

    function moveTo(index) {
        if (index < 0 || index >= rowList.length) return;
        current = index;
        list.positionViewAtIndex(index, ListView.Contain);
        if (rowList[index].type === 'quest') ShellState.selectQuest(rowList[index].key);
    }
    function toggleGroup(group, open) {
        var next = Object.assign({}, expanded); next[group] = open; expanded = next;
    }
    function activate(index) {
        var row = rowList[index];
        if (!row) return;
        if (row.type === 'header') { toggleGroup(row.group, !row.expanded); return; }
        moveTo(index);
        Qt.callLater(() => { var b = detailFirst(); if (b) b.forceActiveFocus(); });
    }
    function detailFirst() { return trackButton.visible && trackButton.enabled ? trackButton : acceptButton.visible ? acceptButton : resumeButton.visible ? resumeButton : editButton.visible ? editButton : null; }
    function say(text) { ShellState.questFeedback = text; ShellState.questFeedbackTimer.restart(); }
    function track() {
        if (!detail) return;
        if (actions.accept) { ShellState.questAction('quests.accept', {questRef: ref}); return; }
        if (!actions.track) { say('Only active quests can be tracked.'); return; }
        ShellState.questAction('quests.track', {questRef: isTracked ? null : ref});
    }
    function markDone(stepId, objectiveId) {
        if (!detail) return;
        var pick = stepId ? {stepId: stepId, objectiveId: objectiveId} : Quests.firstObjective(detail, 'manual');
        if (!pick) { say('Nothing to mark done in the current step.'); return; }
        ShellState.questAction('quests.mark', {questRef: ref, stepId: pick.stepId, objectiveId: pick.objectiveId});
    }
    function startFocus(objectiveId) {
        if (!detail) return;
        if (!focusIdle) { say('A focus session is already running.'); return; }
        if (detail.state !== 'active') { say('Accept or resume the quest first.'); return; }
        var pick = objectiveId ? {objectiveId: objectiveId} : Quests.firstObjective(detail, 'focus');
        var params = {questRef: ref};
        if (pick) params.objectiveId = pick.objectiveId;
        ShellState.questAction('focus.start', params);
    }
    function openForm(seed) {
        // seed: null = new quest; {edit: true} = the selected personal quest; a form object prefills.
        var editingDetail = seed && seed.edit ? detail : null;
        if (seed && seed.edit && !(detail && detail.personal)) return;
        editRef = editingDetail ? editingDetail.questRef : null;
        form.previous = editingDetail;
        editing = true;
        var base = Quests.formFromDetail(editingDetail);
        var extra = Object.assign({}, seed || {}); delete extra.edit;
        form.load(Object.assign(base, extra));
    }
    function save(input) {
        if (editRef) ShellState.questAction('quests.update', {questRef: editRef, quest: input});
        else ShellState.questAction('quests.create', {quest: input});
    }
    function resolve(target, stepId, objectiveId, label) {
        return Quests.resolveTarget(target, Object.assign({questKey: ShellState.selectedQuest, stepId: stepId, objectiveId: objectiveId, label: label}, ctx));
    }
    function setWaypoint(resolved, stepId) {
        var params = Quests.waypointParams(resolved, 'quest-' + Quests.slugify(ShellState.selectedQuest + '-' + stepId, 'target'), resolved.label);
        if (params) ShellState.questAction('waypoint.set', params);
    }

    Keys.onPressed: (event) => {
        if (!ShellState.questsSupported || root.editing) return;
        var mods = event.modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier);
        if (mods) return;
        if (event.key === Qt.Key_N) { root.openForm(null); event.accepted = true; }
        else if (event.key === Qt.Key_T) { root.track(); event.accepted = true; }
        else if (event.key === Qt.Key_F) { root.startFocus(''); event.accepted = true; }
    }

    HudLabel {
        anchors.centerIn: parent
        width: Math.min(parent.width - 40, 640)
        visible: !ShellState.questsSupported
        text: 'Quests, markers and focus sessions need core IPC 0.21.'
        color: Tokens.muted; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter
    }

    RowLayout {
        anchors.fill: parent
        spacing: 20
        visible: ShellState.questsSupported

        // ---- List ----
        Rectangle {
            Layout.preferredWidth: root.width < 1100 ? 300 : 380
            Layout.fillHeight: true
            color: Tokens.panel
            border.color: Tokens.line
            radius: 3

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                RowLayout {
                    Layout.fillWidth: true
                    HudLabel { text: 'QUEST LOG'; color: Tokens.gold; font.pixelSize: 11; font.letterSpacing: 2; Layout.fillWidth: true }
                    ActionButton { objectName: 'quests-new'; text: 'New quest · N'; implicitWidth: 132; enabled: ShellState.available('quests.create'); onClicked: root.openForm(null) }
                }

                ListView {
                    id: list
                    objectName: 'questList'
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    focus: true
                    model: root.rowList
                    currentIndex: root.current
                    keyNavigationEnabled: false
                    highlightFollowsCurrentItem: false
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.vertical: ScrollBar {}
                    Keys.onUpPressed: root.moveTo(Quests.move(root.rowList, root.current, -1))
                    Keys.onDownPressed: root.moveTo(Quests.move(root.rowList, root.current, 1))
                    Keys.onReturnPressed: root.activate(root.current)
                    Keys.onEnterPressed: root.activate(root.current)
                    Keys.onSpacePressed: root.markDone('', '')

                    delegate: Item {
                        id: row
                        required property var modelData
                        required property int index
                        readonly property bool header: modelData.type === 'header'
                        readonly property bool selected: !header && modelData.key === ShellState.selectedQuest
                        readonly property bool cursor: list.activeFocus && index === root.current
                        width: list.width - 8
                        height: header ? 38 : 62

                        Rectangle {
                            anchors.fill: parent
                            anchors.topMargin: row.header ? 6 : 2
                            radius: 3
                            color: row.selected ? Tokens.raised : 'transparent'
                            border.width: row.cursor ? 2 : 0
                            border.color: Tokens.gold
                        }
                        Rectangle { visible: !row.header && row.modelData.quest.tracked; x: 0; y: 8; width: 3; height: parent.height - 12; color: Tokens.quest }
                        // Group header
                        HudLabel {
                            visible: row.header
                            x: 8; y: 6; height: parent.height - 6; width: parent.width - 16
                            verticalAlignment: Text.AlignVCenter
                            text: row.header ? (row.modelData.expanded ? '▾  ' : '▸  ') + row.modelData.title.toUpperCase() + '   ' + row.modelData.count : ''
                            font.pixelSize: 12; font.letterSpacing: 1.4
                            color: row.modelData.count ? Tokens.accent : Tokens.muted
                        }
                        // Quest summary
                        Column {
                            visible: !row.header
                            x: 14; y: 9; width: parent.width - 24
                            spacing: 4
                            RowLayout {
                                width: parent.width
                                HudLabel {
                                    Layout.fillWidth: true
                                    text: row.header ? '' : (row.modelData.quest.tracked ? '◆ ' : '') + row.modelData.quest.title
                                    font.pixelSize: 15
                                    color: row.selected ? Tokens.text : Tokens.text
                                }
                                HudLabel {
                                    text: row.header ? '' : Quests.progressText(row.modelData.quest.progress)
                                    font.family: Tokens.mono; font.pixelSize: 11
                                    color: Tokens.muted
                                }
                            }
                            HudLabel {
                                width: parent.width
                                text: row.header ? '' : (row.modelData.quest.offWorld ? 'NOT IN THIS WORLD  ·  ' : '')
                                      + (row.modelData.quest.step ? row.modelData.quest.step.title : row.modelData.quest.state === 'completed' ? 'Complete' : row.modelData.quest.state)
                                font.pixelSize: 12
                                color: Tokens.muted
                            }
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: { list.forceActiveFocus(); if (row.header) root.toggleGroup(row.modelData.group, !row.modelData.expanded); else root.moveTo(row.index); }
                            onDoubleClicked: { if (!row.header) root.activate(row.index); }
                        }
                    }

                    HudLabel {
                        anchors.centerIn: parent
                        width: parent.width - 20
                        visible: !ShellState.questList.length
                        text: 'No quests yet. N writes a personal quest: a title and one step per line.'
                        color: Tokens.muted; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: Tokens.line }
                FocusPanel { Layout.fillWidth: true }
            }
        }

        // ---- Details / form ----
        ScrollView {
            id: detailScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: availableWidth

            ColumnLayout {
                width: Math.min(detailScroll.availableWidth - 16, 980)
                spacing: 14

                QuestForm {
                    id: form
                    Layout.fillWidth: true
                    visible: root.editing
                    onSave: (input) => root.save(input)
                    onCancel: { root.editing = false; list.forceActiveFocus(); }
                }

                HudLabel {
                    Layout.fillWidth: true
                    visible: !root.editing && !root.detail
                    text: ShellState.selectedQuest ? 'Loading…' : 'Select a quest, or press N to write one.'
                    color: Tokens.muted; font.pixelSize: 14
                }

                ColumnLayout {
                    id: details
                    Layout.fillWidth: true
                    visible: !root.editing && !!root.detail
                    spacing: 14

                    HudLabel {
                        Layout.fillWidth: true
                        text: root.detail ? [root.detail.category, root.detail.state, root.isTracked ? 'tracked' : ''].filter(v => v).join('  ·  ').toUpperCase() : ''
                        color: root.isTracked ? Tokens.quest : Tokens.gold
                        font.pixelSize: 11; font.letterSpacing: 1.8
                    }
                    HudLabel {
                        objectName: 'questTitle'
                        Layout.fillWidth: true
                        text: root.detail ? root.detail.title : ''
                        font.pixelSize: Tokens.title; font.weight: Font.Light
                        wrapMode: Text.Wrap; maximumLineCount: 2
                    }
                    HudLabel {
                        Layout.fillWidth: true
                        visible: text !== ''
                        text: root.detail ? root.detail.summary || '' : ''
                        color: Tokens.muted; wrapMode: Text.Wrap; lineHeight: 1.3
                    }
                    HudLabel {
                        Layout.fillWidth: true
                        visible: !!(root.detail && root.detail.expires)
                        text: root.detail && root.detail.expires ? 'Due ' + root.detail.expires.replace('T', ' ') : ''
                        color: Tokens.muted; font.pixelSize: 12
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        ActionButton { id: trackButton; objectName: 'quest-track'; visible: !!root.actions.track; text: root.isTracked ? 'Untrack · T' : 'Track · T'; primary: !root.isTracked; enabled: ShellState.available('quests.track'); onClicked: root.track() }
                        ActionButton { id: acceptButton; objectName: 'quest-accept'; visible: !!root.actions.accept; text: 'Accept · T'; primary: true; enabled: ShellState.available('quests.accept'); onClicked: ShellState.questAction('quests.accept', {questRef: root.ref}) }
                        ActionButton { id: resumeButton; objectName: 'quest-resume'; visible: !!root.actions.resume; text: 'Resume'; primary: true; enabled: ShellState.available('quests.resume'); onClicked: ShellState.questAction('quests.resume', {questRef: root.ref}) }
                        ActionButton { objectName: 'quest-focus'; visible: !!root.detail && root.detail.state === 'active'; text: 'Focus session · F'; enabled: root.focusIdle && ShellState.available('focus.start'); onClicked: root.startFocus('') }
                        ActionButton { id: editButton; objectName: 'quest-edit'; visible: !!root.actions.edit; text: 'Edit'; enabled: ShellState.available('quests.update'); onClicked: root.openForm({edit: true}) }
                        ActionButton { objectName: 'quest-abandon'; visible: !!root.actions.abandon; text: 'Abandon'; enabled: ShellState.available('quests.abandon'); onClicked: ShellState.questAction('quests.abandon', {questRef: root.ref}) }
                        ActionButton {
                            objectName: 'quest-delete'
                            visible: !!root.actions.remove
                            text: root.confirmDelete === ShellState.selectedQuest ? 'Delete for good?' : 'Delete'
                            enabled: ShellState.available('quests.delete')
                            onClicked: {
                                if (root.confirmDelete === ShellState.selectedQuest) { root.confirmDelete = ''; ShellState.questAction('quests.delete', {questRef: root.ref}); }
                                else root.confirmDelete = ShellState.selectedQuest;
                            }
                        }
                    }
                    HudLabel { Layout.fillWidth: true; visible: text !== ''; text: ShellState.questFeedback; color: Tokens.gold; font.pixelSize: 12; wrapMode: Text.Wrap }

                    Rectangle { Layout.fillWidth: true; height: 1; color: Tokens.line }
                    HudLabel { text: root.detail && !root.detail.sequential ? 'STEPS · ANY ORDER' : 'STEPS'; color: Tokens.gold; font.pixelSize: Tokens.caption; font.letterSpacing: 1.5; Layout.fillWidth: true }

                    Repeater {
                        model: root.detail ? root.detail.steps : []
                        delegate: ColumnLayout {
                            id: stepItem
                            required property var modelData
                            required property int index
                            readonly property bool open: modelData.state === 'current'
                            Layout.fillWidth: true
                            spacing: 6
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10
                                HudLabel {
                                    Layout.preferredWidth: 22
                                    text: stepItem.modelData.state === 'done' ? '✓' : stepItem.open ? '▸' : '○'
                                    color: stepItem.modelData.state === 'done' ? Tokens.positive : stepItem.open ? Tokens.quest : Tokens.muted
                                    font.pixelSize: 16
                                }
                                HudLabel {
                                    Layout.fillWidth: true
                                    text: stepItem.modelData.title + (stepItem.modelData.optional ? '  (optional)' : '')
                                    font.pixelSize: 16
                                    color: stepItem.modelData.state === 'pending' ? Tokens.muted : Tokens.text
                                    wrapMode: Text.Wrap
                                }
                                HudLabel {
                                    visible: !!stepItem.modelData.target
                                    text: Quests.targetText(stepItem.modelData.target, root.ctx)
                                    color: Tokens.muted; font.pixelSize: 12
                                    Layout.maximumWidth: 220
                                }
                            }
                            Repeater {
                                model: stepItem.modelData.objectives
                                delegate: ColumnLayout {
                                    id: objective
                                    required property var modelData
                                    readonly property var target: modelData.target || stepItem.modelData.target
                                    readonly property var resolved: target ? root.resolve(target, stepItem.modelData.id, modelData.id, modelData.label || stepItem.modelData.title) : null
                                    readonly property bool done: Quests.objectiveDone(modelData)
                                    readonly property bool active: stepItem.open && root.detail.state === 'active'
                                    readonly property bool canMark: modelData.type === 'manual' && !done && active
                                    readonly property bool canFocus: modelData.type === 'focus' && !done && active
                                    readonly property bool canWaypoint: !!resolved && !done
                                    readonly property bool canMap: !!resolved && !!ShellState.mapData
                                    // A step's default single "Done" checkbox needs no row of its own.
                                    readonly property bool plain: stepItem.modelData.objectives.length === 1 && modelData.type === 'manual' && (modelData.count || 1) === 1
                                    Layout.fillWidth: true
                                    Layout.leftMargin: 32
                                    spacing: 6
                                    RowLayout {
                                        Layout.fillWidth: true
                                        visible: !objective.plain
                                        HudLabel { Layout.fillWidth: true; text: objective.modelData.label || objective.modelData.type; color: objective.done ? Tokens.muted : Tokens.text; font.pixelSize: 13 }
                                        HudLabel {
                                            text: Quests.objectiveProgress(objective.modelData)
                                                  + (objective.modelData.type === 'focus' && objective.modelData.creditedMinutes ? '  ·  ' + Math.round(objective.modelData.creditedMinutes) + ' min' : '')
                                            font.family: Tokens.mono; font.pixelSize: 12
                                            color: objective.done ? Tokens.positive : Tokens.accent
                                        }
                                    }
                                    Flow {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        visible: objective.canMark || objective.canFocus || objective.canWaypoint || objective.canMap
                                        ActionButton { id: markButton; objectName: 'quest-mark-' + stepItem.modelData.id + '-' + objective.modelData.id; implicitHeight: 34; visible: objective.canMark; text: 'Mark done · Space'; enabled: ShellState.available('quests.mark'); onClicked: root.markDone(stepItem.modelData.id, objective.modelData.id) }
                                        ActionButton { id: focusButton; objectName: 'quest-start-focus-' + stepItem.modelData.id; implicitHeight: 34; visible: objective.canFocus; text: 'Start focus session'; enabled: root.focusIdle && ShellState.available('focus.start'); onClicked: root.startFocus(objective.modelData.id) }
                                        ActionButton { id: waypointButton; objectName: 'quest-waypoint-' + stepItem.modelData.id; implicitHeight: 34; visible: objective.canWaypoint; text: 'Set waypoint ◇'; enabled: ShellState.available('waypoint.set'); onClicked: root.setWaypoint(objective.resolved, stepItem.modelData.id) }
                                        ActionButton { id: mapButton; objectName: 'quest-map-' + stepItem.modelData.id; implicitHeight: 34; visible: objective.canMap; text: 'Show on map'; onClicked: ShellState.showOnMap(objective.resolved) }
                                    }
                                    HudLabel {
                                        Layout.fillWidth: true
                                        visible: !!objective.target && !objective.resolved && !objective.done
                                        text: 'Not in this world: no marker here.'
                                        color: Tokens.muted; font.pixelSize: 12
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
