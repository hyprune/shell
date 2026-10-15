import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../SettingsModel.js" as Model
import "PerformanceText.js" as PerformanceText

// One setting (SettingsModel.ROWS): its control, a dot while it is overridden (an explicit
// choice that survives preset switches) and a button back to the preset's default.
ColumnLayout {
    id: root
    required property var row
    required property var ctx
    property bool editable: true
    readonly property var entry: Model.entry(row, ctx)
    readonly property bool overridden: entry.source === 'user'
    readonly property bool fromLua: entry.source === 'lua'
    readonly property var options: Model.options(row, ctx)
    readonly property var range: Model.range(row, ctx)
    readonly property string objectKey: row.key.replace('.', '-')
    // Narrow (2x scale, small windows): the columns share the width instead of fixed sizes.
    readonly property bool compact: width > 0 && width < 800
    readonly property real labelWidth: compact ? width * .36 : 300
    readonly property real controlWidth: compact ? width * .44 : 360
    function set(v) { ShellState.settingRequest(Model.setRequest(row, v, ctx)); }
    function reset() { ShellState.settingRequest(Model.resetRequest(row, ctx)); }
    function costText(ms) { return ms ? 'GPU ' + ms + '.' : ''; }
    function optionIndex(v) { for (var i = 0; i < options.length; i++) if (Model.same(options[i].value, v)) return i; return -1; }
    spacing: 2
    Layout.fillWidth: true
    objectName: 'setting:' + row.key

    RowLayout {
        Layout.fillWidth: true
        spacing: 12
        // The label column: a fixed width, so every control lines up (a nested layout would
        // otherwise share the row's spare width with the slider).
        RowLayout {
            Layout.fillWidth: false
            Layout.preferredWidth: root.labelWidth
            Layout.maximumWidth: root.labelWidth
            spacing: 6
            Rectangle {
                objectName: 'overridden:' + root.row.key
                width: 8; height: 8; radius: 4
                color: root.overridden ? Tokens.accent : 'transparent'
                border.width: root.overridden ? 0 : 1
                border.color: Tokens.line
                Accessible.name: root.overridden ? 'Changed from the preset' : 'Preset default'
            }
            HudLabel { text: root.row.label; Layout.fillWidth: true; wrapMode: Text.Wrap; color: root.overridden ? Tokens.text : Tokens.text }
            HudLabel { visible: root.fromLua; text: 'LUA'; color: Tokens.muted; font.family: Tokens.mono; font.pixelSize: 10 }
        }
        // choice
        Choice {
            id: choice
            objectName: root.objectKey
            visible: root.row.kind === 'choice' || root.row.kind === 'colour'
            Layout.preferredWidth: root.controlWidth
            model: root.options.map(o => o.label).concat(root.row.kind === 'colour' && root.optionIndex(root.entry.value) < 0 ? ['Custom'] : [])
            enabled: root.editable
            onActivated: index => { if (index < root.options.length) root.set(root.options[index].value); }
            Binding on currentIndex { value: Math.max(root.optionIndex(root.entry.value), root.row.kind === 'colour' ? root.options.length : 0); when: !choice.popup.visible }
        }
        // toggle
        ActionButton {
            objectName: root.objectKey
            visible: root.row.kind === 'toggle'
            Layout.preferredWidth: Math.min(140, root.controlWidth)
            text: root.entry.value ? 'On' : 'Off'
            primary: !!root.entry.value
            enabled: root.editable
            onClicked: root.set(!root.entry.value)
        }
        // slider (cap: null reads Automatic)
        SettingSlider {
            id: slider
            objectName: root.objectKey
            visible: root.row.kind === 'slider' || root.row.kind === 'cap'
            Layout.preferredWidth: root.controlWidth * .7
            from: root.range[0]; to: root.range[1]; stepSize: root.row.step || 0.01
            enabled: root.editable
            onMoved: root.set(root.row.step && root.row.step >= 1 ? Math.round(value) : Math.round(value / root.row.step) * root.row.step)
            Binding on value { value: root.entry.value === null || root.entry.value === undefined ? slider.from : Number(root.entry.value); when: !slider.pressed }
        }
        HudLabel {
            visible: slider.visible
            Layout.preferredWidth: root.controlWidth * .3 - 12
            horizontalAlignment: Text.AlignRight
            text: root.row.kind === 'cap' && (root.entry.value === null || root.entry.value === undefined) && !slider.pressed ? 'Automatic' : Model.format(root.row, slider.pressed ? slider.value : root.entry.value)
            font.pixelSize: 12
        }
        Item { visible: root.row.kind === 'toggle'; Layout.preferredWidth: root.controlWidth - Math.min(140, root.controlWidth) - 12 }
        ActionButton {
            objectName: 'reset:' + root.row.key
            implicitWidth: 36; leftPadding: 6; rightPadding: 6
            text: '↺'
            enabled: root.overridden && root.editable
            opacity: root.overridden ? 1 : 0.35
            Accessible.name: 'Back to the preset default'
            ToolTip.text: 'Back to the preset default: ' + Model.format(root.row, root.entry.default)
            ToolTip.visible: hovered && root.overridden
            onClicked: root.reset()
        }
    }
    HudLabel {
        Layout.fillWidth: true
        Layout.leftMargin: 14
        visible: text !== ''
        wrapMode: Text.Wrap
        color: Tokens.muted
        font.pixelSize: 12
        text: [root.row.note || '',
               root.overridden && root.entry.default !== null && root.entry.default !== undefined ? 'Default ' + Model.format(root.row, root.entry.default) + '.' : '',
               root.fromLua ? 'Set in the compositor config (Lua).' : '',
               root.row.cost && root.ctx.graphics ? root.costText(PerformanceText.effectCost(root.ctx.graphics.performance, root.ctx.graphics.timings || {}, Model.name(root.row.key))) : '']
              .filter(t => t).join('  ')
    }
}
