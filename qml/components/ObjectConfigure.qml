import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../Objects.js" as Objects

// Director > Objects > Placed: the configure panel of one instance (RFC-0011 P1). It is
// built from per-trait sections in a fixed order (Objects.SECTIONS): Transform, Lock,
// Remove / Reset and Data (RFC-0013 data bindings: a machine's data source id), so a later
// section joins without changing the panel. The header shows the instance id.
ColumnLayout {
    id: panel
    objectName: 'objectConfigure'
    property var instance: null
    property var entry: null          // its catalog entry (movable.scale range), if listed
    // Rebuilt only when a section changes, not on every snapshot (keeps focus while typing).
    property var sections: []
    readonly property var sectionIds: sections.map(s => s.id)
    function refreshSections() {
        var next = Objects.panelSections(instance, entry);
        if (JSON.stringify(next) !== JSON.stringify(sections)) sections = next;
    }
    onInstanceChanged: refreshSections()
    onEntryChanged: refreshSections()
    Component.onCompleted: refreshSections()
    spacing: 14

    function can(method) { return ShellState.objectsCan(method); }
    function run(actionId) {
        var request = Objects.sectionAction(instance, actionId);
        if (request && can(request.method)) ShellState.objectAction(request.method, request.params);
    }
    // Enter on the Placed list: the first control of the first visible section.
    function focusFirst() {
        for (var i = 0; i < sectionRepeater.count; i++) {
            var item = sectionRepeater.itemAt(i);
            if (item && item.visible && item.focusFirst()) return true;
        }
        return false;
    }

    component Field: TextField {
        Layout.fillWidth: true
        Layout.minimumWidth: 0
        Layout.preferredWidth: 1     // equal columns whatever the caption widths
        implicitHeight: 38
        color: readOnly ? Tokens.muted : Tokens.text
        selectionColor: Tokens.accent
        selectedTextColor: Tokens.ink
        font.family: Tokens.mono; font.pixelSize: 13
        leftPadding: 10; rightPadding: 10
        inputMethodHints: Qt.ImhFormattedNumbersOnly
        background: Rectangle {
            radius: Tokens.radius
            color: parent.readOnly ? 'transparent' : Tokens.panel
            border.width: parent.activeFocus ? 2 : 1
            border.color: parent.activeFocus ? Tokens.gold : Tokens.line
        }
    }
    component Caption: HudLabel { Layout.fillWidth: true; Layout.minimumWidth: 0; Layout.preferredWidth: 1; font.pixelSize: 11; color: Tokens.muted }

    // Transform: position, yaw and uniform scale. Each field commits on Enter or on leaving
    // it; field text follows core's committed pose except while it is being edited.
    component TransformBody: ColumnLayout {
        id: body
        property var section: ({})
        readonly property var instance: panel.instance
        property string loadedId: ''
        spacing: 8
        function focusFirst() { if (fieldX.readOnly) return false; fieldX.forceActiveFocus(); return true; }
        function load(all) {
            var d = Objects.transformDraft(instance);
            if (!d) { loadedId = ''; return; }
            [[fieldX, d.x], [fieldY, d.y], [fieldZ, d.z], [fieldYaw, d.yaw], [fieldScale, d.scale]].forEach(f => {
                if (all || !f[0].activeFocus) f[0].text = String(f[1]);
            });
            loadedId = instance.id;
        }
        onInstanceChanged: load(!instance || instance.id !== loadedId)
        Component.onCompleted: load(true)
        function commit() {
            if (!instance || instance.id !== loadedId || !section.editable) return;
            var made = Objects.transformParams(instance, {x: fieldX.text, y: fieldY.text, z: fieldZ.text, yaw: fieldYaw.text, scale: fieldScale.text},
                                               panel.entry ? panel.entry.scale : null);
            if (made.error) { ShellState.sayObjects(made.error, 'warning'); return; }
            if (made.params && panel.can('objects.transform')) ShellState.objectAction('objects.transform', made.params);
        }
        GridLayout {
            id: grid
            Layout.fillWidth: true
            columns: panel.width < 560 ? 3 : 5
            columnSpacing: 10; rowSpacing: 4
            Caption { text: 'X  m' }
            Caption { text: 'Y  m' }
            Caption { text: 'Z  m' }
            Caption { text: 'Yaw  °'; visible: grid.columns === 5 }
            Caption { text: 'Scale  ×'; visible: grid.columns === 5 }
            Field { id: fieldX; objectName: 'object-x'; Accessible.name: 'Position X in metres'; readOnly: !body.section.editable; onEditingFinished: body.commit() }
            Field { id: fieldY; objectName: 'object-y'; Accessible.name: 'Position Y in metres'; readOnly: !body.section.editable; onEditingFinished: body.commit() }
            Field { id: fieldZ; objectName: 'object-z'; Accessible.name: 'Position Z in metres'; readOnly: !body.section.editable; onEditingFinished: body.commit() }
            Caption { text: 'Yaw  °'; visible: grid.columns === 3 }
            Caption { text: 'Scale  ×'; visible: grid.columns === 3 }
            Item { visible: grid.columns === 3; Layout.fillWidth: true; Layout.preferredWidth: 1; implicitHeight: 1 }
            Field { id: fieldYaw; objectName: 'object-yaw'; Accessible.name: 'Yaw in degrees'; readOnly: !body.section.editable; onEditingFinished: body.commit() }
            Field { id: fieldScale; objectName: 'object-scale'; Accessible.name: 'Uniform scale'; readOnly: !body.section.editable; onEditingFinished: body.commit() }
        }
        HudLabel {
            Layout.fillWidth: true
            text: body.section.note || ('Enter or leaving a field moves it. Scale ' + (panel.entry && panel.entry.scale ? Math.max(0.25, panel.entry.scale[0]) + '–' + Math.min(4, panel.entry.scale[1]) : '0.25–4') + '.')
            color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap
        }
    }

    // ---- Header ----
    HudLabel {
        Layout.fillWidth: true
        text: panel.instance ? [Objects.sourceLabel(panel.instance.source), Objects.stateText(panel.instance), panel.instance.locked ? 'locked' : ''].filter(v => v).join('  ·  ').toUpperCase() : ''
        color: panel.instance && Objects.stateLevel(panel.instance) === 'warning' ? Tokens.warning : Tokens.gold
        font.pixelSize: 11; font.letterSpacing: 1.8
    }
    HudLabel {
        objectName: 'objectTitle'
        Layout.fillWidth: true
        text: panel.instance ? panel.instance.name : ''
        font.pixelSize: Tokens.title; font.weight: Font.Light
        wrapMode: Text.Wrap; maximumLineCount: 2
    }
    HudLabel {
        Layout.fillWidth: true
        text: panel.instance ? [panel.instance.ref || panel.instance.id, panel.instance.areaId ? 'area ' + panel.instance.areaId : ''].filter(v => v).join('  ·  ') : ''
        font.family: Tokens.mono; font.pixelSize: 12; color: Tokens.muted
    }
    HudLabel {
        objectName: 'objectId'
        Layout.fillWidth: true
        visible: text !== ''
        text: Objects.idText(panel.instance)
        font.family: Tokens.mono; font.pixelSize: 12; color: Tokens.muted
    }
    HudLabel {
        Layout.fillWidth: true
        visible: text !== ''
        text: panel.entry ? [Objects.sizeText(panel.entry.bounds, panel.instance ? panel.instance.scale : 1), Objects.trianglesText(panel.entry.triangles)].filter(v => v).join('  ·  ') : ''
        font.pixelSize: 12; color: Tokens.muted
    }

    // ---- Sections, in Objects.SECTIONS order ----
    Repeater {
        id: sectionRepeater
        model: panel.sections
        delegate: ColumnLayout {
            id: section
            required property var modelData
            function focusFirst() {
                if (modelData.id === 'transform' && transformBody.focusFirst()) return true;
                if (modelData.id === 'lock' && lockButton.enabled) { lockButton.forceActiveFocus(); return true; }
                return false;
            }
            objectName: 'objectSection:' + modelData.id
            visible: modelData.visible
            Layout.fillWidth: true
            spacing: 10

            Rectangle { Layout.fillWidth: true; height: 1; color: Tokens.line }
            HudLabel { Layout.fillWidth: true; text: section.modelData.title.toUpperCase(); color: Tokens.gold; font.pixelSize: Tokens.caption; font.letterSpacing: 1.5 }

            TransformBody { id: transformBody; visible: section.modelData.id === 'transform'; Layout.fillWidth: true; section: section.modelData }
            // Lock: a locked object ignores tools and edits until unlocked.
            RowLayout {
                visible: section.modelData.id === 'lock'
                Layout.fillWidth: true
                spacing: 12
                HudLabel {
                    Layout.fillWidth: true
                    text: section.modelData.locked ? 'Locked: tools and the Director leave it as it is.' : 'Unlocked: tools 4 and 5 can move it.'
                    wrapMode: Text.Wrap; font.pixelSize: 13
                }
                ActionButton {
                    id: lockButton
                    objectName: 'object-lock'
                    text: section.modelData.locked ? 'Unlock · L' : 'Lock · L'
                    checkable: false
                    Accessible.checkable: true
                    Accessible.checked: !!section.modelData.locked
                    Accessible.name: 'Lock'
                    enabled: panel.can('objects.configure')
                    onClicked: panel.run('lock')
                }
            }

            // Remove / Reset (user) or Hide / Reset (authored, which is never deleted).
            Flow {
                visible: section.modelData.id === 'remove'
                Layout.fillWidth: true
                spacing: 8
                Repeater {
                    model: section.modelData.actions || []
                    delegate: ActionButton {
                        required property var modelData
                        objectName: 'object-' + modelData.id
                        text: modelData.label + (modelData.id === 'reset' ? ' · R' : modelData.id === 'hide' ? ' · H' : ' · Del')
                        enabled: modelData.enabled && panel.can(Objects.sectionAction(panel.instance, modelData.id).method)
                        onClicked: panel.run(modelData.id)
                    }
                }
            }
            HudLabel {
                Layout.fillWidth: true
                visible: section.modelData.id === 'remove'
                text: !panel.instance ? '' : panel.instance.source === 'user'
                      ? (panel.instance.locked ? 'Unlock it to remove or reset it. ' : '') + 'Remove deletes it from this world. Reset stands it upright at scale 1.'
                      : 'Authored objects are never deleted. ' + (section.modelData.actions && section.modelData.actions.length > 1 ? 'Hidden ones are not drawn and have no collision. ' : '')
                        + 'Reset puts it back where the world placed it.'
                color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap
            }
            // Data (RFC-0013 draft): where a machine reads its inputs; other objects hide it.
            HudLabel {
                objectName: 'objectDataSource'
                visible: section.modelData.id === 'data' && !!section.modelData.source
                Layout.fillWidth: true
                text: section.modelData.source ? section.modelData.source.line : ''
                font.family: Tokens.mono; font.pixelSize: 13
            }
            HudLabel {
                objectName: 'objectDataHint'
                visible: section.modelData.id === 'data' && !!section.modelData.source
                Layout.fillWidth: true
                text: section.modelData.source ? section.modelData.source.hint : ''
                color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap
            }
        }
    }
}
