import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../PlayerSettings.js" as Player
import "../HudManipulation.js" as Manipulation
// IPC 0.19: field of view (graphics.set), walk/run speed, view bob and reach (player.set).
ColumnLayout {
    id: root
    readonly property var settings: ShellState.playerSettings
    readonly property bool editable: ShellState.playerEditable
    readonly property var graphics: ShellState.graphics
    readonly property real fov: graphics && graphics.config.fov !== undefined ? graphics.config.fov : Player.FOV_DEFAULT
    readonly property bool reducedMotion: !!(graphics && graphics.config.reduced_motion)
    property real pendingFov: -1
    function value(key) { return Player.value(settings, key); }
    function range(key) { return Player.range(settings, key); }
    function set(key, v) { ShellState.patchPlayer(Player.patch(settings, key, v)); }
    spacing: 12
    // The 1 s graphics poll must not snap the handle back mid-drag: hold the dragged
    // value until core reports it (or gives up after 1.5 s, e.g. a rejected patch).
    Timer { id: fovCommit; interval: 120; onTriggered: { ShellState.action('graphics.set', {patch: {fov: Math.round(root.pendingFov)}}); fovSettle.restart(); } }
    Timer { id: fovSettle; interval: 1500; onTriggered: root.pendingFov = -1 }
    onFovChanged: { if (Math.round(pendingFov) === fov && !fovCommit.running) pendingFov = -1; }
    HudLabel { text: 'MOVEMENT'; color: Tokens.gold; font.pixelSize: Tokens.caption; font.letterSpacing: 1.5; Layout.fillWidth: true }
    HudLabel { Layout.fillWidth: true; text: root.settings ? 'Live changes · saved automatically' : 'Waiting for player settings from core.'; color: Tokens.muted; font.pixelSize: 12 }
    RowLayout {
        Layout.fillWidth: true
        HudLabel { text: 'Field of view'; Layout.preferredWidth: 190; wrapMode: Text.Wrap }
        SettingSlider { id: fovSlider; objectName: 'player-fov'; Layout.fillWidth: true; from: Player.FOV_RANGE[0]; to: Player.FOV_RANGE[1]; stepSize: 1; value: root.pendingFov >= 0 ? root.pendingFov : root.fov; enabled: ShellState.available('graphics.set') || (ShellState.dev && !!ShellState.playerPreview); onMoved: { root.pendingFov = value; fovCommit.restart(); } }
        HudLabel { Layout.preferredWidth: 180; text: Player.degrees(fovSlider.value) + '  ·  default ' + Player.degrees(Player.FOV_DEFAULT); horizontalAlignment: Text.AlignRight; font.pixelSize: 12 }
    }
    Rectangle { Layout.fillWidth: true; height: 1; color: Tokens.line }
    Repeater {
        model: [{key: 'walk_speed', name: 'Walk speed', note: 'Walking and flight base speed.'},
                {key: 'run_speed', name: 'Run speed', note: 'While sprint (' + Manipulation.keyName(ShellState.state, 'sprint', 'Ctrl') + ') is held. Flight scales by run / walk.'}]
        ColumnLayout {
            required property var modelData
            Layout.fillWidth: true
            spacing: 2
            RowLayout {
                Layout.fillWidth: true
                HudLabel { text: modelData.name; Layout.preferredWidth: 190; wrapMode: Text.Wrap }
                SettingSlider { id: speedSlider; objectName: 'player-' + modelData.key; Layout.fillWidth: true; from: root.range(modelData.key)[0]; to: root.range(modelData.key)[1]; stepSize: 0.1; value: root.value(modelData.key); enabled: root.editable; onMoved: root.set(modelData.key, value) }
                HudLabel { Layout.preferredWidth: 180; text: Player.speed(speedSlider.value); horizontalAlignment: Text.AlignRight; font.pixelSize: 12 }
            }
            HudLabel { Layout.fillWidth: true; Layout.leftMargin: 0; text: modelData.note + '  Default ' + Player.speed(Player.defaultValue(root.settings, modelData.key)) + '.'; color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap }
        }
    }
    RowLayout {
        Layout.fillWidth: true
        HudLabel { text: 'View bob'; Layout.fillWidth: true; wrapMode: Text.Wrap }
        Choice { objectName: 'player-view_bob'; Layout.preferredWidth: 220; model: Player.VIEW_BOB.map(o => o.name); currentIndex: Player.viewBobIndex(root.value('view_bob')); enabled: root.editable; onActivated: root.set('view_bob', Player.VIEW_BOB[currentIndex].value) }
    }
    HudLabel { Layout.fillWidth: true; text: root.reducedMotion ? 'View bob is off while Reduced motion is on in graphics settings.' : 'A gentle sway while walking. Reduced motion always turns it off.'; color: root.reducedMotion ? Tokens.gold : Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap }
    // IPC 0.29 feel settings: smoothing, head tilt and how a carried window follows.
    Rectangle { Layout.fillWidth: true; height: 1; color: Tokens.line; visible: Player.feelSupported(root.settings) }
    HudLabel { text: 'FEEL'; color: Tokens.gold; font.pixelSize: Tokens.caption; font.letterSpacing: 1.5; Layout.fillWidth: true; visible: Player.feelSupported(root.settings) }
    Repeater {
        model: Player.feelSupported(root.settings) ? Player.FEEL : []
        ColumnLayout {
            required property var modelData
            Layout.fillWidth: true
            spacing: 2
            RowLayout {
                Layout.fillWidth: true
                HudLabel { text: modelData.name; Layout.preferredWidth: 190; wrapMode: Text.Wrap }
                SettingSlider { id: feelSlider; objectName: 'player-' + modelData.key; Layout.fillWidth: true; from: root.range(modelData.key)[0]; to: root.range(modelData.key)[1]; stepSize: modelData.ms ? 0.005 : 0.1; value: root.value(modelData.key); enabled: root.editable; onMoved: root.set(modelData.key, value) }
                HudLabel { Layout.preferredWidth: 180; text: Player.feelText(modelData, feelSlider.value); horizontalAlignment: Text.AlignRight; font.pixelSize: 12 }
            }
            HudLabel { Layout.fillWidth: true; text: modelData.note + '  Default ' + Player.feelText(modelData, Player.defaultValue(root.settings, modelData.key)) + '.'; color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap }
        }
    }
    Rectangle { Layout.fillWidth: true; height: 1; color: Tokens.line }
    HudLabel { text: 'REACH'; color: Tokens.gold; font.pixelSize: Tokens.caption; font.letterSpacing: 1.5; Layout.fillWidth: true }
    Repeater {
        model: [{key: 'reach_grab', name: 'Grab', note: 'Super + button window gestures: carry, resize, roll.'},
                {key: 'reach_mount', name: 'Mount', note: 'Snapping windows into mount frames (tools 2 and 5, carry release).'},
                {key: 'reach_placement', name: 'Placement', note: 'Placing on a surface or pocketing (tool 5), mounting on a wall (tool 2), path points (tool 3).'}]
        ColumnLayout {
            required property var modelData
            Layout.fillWidth: true
            spacing: 2
            RowLayout {
                Layout.fillWidth: true
                HudLabel { text: modelData.name; Layout.preferredWidth: 190; wrapMode: Text.Wrap }
                SettingSlider { id: reachSlider; objectName: 'player-' + modelData.key; Layout.fillWidth: true; from: root.range(modelData.key)[0]; to: root.range(modelData.key)[1]; stepSize: 0.5; value: root.value(modelData.key); enabled: root.editable; onMoved: root.set(modelData.key, value) }
                HudLabel { Layout.preferredWidth: 180; text: Player.metres(reachSlider.value); horizontalAlignment: Text.AlignRight; font.pixelSize: 12 }
            }
            HudLabel { Layout.fillWidth: true; text: modelData.note + '  Default ' + Player.metres(Player.defaultValue(root.settings, modelData.key)) + '.'; color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap }
        }
    }
    HudLabel { Layout.fillWidth: true; text: 'Beyond reach, the reticle dims and shows the distance; the action does nothing.'; color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap }
    ActionButton { objectName: 'player-reset_movement'; text: 'Reset movement'; Layout.fillWidth: true; enabled: root.editable; onClicked: { ShellState.patchPlayer(Player.resetPatch(Player.feelSupported(root.settings) ? Player.MOVEMENT_KEYS.concat(Player.FEEL_KEYS) : Player.MOVEMENT_KEYS)); if (root.fov !== Player.FOV_DEFAULT && ShellState.available('graphics.set')) ShellState.action('graphics.set', {patch: {fov: Player.FOV_DEFAULT}}); } }
    HudLabel { Layout.fillWidth: true; text: 'Reset restores field of view, speeds, view bob, feel and reach to their defaults.'; color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap }
    HudLabel { Layout.fillWidth: true; visible: text !== ''; text: root.settings ? root.settings.error || '' : ''; color: Tokens.gold; font.pixelSize: 12; wrapMode: Text.Wrap }
}
