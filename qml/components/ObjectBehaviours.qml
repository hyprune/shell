import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../Behaviours.js" as B

// Director > Objects > Placed > Behaviours (RFC-0014 amendment: data-driven behaviours, IPC 0.31):
// the placement's behaviours with their live values, Add (what it changes), and an editor:
// A and B (typed, or captured from the gizmo against the rest pose), the anchor face, the value
// it reads (this object's data source by default, 0 to 100), easing and smoothing. Save sends the
// whole list (objects.configure patch behaviours) and puts a captured object back at rest.
// Data source… opens Objects > Data sources on this object's entry (Test, Run now, Restart).
ColumnLayout {
    id: panel
    objectName: 'objectBehaviours'
    property var instance: null
    readonly property var list: B.listOf(instance)
    property var draft: null          // B.draftFrom(...) while editing
    property string editing: ''       // the key being edited ('' for a new one)
    property var rest: null           // the pose when the editor opened (Capture A/B measure from it)
    readonly property var errors: draft ? B.draftErrors(draft) : []
    spacing: 8
    onInstanceChanged: { if (draft && (!instance || instance.id !== draftFor)) close(); }
    property string draftFor: ''

    function open(b, key) {
        draft = B.draftFrom(b);
        editing = key || '';
        draftFor = instance ? instance.id : '';
        rest = B.restOf(instance);
    }
    function close() {
        if (rest && instance && B.moved(rest, instance)) ShellState.objectAction('objects.transform', B.restParams(instance.id, rest));
        draft = null; editing = ''; rest = null;
    }
    function set(patch) { draft = Object.assign({}, draft, patch); }
    function setEnd(end, index, text) {
        var values = draft[end].slice(); values[index] = text;
        var patch = {}; patch[end] = values; set(patch);
    }
    function captureInto(end) {
        var v = B.capture(rest, instance, draft.property);
        if (!v) return;
        var patch = {}; patch[end] = v.map(String); set(patch);
    }
    function save() {
        if (!draft || errors.length || !instance) return;
        var next = B.withBehaviour(list, B.fromDraft(draft), editing || draft.key);
        close();
        ShellState.objectAction('objects.configure', B.configureParams(instance.id, next));
    }
    function remove(key) { ShellState.objectAction('objects.configure', B.configureParams(instance.id, B.without(list, key))); }

    component Field: TextField {
        Layout.fillWidth: true
        Layout.preferredWidth: 1
        implicitHeight: 34
        color: Tokens.text
        placeholderTextColor: Tokens.muted
        selectionColor: Tokens.accent
        selectedTextColor: Tokens.ink
        font.family: Tokens.mono; font.pixelSize: 12
        leftPadding: 8; rightPadding: 8
        background: Rectangle { radius: Tokens.radius; color: Tokens.panel; border.width: parent.activeFocus ? 2 : 1; border.color: parent.activeFocus ? Tokens.gold : Tokens.line }
    }
    component Caption: HudLabel { font.pixelSize: 11; color: Tokens.muted }
    component Note: HudLabel { Layout.fillWidth: true; font.pixelSize: 12; color: Tokens.muted; wrapMode: Text.Wrap }

    Rectangle { Layout.fillWidth: true; height: 1; color: Tokens.line }
    RowLayout {
        Layout.fillWidth: true
        HudLabel { text: 'BEHAVIOURS  /  ' + panel.list.length; font.pixelSize: 11; color: Tokens.gold; font.letterSpacing: 2; Layout.fillWidth: true }
        ActionButton {
            objectName: 'behaviour-source'
            text: 'Data source…'
            enabled: !!panel.instance
            onClicked: ShellState.openSourceFor(B.entryOf(B.sourceOf(panel.instance.id, panel.draft ? B.fromDraft(panel.draft) : panel.list[0])) || panel.instance.id)
        }
    }
    Note { text: 'Let live data change how this object looks: a value (0 to 100 from this object\'s data source, unless you choose another) moves it between A and B. Only the look changes: you still bump into it where it stands.' }

    // ---- the list ----
    Repeater {
        model: panel.draft ? [] : panel.list
        RowLayout {
            required property var modelData
            readonly property var live: B.stateOf(panel.instance, modelData.key)
            Layout.fillWidth: true
            spacing: 8
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 1
                HudLabel { text: modelData.key + '  ·  ' + B.summaryText(modelData); font.pixelSize: 13; elide: Text.ElideRight; Layout.fillWidth: true }
                HudLabel {
                    objectName: 'behaviour-state:' + modelData.key
                    text: B.inputText(panel.instance ? panel.instance.id : '', modelData) + '  ·  ' + B.stateText(live)
                    font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true
                    color: B.stateLevel(live) === 'ok' ? Tokens.positive : B.stateLevel(live) === 'warning' ? Tokens.warning : Tokens.muted
                }
                Rectangle {
                    Layout.fillWidth: true; height: 3; radius: 1; color: Tokens.line
                    Rectangle { height: parent.height; radius: 1; width: parent.width * (live ? live.t : 0); color: Tokens.accent }
                }
            }
            ActionButton { objectName: 'behaviour-edit:' + modelData.key; text: 'Edit'; implicitWidth: 64; onClicked: panel.open(modelData, modelData.key) }
            ActionButton { objectName: 'behaviour-remove:' + modelData.key; text: 'Remove'; implicitWidth: 80; onClicked: panel.remove(modelData.key) }
        }
    }
    Flow {
        Layout.fillWidth: true
        spacing: 6
        visible: !panel.draft && panel.list.length < 8
        Repeater {
            model: B.PROPERTIES
            ActionButton {
                required property var modelData
                objectName: 'behaviour-add:' + modelData.id
                text: '+ ' + modelData.label
                implicitWidth: 112
                onClicked: panel.open(B.newBehaviour(modelData.id, panel.list), '')
            }
        }
    }

    // ---- the editor ----
    ColumnLayout {
        objectName: 'behaviourEditor'
        Layout.fillWidth: true
        visible: !!panel.draft
        spacing: 8
        HudLabel { text: panel.draft ? (B.property(panel.draft.property) || {}).label + ': ' + (B.property(panel.draft.property) || {}).hint : ''; font.pixelSize: 13 }
        RowLayout {
            spacing: 8
            Caption { text: 'Name' }
            Field { objectName: 'behaviourKey'; Layout.preferredWidth: 160; Layout.fillWidth: false; text: panel.draft ? panel.draft.key : ''; onTextEdited: panel.set({key: text.trim()}) }
        }
        // A and B: numbers per axis (scale, move, rotate, texture), one number (glow) or a colour.
        Repeater {
            model: panel.draft && panel.draft.property !== 'visible' ? ['from', 'to'] : []
            RowLayout {
                required property string modelData
                readonly property string end: modelData
                Layout.fillWidth: true
                spacing: 6
                Caption { text: end === 'from' ? 'A (value low)' : 'B (value high)'; Layout.preferredWidth: 100 }
                Repeater {
                    model: panel.draft ? panel.draft[parent.end].length : 0
                    Field {
                        required property int index
                        objectName: 'behaviour-' + parent.end + ':' + index
                        placeholderText: panel.draft && panel.draft[parent.end].length === 3 ? B.AXES[index] : ''
                        text: panel.draft ? panel.draft[parent.end][index] : ''
                        onTextEdited: panel.setEnd(parent.end, index, text)
                    }
                }
                ActionButton {
                    objectName: 'behaviour-capture-' + (end === 'from' ? 'a' : 'b')
                    visible: !!panel.draft && ['move', 'rotate', 'scale'].indexOf(panel.draft.property) >= 0
                    text: 'Capture ' + (end === 'from' ? 'A' : 'B')
                    implicitWidth: 104
                    onClicked: panel.captureInto(end)
                }
            }
        }
        Note {
            visible: !!panel.draft && ['move', 'rotate', 'scale'].indexOf(panel.draft.property) >= 0
            text: 'To capture: move, turn or scale the object with the gizmo (tool 4) to how it looks at A, press Capture A; then to B, Capture B. Save puts it back where it stood.'
        }
        RowLayout {
            visible: !!panel.draft && (panel.draft.property === 'scale' || panel.draft.property === 'rotate')
            spacing: 6
            Caption { text: 'Around'; Layout.preferredWidth: 100 }
            Repeater {
                model: B.ANCHORS
                ActionButton {
                    required property string modelData
                    objectName: 'behaviour-anchor:' + modelData
                    text: modelData
                    implicitWidth: 72
                    primary: !!panel.draft && panel.draft.anchor === modelData
                    onClicked: panel.set({anchor: modelData})
                }
            }
        }
        RowLayout {
            visible: !!panel.draft && panel.draft.property === 'glow'
            spacing: 6
            Caption { text: 'Glow colour'; Layout.preferredWidth: 100 }
            Field { objectName: 'behaviourGlowColour'; Layout.preferredWidth: 120; Layout.fillWidth: false; text: panel.draft ? panel.draft.colour : ''; onTextEdited: panel.set({colour: text}) }
        }
        RowLayout {
            visible: !!panel.draft && panel.draft.property === 'texture'
            spacing: 6
            Caption { text: 'Mode'; Layout.preferredWidth: 100 }
            Segmented {
                objectName: 'behaviourMode'
                Layout.preferredWidth: 280
                model: [{id: 'offset', label: 'Slide (repeats)'}, {id: 'scroll', label: 'Scroll (per second)'}]
                current: panel.draft ? panel.draft.mode : 'offset'
                onPicked: (id) => panel.set({mode: id})
            }
        }
        RowLayout {
            visible: !!panel.draft && panel.draft.property === 'visible'
            spacing: 6
            Caption { text: 'Shown from'; Layout.preferredWidth: 100 }
            Field { objectName: 'behaviourAbove'; placeholderText: 'lowest value (optional)'; text: panel.draft ? panel.draft.above : ''; onTextEdited: panel.set({above: text.trim()}) }
            Caption { text: 'below' }
            Field { objectName: 'behaviourBelow'; placeholderText: 'highest value (optional)'; text: panel.draft ? panel.draft.below : ''; onTextEdited: panel.set({below: text.trim()}) }
        }
        // The value it reads.
        RowLayout {
            spacing: 6
            Caption { text: 'Reads'; Layout.preferredWidth: 100 }
            Field { objectName: 'behaviourSource'; placeholderText: 'this object\'s data source'; text: panel.draft ? panel.draft.source : ''; onTextEdited: panel.set({source: text.trim()}) }
            Field { objectName: 'behaviourInputKey'; Layout.preferredWidth: 90; Layout.fillWidth: false; placeholderText: 'value'; text: panel.draft ? panel.draft.inputKey : ''; onTextEdited: panel.set({inputKey: text.trim()}) }
            Field { objectName: 'behaviourMin'; Layout.preferredWidth: 70; Layout.fillWidth: false; placeholderText: '0'; text: panel.draft ? panel.draft.min : ''; onTextEdited: panel.set({min: text.trim()}) }
            Field { objectName: 'behaviourMax'; Layout.preferredWidth: 70; Layout.fillWidth: false; placeholderText: '100'; text: panel.draft ? panel.draft.max : ''; onTextEdited: panel.set({max: text.trim()}) }
        }
        RowLayout {
            visible: !!panel.draft && panel.draft.property !== 'visible'
            spacing: 6
            Caption { text: 'Easing'; Layout.preferredWidth: 100 }
            Repeater {
                model: B.EASINGS
                ActionButton {
                    required property string modelData
                    objectName: 'behaviour-easing:' + modelData
                    text: modelData
                    implicitWidth: 92
                    primary: !!panel.draft && panel.draft.easing === modelData
                    onClicked: panel.set({easing: modelData})
                }
            }
            Caption { text: 'Smoothing (s)' }
            Field { objectName: 'behaviourSmoothing'; Layout.preferredWidth: 70; Layout.fillWidth: false; placeholderText: '0.3'; text: panel.draft ? panel.draft.smoothing : ''; onTextEdited: panel.set({smoothing: text.trim()}) }
        }
        Repeater {
            model: panel.errors
            HudLabel { required property string modelData; text: '· ' + modelData; font.pixelSize: 12; color: Tokens.warning; wrapMode: Text.Wrap; Layout.fillWidth: true }
        }
        RowLayout {
            spacing: 8
            ActionButton { objectName: 'behaviour-save'; text: 'Save behaviour'; primary: true; enabled: panel.errors.length === 0 && ShellState.objectsCan('objects.configure'); onClicked: panel.save() }
            ActionButton { objectName: 'behaviour-cancel'; text: 'Cancel'; onClicked: panel.close() }
            ActionButton { objectName: 'behaviour-rest'; text: 'Back to rest'; visible: !!panel.rest && B.moved(panel.rest, panel.instance); onClicked: ShellState.objectAction('objects.transform', B.restParams(panel.instance.id, panel.rest)) }
        }
    }
}
