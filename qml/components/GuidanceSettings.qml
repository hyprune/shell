import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../Quests.js" as Quests

// Settings > Guidance (IPC 0.21, RFC-0012): markers, quest notifications and focus
// sessions through guidance.get / guidance.set (the player settings pattern).
ColumnLayout {
    id: root
    objectName: 'guidanceSettings'
    readonly property var settings: ShellState.guidance
    readonly property bool editable: ShellState.available('guidance.set')
    readonly property var rows: Quests.guidanceRows(settings)
    function value(key) { return settings && settings.config ? settings.config[key] : undefined; }
    function set(key, v) { ShellState.patchGuidance(Quests.guidancePatch(settings, key, v)); }
    spacing: 12

    HudLabel { Layout.fillWidth: true; text: root.settings ? 'Live changes · saved automatically' : 'Waiting for guidance settings from core.'; color: Tokens.muted; font.pixelSize: 12 }
    Repeater {
        model: root.rows
        ColumnLayout {
            id: entry
            required property var modelData
            readonly property var range: root.settings && root.settings.ranges ? root.settings.ranges[modelData.key] : null
            readonly property var options: root.settings && root.settings.options ? root.settings.options[modelData.key] || [] : []
            readonly property bool overridden: !!(root.settings && root.settings.overrides && root.settings.overrides[modelData.key] !== undefined)
            Layout.fillWidth: true
            spacing: 4
            Rectangle { visible: entry.modelData.first; Layout.fillWidth: true; Layout.topMargin: 6; height: 1; color: Tokens.line }
            HudLabel { visible: entry.modelData.first; text: entry.modelData.group; color: Tokens.gold; font.pixelSize: Tokens.caption; font.letterSpacing: 1.5; Layout.fillWidth: true; Layout.bottomMargin: 4 }
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                HudLabel { text: entry.modelData.name; Layout.preferredWidth: 260; wrapMode: Text.Wrap }
                SettingSlider {
                    id: slider
                    objectName: 'guidance-' + entry.modelData.key
                    visible: entry.modelData.type === 'number' && !!entry.range
                    Layout.fillWidth: true
                    from: entry.range ? entry.range[0] : 0; to: entry.range ? entry.range[1] : 1
                    stepSize: entry.modelData.step || 1
                    value: Number(root.value(entry.modelData.key)) || 0
                    enabled: root.editable
                    onMoved: root.set(entry.modelData.key, value)
                }
                HudLabel {
                    visible: slider.visible
                    Layout.preferredWidth: 120
                    horizontalAlignment: Text.AlignRight
                    text: Quests.guidanceValue(root.settings, entry.modelData.key, slider.value)
                    font.pixelSize: 12
                }
                Segmented {
                    objectName: 'guidance-' + entry.modelData.key
                    visible: entry.modelData.type === 'enum'
                    Layout.fillWidth: true
                    model: entry.options.map(o => ({id: o, label: entry.modelData.labels && entry.modelData.labels[o] ? entry.modelData.labels[o] : o}))
                    current: String(root.value(entry.modelData.key) || '')
                    enabled: root.editable
                    onPicked: (option) => root.set(entry.modelData.key, option)
                }
                ActionButton {
                    objectName: 'guidance-' + entry.modelData.key
                    visible: entry.modelData.type === 'bool'
                    Layout.fillWidth: true
                    text: root.value(entry.modelData.key) ? 'On' : 'Off'
                    primary: !!root.value(entry.modelData.key)
                    enabled: root.editable
                    onClicked: root.set(entry.modelData.key, !root.value(entry.modelData.key))
                }
                ActionButton {
                    implicitWidth: 36; leftPadding: 6; rightPadding: 6
                    text: '↺'
                    enabled: root.editable && entry.overridden
                    Accessible.name: 'Default'
                    ToolTip.text: 'Back to the default'; ToolTip.visible: hovered
                    onClicked: root.set(entry.modelData.key, null)
                }
            }
            HudLabel { visible: !!entry.modelData.note; Layout.fillWidth: true; text: entry.modelData.note || ''; color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap }
        }
    }
    ActionButton {
        objectName: 'guidance-reset'
        Layout.fillWidth: true
        Layout.topMargin: 8
        text: 'Reset guidance'
        enabled: root.editable && !!root.settings && Object.keys(root.settings.overrides || {}).length > 0
        onClicked: { var patch = {}; Object.keys(root.settings.overrides).forEach(k => patch[k] = null); ShellState.patchGuidance(patch); }
    }
    HudLabel { Layout.fillWidth: true; visible: text !== ''; text: root.settings ? root.settings.error || '' : ''; color: Tokens.gold; font.pixelSize: 12; wrapMode: Text.Wrap }
}
