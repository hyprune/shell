import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../Quests.js" as Quests

// Director > Quests: the personal quest form (RFC-0012). New and Edit share it: a title,
// one step per line, an optional target for the quest (workspace, area or place) and
// optional focus sessions per step. Enter in a single-line field saves.
ColumnLayout {
    id: root
    property var previous: null   // QuestDetail when editing
    property bool busy: false
    property var sessions: ({})   // step title -> focus sessions
    property string targetKind: 'none'
    property bool perStep: false   // editing a quest whose steps have their own targets
    property string targetValue: ''
    property string error: ''
    readonly property var stepTitles: Quests.parseSteps(stepsField.text)
    readonly property var areas: ShellState.state && ShellState.state.mounts && ShellState.state.mounts.areas ? ShellState.state.mounts.areas : []
    readonly property var places: ShellState.places
    signal save(var input)
    signal cancel()
    spacing: 12

    function load(form) {
        titleField.text = form.title || '';
        summaryField.text = form.summary || '';
        stepsField.text = form.steps || '';
        sessions = Object.assign({}, form.sessions || {});
        targetKind = form.targetKind || 'none';
        perStep = targetKind === 'keep';
        targetValue = form.targetValue || '';
        workspaceField.text = targetKind === 'workspace' ? targetValue : '';
        error = ''; busy = false;
        titleField.forceActiveFocus();
    }
    function current() {
        return {title: titleField.text, summary: summaryField.text, steps: stepsField.text, sessions: sessions,
                targetKind: targetKind, targetValue: targetKind === 'workspace' ? workspaceField.text : targetValue};
    }
    function submit() {
        var form = current();
        error = Quests.formError(form);
        if (error && error.indexOf('At most') !== 0) return;
        busy = true;
        save(Quests.questInput(form, previous));
    }
    function setSessions(title, n) {
        var next = Object.assign({}, sessions);
        if (n > 0) next[title] = Math.min(12, n); else delete next[title];
        sessions = next;
    }

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

    HudLabel { text: root.previous ? 'EDIT PERSONAL QUEST' : 'NEW PERSONAL QUEST'; color: Tokens.gold; font.pixelSize: Tokens.caption; font.letterSpacing: 1.5; Layout.fillWidth: true }
    HudLabel { text: 'Title'; Layout.fillWidth: true }
    Field { id: titleField; objectName: 'quest-form-title'; onAccepted: root.submit(); maximumLength: 64; placeholderText: 'Write the release notes' }
    HudLabel { text: 'Summary (optional)'; Layout.fillWidth: true }
    Field { id: summaryField; objectName: 'quest-form-summary'; onAccepted: root.submit(); maximumLength: 1000; placeholderText: 'What it is for, in a sentence' }
    HudLabel { text: 'Steps · one per line'; Layout.fillWidth: true }
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 132
        radius: Tokens.radius; color: Tokens.panel
        border.width: stepsField.activeFocus ? 2 : 1; border.color: stepsField.activeFocus ? Tokens.gold : Tokens.line
        ScrollView {
            anchors.fill: parent; anchors.margins: 2
            clip: true
            TextArea {
                id: stepsField
                objectName: 'quest-form-steps'
                color: Tokens.text
                placeholderText: 'Draft\nReview\nPublish'
                placeholderTextColor: Tokens.muted
                selectionColor: Tokens.accent
                selectedTextColor: Tokens.ink
                font.family: Tokens.sans; font.pixelSize: 14
                wrapMode: TextEdit.NoWrap
                background: null
                KeyNavigation.priority: KeyNavigation.BeforeItem
                KeyNavigation.tab: targetChoice
            }
        }
    }
    HudLabel {
        Layout.fillWidth: true
        text: root.stepTitles.length ? root.stepTitles.length + (root.stepTitles.length === 1 ? ' step' : ' steps') + ' · each is marked done by hand unless it has focus sessions'
                                     : 'Without steps the quest has one step: its title.'
        color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap
    }

    HudLabel { text: 'Where (optional)'; Layout.fillWidth: true }
    Segmented {
        id: targetChoice
        objectName: 'quest-form-target'
        Layout.fillWidth: true
        model: (root.perStep ? [{id: 'keep', label: 'Per step (unchanged)'}] : []).concat([{id: 'none', label: 'Anywhere'}, {id: 'workspace', label: 'Workspace'},
                {id: 'area', label: 'Area', selectable: root.areas.length > 0}, {id: 'place', label: 'Place', selectable: root.places.length > 0}])
        current: root.targetKind
        onPicked: (kind) => { root.targetKind = kind; root.targetValue = kind === 'area' && root.areas.length ? root.areas[0].id : kind === 'place' && root.places.length ? root.places[0].id : ''; }
    }
    RowLayout {
        Layout.fillWidth: true
        visible: root.targetKind === 'workspace'
        Field { id: workspaceField; objectName: 'quest-form-workspace'; onAccepted: root.submit(); Layout.preferredWidth: 140; Layout.fillWidth: false; placeholderText: 'e.g. 21'
            validator: IntValidator { bottom: 1; top: 2147483647 }
        }
        HudLabel {
            Layout.fillWidth: true
            readonly property var homes: ShellState.workspaces.filter(w => !w.desktop).slice(0, 6)
            text: homes.length ? 'Homes here: ' + homes.map(w => w.id + ' ' + w.title).join('  ·  ') : ''
            color: Tokens.muted; font.pixelSize: 12
        }
    }
    Choice {
        objectName: 'quest-form-area'
        visible: root.targetKind === 'area'
        Layout.fillWidth: true
        model: root.areas.map(a => a.id.replace(/-/g, ' ') + (a.workspaceSlot ? '  ·  workspace ' + Number(a.workspaceSlot) : ''))
        currentIndex: root.areas.findIndex(a => a.id === root.targetValue)
        onActivated: root.targetValue = root.areas[currentIndex].id
    }
    Choice {
        objectName: 'quest-form-place'
        visible: root.targetKind === 'place'
        Layout.fillWidth: true
        model: root.places.map(p => p.name || p.id)
        currentIndex: root.places.findIndex(p => p.id === root.targetValue)
        onActivated: root.targetValue = root.places[currentIndex].id
    }
    HudLabel {
        Layout.fillWidth: true
        visible: root.targetKind !== 'none'
        text: root.targetKind === 'keep' ? 'Each step keeps its own place; new steps have none.' : 'The quest gets a marker there (TAB in the world) wherever that ' + (root.targetKind === 'workspace' ? 'workspace has a home.' : root.targetKind + ' exists.')
        color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap
    }

    HudLabel { visible: root.stepTitles.length > 0; text: 'Focus sessions per step (optional)'; Layout.fillWidth: true }
    Repeater {
        model: root.stepTitles
        RowLayout {
            required property string modelData
            required property int index
            readonly property int count: root.sessions[modelData] || 0
            Layout.fillWidth: true
            spacing: 8
            HudLabel { Layout.fillWidth: true; text: (index + 1) + '.  ' + modelData; font.pixelSize: 13 }
            ActionButton { objectName: 'quest-form-less-' + index; implicitWidth: 36; leftPadding: 6; rightPadding: 6; text: '−'; enabled: count > 0; Accessible.name: 'Fewer focus sessions'; onClicked: root.setSessions(modelData, count - 1) }
            HudLabel { Layout.preferredWidth: 92; horizontalAlignment: Text.AlignHCenter; text: count ? count + (count === 1 ? ' session' : ' sessions') : 'by hand'; color: count ? Tokens.text : Tokens.muted; font.pixelSize: 12 }
            ActionButton { objectName: 'quest-form-more-' + index; implicitWidth: 36; leftPadding: 6; rightPadding: 6; text: '+'; enabled: count < 12; Accessible.name: 'More focus sessions'; onClicked: root.setSessions(modelData, count + 1) }
        }
    }

    HudLabel { Layout.fillWidth: true; visible: text !== ''; text: root.error; color: Tokens.gold; font.pixelSize: 12; wrapMode: Text.Wrap }
    RowLayout {
        Layout.fillWidth: true
        Item { Layout.fillWidth: true }
        ActionButton { objectName: 'quest-form-cancel'; text: 'Cancel'; onClicked: root.cancel() }
        ActionButton {
            objectName: 'quest-form-save'
            text: root.busy ? 'Saving…' : root.previous ? 'Save changes' : 'Create quest'
            primary: true
            enabled: !root.busy && ShellState.available(root.previous ? 'quests.update' : 'quests.create')
            onClicked: root.submit()
        }
    }
}
