import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../PlayerSettings.js" as Player
// IPC 0.19 reticle (player.set reticle_*). Core draws it; state shapes/colours are core's.
ColumnLayout {
    id: root
    readonly property var settings: ShellState.playerSettings
    readonly property bool editable: ShellState.playerEditable
    readonly property bool reducedMotion: !!(ShellState.graphics && ShellState.graphics.config.reduced_motion)
    readonly property var colourValue: value('reticle_colour')
    function value(key) { return Player.value(settings, key); }
    function range(key) { return Player.range(settings, key); }
    function set(key, v) { ShellState.patchPlayer(Player.patch(settings, key, v)); }
    spacing: 12
    HudLabel { text: 'RETICLE'; color: Tokens.gold; font.pixelSize: Tokens.caption; font.letterSpacing: 1.5; Layout.fillWidth: true }
    HudLabel { Layout.fillWidth: true; text: root.settings ? 'Live changes · saved automatically' : 'Waiting for player settings from core.'; color: Tokens.muted; font.pixelSize: 12 }
    RowLayout {
        Layout.fillWidth: true
        spacing: 24
        ReticlePreview {
            Layout.alignment: Qt.AlignTop
            style: root.value('reticle_style')
            size: sizeSlider.value; thickness: thicknessSlider.value; gap: gapSlider.value; reticleOpacity: opacitySlider.value
            outline: root.value('reticle_outline')
            colour: Array.isArray(root.colourValue) ? Qt.rgba(root.colourValue[0], root.colourValue[1], root.colourValue[2], 1) : Tokens.hudForeground
        }
        ColumnLayout {
            Layout.fillWidth: true; Layout.minimumWidth: 0
            spacing: 12
            RowLayout {
                Layout.fillWidth: true
                HudLabel { text: 'Style'; Layout.fillWidth: true }
                Choice { objectName: 'player-reticle_style'; Layout.preferredWidth: 220; model: Player.RETICLE_STYLES.map(o => o.name); currentIndex: Player.styleIndex(root.value('reticle_style')); enabled: root.editable; onActivated: root.set('reticle_style', Player.RETICLE_STYLES[currentIndex].value) }
            }
            RowLayout {
                Layout.fillWidth: true
                HudLabel { text: 'Colour'; Layout.fillWidth: true }
                Rectangle { implicitWidth: 22; implicitHeight: 22; radius: 2; border.color: Tokens.line; color: Array.isArray(root.colourValue) ? Qt.rgba(root.colourValue[0], root.colourValue[1], root.colourValue[2], 1) : Tokens.hudForeground }
                Choice { objectName: 'player-reticle_colour'; Layout.preferredWidth: 220; model: Player.colourNames(root.colourValue); currentIndex: Player.colourIndex(root.colourValue) < 0 ? model.length - 1 : Player.colourIndex(root.colourValue); enabled: root.editable; onActivated: { if (currentIndex < Player.RETICLE_COLOURS.length) root.set('reticle_colour', Player.RETICLE_COLOURS[currentIndex].value); } }
            }
            HudLabel { Layout.fillWidth: true; text: 'Theme follows the HUD concept and world style. Aimed actions use the theme’s positive and warning colours, with distinct shapes.'; color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap }
        }
    }
    Rectangle { Layout.fillWidth: true; height: 1; color: Tokens.line }
    RowLayout {
        Layout.fillWidth: true
        HudLabel { text: 'Size'; Layout.preferredWidth: 190 }
        SettingSlider { id: sizeSlider; objectName: 'player-reticle_size'; Layout.fillWidth: true; from: root.range('reticle_size')[0]; to: root.range('reticle_size')[1]; stepSize: 1; value: root.value('reticle_size'); enabled: root.editable; onMoved: root.set('reticle_size', value) }
        HudLabel { Layout.preferredWidth: 180; text: Player.pixels(sizeSlider.value); horizontalAlignment: Text.AlignRight; font.pixelSize: 12 }
    }
    RowLayout {
        Layout.fillWidth: true
        HudLabel { text: 'Thickness'; Layout.preferredWidth: 190 }
        SettingSlider { id: thicknessSlider; objectName: 'player-reticle_thickness'; Layout.fillWidth: true; from: root.range('reticle_thickness')[0]; to: root.range('reticle_thickness')[1]; stepSize: 0.5; value: root.value('reticle_thickness'); enabled: root.editable; onMoved: root.set('reticle_thickness', value) }
        HudLabel { Layout.preferredWidth: 180; text: Player.pixels(thicknessSlider.value); horizontalAlignment: Text.AlignRight; font.pixelSize: 12 }
    }
    RowLayout {
        Layout.fillWidth: true
        HudLabel { text: 'Gap'; Layout.preferredWidth: 190 }
        SettingSlider { id: gapSlider; objectName: 'player-reticle_gap'; Layout.fillWidth: true; from: root.range('reticle_gap')[0]; to: root.range('reticle_gap')[1]; stepSize: 1; value: root.value('reticle_gap'); enabled: root.editable; onMoved: root.set('reticle_gap', value) }
        HudLabel { Layout.preferredWidth: 180; text: Player.pixels(gapSlider.value); horizontalAlignment: Text.AlignRight; font.pixelSize: 12 }
    }
    RowLayout {
        Layout.fillWidth: true
        HudLabel { text: 'Opacity'; Layout.preferredWidth: 190 }
        SettingSlider { id: opacitySlider; objectName: 'player-reticle_opacity'; Layout.fillWidth: true; from: root.range('reticle_opacity')[0]; to: root.range('reticle_opacity')[1]; stepSize: 0.05; value: root.value('reticle_opacity'); enabled: root.editable; onMoved: root.set('reticle_opacity', value) }
        HudLabel { Layout.preferredWidth: 180; text: Player.percent(opacitySlider.value); horizontalAlignment: Text.AlignRight; font.pixelSize: 12 }
    }
    HudLabel { Layout.fillWidth: true; text: 'Sizes are logical pixels at native resolution, independent of render scale.'; color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap }
    RowLayout {
        Layout.fillWidth: true
        ActionButton { objectName: 'player-reticle_outline'; Layout.fillWidth: true; Layout.minimumWidth: 0; Layout.preferredWidth: 1; text: 'Outline · ' + (root.value('reticle_outline') ? 'On' : 'Off'); enabled: root.editable; onClicked: root.set('reticle_outline', !root.value('reticle_outline')) }
        ActionButton { objectName: 'player-reticle_dynamic'; Layout.fillWidth: true; Layout.minimumWidth: 0; Layout.preferredWidth: 1; text: 'Dynamic · ' + (root.value('reticle_dynamic') ? 'On' : 'Off'); enabled: root.editable; onClicked: root.set('reticle_dynamic', !root.value('reticle_dynamic')) }
    }
    HudLabel { Layout.fillWidth: true; text: 'Outline adds a dark 1 px edge for contrast. Dynamic expands the reticle while moving or turning' + (root.reducedMotion ? '; it is off while Reduced motion is on.' : '; Reduced motion turns it off.'); color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap }
    ActionButton { objectName: 'player-reset_reticle'; text: 'Reset reticle'; Layout.fillWidth: true; enabled: root.editable; onClicked: ShellState.patchPlayer(Player.resetPatch(Player.RETICLE_KEYS)) }
    HudLabel { Layout.fillWidth: true; visible: text !== ''; text: root.settings ? root.settings.error || '' : ''; color: Tokens.gold; font.pixelSize: 12; wrapMode: Text.Wrap }
}
