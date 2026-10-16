import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../Objects.js" as Objects
import "../Import.js" as Import

// Director > Objects > Placed > Model (RFC-0014 Managing objects, as amended): an imported
// object's fit after the fact. Adjust sets the units, up axis, turn and surface again (absolute
// values, as at import); Simplify decimates it again and shrinks its textures, with the numbers
// before and after. Each keeps a backup; a world folder's copy shows after the folder reloads.
ColumnLayout {
    id: panel
    objectName: 'objectModel'
    property var instance: null
    property var entry: null
    readonly property string ref: instance ? String(instance.ref) : ''
    readonly property var fit: ShellState.objectFit && ShellState.objectFit.ref === ref ? ShellState.objectFit : null
    property var draft: ({})
    property string triangles: ''
    property string texture: '2048'
    spacing: 8
    onRefChanged: { draft = {}; triangles = ''; if (visible && ref) ShellState.objectEditRun('fit', ref); }
    onVisibleChanged: { if (visible && ref && !fit) ShellState.objectEditRun('fit', ref); }

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
    component Note: HudLabel { Layout.fillWidth: true; font.pixelSize: 12; color: Tokens.muted; wrapMode: Text.Wrap }
    function value(key) { return draft[key] !== undefined ? draft[key] : fit ? String(fit.fit[key]) : ''; }
    function set(key, v) { var d = Object.assign({}, draft); d[key] = v; draft = d; }
    readonly property bool changed: !!fit && Object.keys(draft).some(k => String(draft[k]) !== String(fit.fit[k]))

    Rectangle { Layout.fillWidth: true; height: 1; color: Tokens.line }
    HudLabel { text: 'MODEL'; font.pixelSize: 11; color: Tokens.gold; font.letterSpacing: 2 }
    Note { objectName: 'object-fit'; text: panel.fit ? Objects.fitText(panel.fit) + (panel.fit.triangles ? '  ' + Import.count(panel.fit.triangles) + ' triangles.' : '') : 'Reading how it was imported…' }
    Note { visible: !!panel.fit && !panel.fit.adjustable; color: Tokens.warning; text: panel.fit && panel.fit.reason ? panel.fit.reason + '.' : '' }
    ColumnLayout {
        visible: !!panel.fit && panel.fit.adjustable
        Layout.fillWidth: true
        spacing: 8
        Segmented { objectName: 'fitUnits'; Layout.preferredWidth: 300; model: Objects.FIT_UNITS; current: panel.value('units'); onPicked: (id) => panel.set('units', id) }
        Segmented { objectName: 'fitUp'; Layout.preferredWidth: 180; model: Import.UP; current: panel.value('up'); onPicked: (id) => panel.set('up', id) }
        Segmented { objectName: 'fitYaw'; Layout.preferredWidth: 300; model: Import.YAW; current: panel.value('yaw'); onPicked: (id) => panel.set('yaw', id) }
        Segmented { objectName: 'fitSurface'; Layout.preferredWidth: 360; model: Import.SURFACES; current: panel.value('surface'); onPicked: (id) => panel.set('surface', id) }
        RowLayout {
            spacing: 8
            ActionButton {
                objectName: 'object-adjust'
                text: ShellState.objectEditBusy && ShellState.objectEditJob.kind === 'adjust' ? 'Adjusting…' : 'Adjust'
                enabled: panel.changed && !ShellState.objectEditBusy
                onClicked: { if (ShellState.objectEditRun('adjust', panel.ref, panel.draft)) panel.draft = {}; }
            }
            ActionButton { text: 'Undo changes'; visible: panel.changed; onClicked: panel.draft = {} }
        }
        Note { text: 'Sizes and axes as at import. Every placement of this object changes with it; a backup is kept.' }
        RowLayout {
            spacing: 8
            Field {
                objectName: 'object-simplify-triangles'
                Layout.preferredWidth: 140; Layout.fillWidth: false
                placeholderText: panel.fit && panel.fit.triangles ? String(Math.max(100, Math.round(panel.fit.triangles / 2))) : '50000'
                text: panel.triangles
                onTextEdited: panel.triangles = text
            }
            Segmented { objectName: 'object-simplify-texture'; Layout.preferredWidth: 330; model: Import.TEXTURES; current: panel.texture; onPicked: (id) => panel.texture = id }
            ActionButton {
                objectName: 'object-simplify'
                text: ShellState.objectEditBusy && ShellState.objectEditJob.kind === 'simplify' ? 'Simplifying…' : 'Simplify'
                enabled: !ShellState.objectEditBusy && !!panel.fit
                onClicked: ShellState.objectEditRun('simplify', panel.ref, {maxTriangles: panel.triangles || (panel.fit.triangles ? Math.max(100, Math.round(panel.fit.triangles / 2)) : 50000), maxTexture: panel.texture})
            }
        }
    }
    Note {
        objectName: 'object-edit-result'
        readonly property var last: ShellState.objectEditLast
        visible: !!last && last.ref === panel.ref
        color: last && last.phase === 'failed' ? Tokens.warning : Tokens.muted
        text: !visible ? '' : last.phase === 'failed' ? last.error.message + (last.error.hint ? ' ' + last.error.hint + '.' : '') : Objects.editResultText(last.kind, last.result)
    }
}
