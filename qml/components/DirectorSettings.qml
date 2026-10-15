import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../SettingsModel.js" as Model
import "../Quests.js" as Quests

// Director > Settings: categories on the left, one global preset at the top (IPC 0.30), every
// setting with a dot while it is overridden and a way back to the preset's default, reset all,
// and a search across every category.
Item {
    id: root
    // ---- the keymap (Controls & keys): a draft saved with Save keys ----
    property var draft: null
    property var feedback: ({conflicts:[], steals:[]})
    property string mode: 'world'
    property string pending: ''
    property string lastCapture: ''
    readonly property var actions: draft ? Object.keys(draft.modes[mode]).filter(a=>a!=='hud.cycle') : []
    function load() {
        if (ShellState.state && ShellState.state.keymap) {
            draft = JSON.parse(JSON.stringify(ShellState.state.keymap.config));
            feedback = ShellState.state.keymap;
        }
    }
    function preview() { ShellState.action('input.preview', {config:draft}); }
    function change(action, slot, value) {
        var next = JSON.parse(JSON.stringify(draft));
        var bindings = next.modes[mode][action];
        while (bindings.length <= slot) bindings.push('');
        bindings[slot] = value;
        next.modes[mode][action] = bindings.filter(v => v !== '');
        draft = next; pending = ''; preview();
    }
    // tool1-tool5 and tool9 (IPC 0.26, the debug tool) carry the tool's name from core's definitions.
    function actionLabel(action) {
        var m = /^tool([0-9])$/.exec(action), editor = ShellState.state && ShellState.state.editor;
        var tool = m && editor && editor.toolDefinitions ? editor.toolDefinitions.find(d => d.slot === Number(m[1])) : null;
        return action.replace(/_/g, ' ') + (tool ? ' · ' + tool.name : '');
    }
    function details(action) {
        var conflicts = (feedback.conflicts || []).filter(c => c.mode === mode && c.actions.indexOf(action) >= 0).map(c => 'Conflict: ' + c.binding + ' → ' + c.actions.join(' / '));
        var steals = (feedback.steals || []).filter(c => c.mode === mode && c.action === action).map(c => c.binding + ' — steals Hyprland: ' + c.description);
        return conflicts.concat(steals).join('   ·   ');
    }
    // The default bindings of an action (IPC 0.30 settings.get keymapDefaults), or null.
    function defaultBindings(action) {
        var d = ShellState.settingsState && ShellState.settingsState.keymapDefaults;
        return d && d.modes[mode] ? d.modes[mode][action] : null;
    }
    function rebound(action) { var d = defaultBindings(action); return !!d && !!draft && !Model.same(draft.modes[mode][action], d); }
    function resetAction(action) {
        var d = defaultBindings(action);
        if (!d) return;
        var next = JSON.parse(JSON.stringify(draft)); next.modes[mode][action] = d.slice();
        draft = next; pending = ''; preview();
    }
    readonly property bool keymapDirty: !!draft && !!ShellState.state && !!ShellState.state.keymap && !Model.same(draft, ShellState.state.keymap.config)

    // ---- the settings model ----
    readonly property var ctx: ({protocol: ShellState.protocol, settings: ShellState.settingsState, graphics: ShellState.graphics,
                                 player: ShellState.playerSettings, guidance: ShellState.guidance,
                                 keymap: ShellState.state ? ShellState.state.keymap : null, prefs: ShellState.shellPreferences})
    readonly property var guidanceRows: Quests.guidanceRows(ShellState.guidance)
    readonly property var counts: Model.counts(ctx, guidanceRows)
    readonly property string category: ShellState.settingsCategory
    readonly property var categoryRows: Model.rows(category, ctx, guidanceRows)
    readonly property var found: Model.search(query, ctx, guidanceRows)
    readonly property string query: ShellState.settingsSearch
    readonly property bool confirmReset: ShellState.settingsConfirm
    readonly property var presets: Model.presetList(ctx)
    readonly property var currentPreset: presets.find(p => ShellState.settingsState && p.id === ShellState.settingsState.preset) || null
    function groups(rows) {
        var out = [];
        rows.forEach(r => { var g = out.find(x => x.name === r.group); if (!g) out.push(g = {name: r.group, rows: []}); g.rows.push(r); });
        return out;
    }
    function categoryName(id) { var c = Model.CATEGORIES.find(c => c.id === id); return c ? c.name : id; }
    function show(id) { ShellState.settingsCategory = id; ShellState.settingsSearch = ''; scroll.contentItem.contentY = 0; }
    function resetAll() {
        Model.resetAllRequests(ctx).forEach(r => ShellState.settingRequest(r));
        ShellState.settingsConfirm = false;
        load();
    }
    function inkPatch(patch) { // InkSettings: nulls return to the preset, values override
        if (!ShellState.presetsSupported) { ShellState.action('graphics.set', {patch: patch}); return; }
        var set = {}, reset = [];
        Object.keys(patch).forEach(k => { if (patch[k] === null) reset.push('graphics.' + k); else set['graphics.' + k] = patch[k]; });
        var params = {};
        if (reset.length) params.reset = reset;
        if (Object.keys(set).length) params.set = set;
        ShellState.action('settings.set', params);
    }
    onVisibleChanged: {
        if (visible) { load(); ShellState.refreshPlayer(); ShellState.refreshGuidance(); ShellState.refreshSettings(); }
        else { if (pending) pending = ''; ShellState.settingsConfirm = false; }
    }
    Component.onCompleted: load()
    Connections {
        target: ShellState
        // Dev hooks from before categories: 0 appearance, 1 performance, 2 input, 3 movement,
        // 4 reticle, 5 guidance, 6 companion.
        function onBrowseSettings(section) { root.show(['hud', 'display', 'controls', 'movement', 'hud', 'guidance', 'world'][section] || 'display'); }
        function onScrollSettings(fraction) { scroll.contentItem.contentY = Math.max(0, scroll.contentItem.contentHeight - scroll.contentItem.height) * fraction; }
        function onBeginInputCapture(mode, action, slot) {
            root.show('controls');
            root.mode=mode;root.pending=action+':'+slot;root.lastCapture='';ShellState.action('input.capture',{leaseId:ShellState.lease,mode:mode,action:action,slot:slot});
        }
        function onSaveInputDraft() {ShellState.action('input.set',{config:root.draft});}
        function onInputFeedback(result) { root.feedback = result; }
        function onInputCapture(result) {
            var signature = JSON.stringify(result);
            if (signature === root.lastCapture || !root.pending) return;
            root.lastCapture = signature;
            ShellState.lastCapturedInput = result;
            root.mode = result.mode;
            root.change(result.action,result.slot,result.binding);
            ShellState.action('input.capture.cancel',{});
        }
    }
    onPendingChanged: {
        if (!pending) ShellState.action('input.capture.cancel', {});
        else Qt.callLater(function() {
            var index = root.actions.indexOf(root.pending.split(':')[0]);
            var row = bindingRows.itemAt(index);
            if (row && scroll.contentItem) {
                var point = row.mapToItem(scroll.contentItem.contentItem, 0, 0);
                scroll.contentItem.contentY = Math.max(0, Math.min(point.y, scroll.contentItem.contentHeight - scroll.contentItem.height));
            }
        });
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 12
        // Title, the preset, overrides and reset all.
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            HudLabel { text: 'Settings'; font.pixelSize: Tokens.title }
            Item { Layout.fillWidth: true }
            HudLabel { visible: ShellState.presetsSupported; text: 'Preset'; color: Tokens.muted }
            Choice {
                id: presetChoice
                objectName: 'settings-preset'
                visible: ShellState.presetsSupported && root.presets.length > 0
                Layout.preferredWidth: 280
                model: root.presets.map(p => p.name)
                enabled: ShellState.available('settings.set')
                onActivated: index => ShellState.setPreset(root.presets[index].id)
                Binding on currentIndex { value: root.presets.findIndex(p => root.currentPreset && p.id === root.currentPreset.id); when: !presetChoice.popup.visible }
            }
            HudLabel { objectName: 'settings-override-count'; text: root.counts.total === 1 ? '1 change' : root.counts.total + ' changes'; color: root.counts.total ? Tokens.accent : Tokens.muted; font.pixelSize: 12 }
            ActionButton { objectName: 'settings-reset-all'; text: 'Reset all…'; enabled: root.counts.total > 0; onClicked: ShellState.settingsConfirm = true }
        }
        HudLabel {
            Layout.fillWidth: true
            wrapMode: Text.Wrap; color: Tokens.muted; font.pixelSize: 12
            text: !ShellState.presetsSupported ? 'Global presets need a core with IPC 0.30; settings below still save as before.'
                  : root.currentPreset ? root.currentPreset.description + '  Changing the preset keeps what you changed (the dotted settings).' : ''
        }
        Rectangle {
            objectName: 'settings-reset-confirm'
            visible: root.confirmReset
            Layout.fillWidth: true
            implicitHeight: confirmRow.implicitHeight + 20
            radius: Tokens.radius; color: Tokens.raised; border.color: Tokens.gold
            RowLayout {
                id: confirmRow
                anchors { fill: parent; margins: 10 }
                HudLabel { Layout.fillWidth: true; wrapMode: Text.Wrap; text: 'Reset every setting to the ' + (root.currentPreset ? root.currentPreset.name : 'default') + ' defaults? This clears ' + root.counts.total + (root.counts.total === 1 ? ' change' : ' changes') + ', key bindings included. The preset stays.' }
                ActionButton { objectName: 'settings-reset-all-confirm'; text: 'Reset all'; primary: true; onClicked: root.resetAll() }
                ActionButton { text: 'Cancel'; onClicked: ShellState.settingsConfirm = false }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 16
            // Categories (and the search).
            ColumnLayout {
                Layout.preferredWidth: 250
                Layout.maximumWidth: 250
                Layout.fillHeight: true
                spacing: 4
                TextField {
                    id: searchField
                    objectName: 'settings-search'
                    Layout.fillWidth: true
                    placeholderText: 'Search settings'
                    onTextEdited: ShellState.settingsSearch = text
                    Binding on text { value: root.query; when: !searchField.activeFocus || root.query === '' }
                    color: Tokens.text
                    font.pixelSize: 13
                    background: Rectangle { radius: Tokens.radius; color: Tokens.panel; border.color: searchField.activeFocus ? Tokens.gold : Tokens.line }
                    Keys.onEscapePressed: event => { if (root.query) { ShellState.settingsSearch = ''; event.accepted = true; } else event.accepted = false; }
                }
                Repeater {
                    model: Model.CATEGORIES
                    ActionButton {
                        required property var modelData
                        required property int index
                        objectName: 'settings-category-' + modelData.id
                        Layout.fillWidth: true
                        text: modelData.name + (root.counts[modelData.id] ? '  ·  ' + root.counts[modelData.id] : '')
                        primary: !root.query && root.category === modelData.id
                        onClicked: root.show(modelData.id)
                        Keys.onUpPressed: { if (index > 0) { root.show(Model.CATEGORIES[index - 1].id); nextItemInFocusChain(false).forceActiveFocus(); } }
                        Keys.onDownPressed: { if (index < Model.CATEGORIES.length - 1) { root.show(Model.CATEGORIES[index + 1].id); nextItemInFocusChain(true).forceActiveFocus(); } }
                    }
                }
                Item { Layout.fillHeight: true }
            }
            ScrollView {
                id: scroll
                Layout.fillWidth: true; Layout.fillHeight: true
                contentWidth: availableWidth
                clip: true
                ColumnLayout {
                    width: Math.min(scroll.availableWidth - 16, 1100)
                    spacing: 14
                    HudLabel { text: root.query ? 'Search: ' + root.query : root.categoryName(root.category); font.pixelSize: 20; Layout.fillWidth: true }
                    // Search results across every category.
                    HudLabel { visible: !!root.query && root.found.length === 0; text: 'No setting matches.'; color: Tokens.muted }
                    Repeater {
                        model: root.query ? root.found : []
                        ColumnLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: 2
                            HudLabel { text: root.categoryName(modelData.category).toUpperCase() + ' · ' + (modelData.group || '').toUpperCase(); color: Tokens.gold; font.pixelSize: Tokens.caption; font.letterSpacing: 1.5 }
                            SettingRow { row: modelData; ctx: root.ctx }
                        }
                    }
                    // The category's own top blocks.
                    HudLabel {
                        visible: !root.query && root.category === 'display'
                        Layout.fillWidth: true
                        text: 'Live · ' + HudData.stats + (ShellState.graphics && ShellState.graphics.performance ? '  ·  ' + (ShellState.graphics.performance.activeRenderer === 'offload' ? 'offload renderer' : 'in-process renderer') : '')
                        font.family: Tokens.mono; color: Tokens.accent; font.pixelSize: 13; wrapMode: Text.Wrap
                    }
                    // Grouped rows.
                    Repeater {
                        model: root.query ? [] : root.groups(root.categoryRows)
                        ColumnLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: 10
                            Rectangle { Layout.fillWidth: true; height: 1; color: Tokens.line }
                            HudLabel { text: String(modelData.name).toUpperCase(); color: Tokens.gold; font.pixelSize: Tokens.caption; font.letterSpacing: 1.5 }
                            ReticlePreview {
                                visible: modelData.name === 'Reticle' && !!ShellState.playerSettings
                                style: ShellState.playerSettings ? ShellState.playerSettings.config.reticle_style : 'cross_dot'
                                size: ShellState.playerSettings ? ShellState.playerSettings.config.reticle_size : 18
                                thickness: ShellState.playerSettings ? ShellState.playerSettings.config.reticle_thickness : 2
                                gap: ShellState.playerSettings ? ShellState.playerSettings.config.reticle_gap : 4
                                reticleOpacity: ShellState.playerSettings ? ShellState.playerSettings.config.reticle_opacity : .9
                                outline: ShellState.playerSettings ? ShellState.playerSettings.config.reticle_outline : true
                                colour: { var c = ShellState.playerSettings && ShellState.playerSettings.config.reticle_colour; return Array.isArray(c) ? Qt.rgba(c[0], c[1], c[2], 1) : Tokens.hudForeground; }
                            }
                            Repeater {
                                model: modelData.rows
                                SettingRow { required property var modelData; row: modelData; ctx: root.ctx }
                            }
                            // Offload: which GPU (automatic or pinned to the one in use).
                            RowLayout {
                                visible: modelData.name === 'Offload renderer' && !!ShellState.graphics && ShellState.graphics.config.offload_device !== undefined
                                Layout.fillWidth: true
                                spacing: 12
                                HudLabel { text: 'GPU'; Layout.preferredWidth: 294 }
                                Choice {
                                    objectName: 'graphics-offload_device'
                                    Layout.fillWidth: true; Layout.maximumWidth: 360
                                    readonly property var device: ShellState.graphics && ShellState.graphics.performance ? ShellState.graphics.performance.device : null
                                    model: ['Automatic', device ? 'Pin ' + (device.name || device.pci) : 'Pin the GPU in use']
                                    currentIndex: ShellState.graphics && ShellState.graphics.config.offload_device === 'auto' ? 0 : 1
                                    enabled: !!device && ShellState.available('graphics.set')
                                    onActivated: index => ShellState.settingRequest(Model.setRequest({key: 'graphics.offload_device'}, index === 0 ? 'auto' : device.pci, root.ctx))
                                }
                            }
                        }
                    }
                    // Display: outlines (with the world's ink).
                    ColumnLayout {
                        visible: !root.query && root.category === 'display' && !!ShellState.graphics && ShellState.graphics.config.outline !== undefined
                        Layout.fillWidth: true
                        Rectangle { Layout.fillWidth: true; height: 1; color: Tokens.line }
                        InkSettings { Layout.fillWidth: true; graphics: ShellState.graphics; onGraphicsPatch: patch => root.inkPatch(patch) }
                    }
                    // Controls & keys: the keymap.
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 12; visible: !root.query && root.category === 'controls'
                        Rectangle { Layout.fillWidth: true; height: 1; color: Tokens.line }
                        RowLayout {
                            Layout.fillWidth: true
                            HudLabel { text: 'KEYS'; color: Tokens.gold; font.pixelSize: Tokens.caption; font.letterSpacing: 1.5; Layout.fillWidth: true }
                            ActionButton { text: 'Revert'; enabled: root.keymapDirty; onClicked: root.load() }
                            ActionButton { objectName: 'settings-save-keys'; text: 'Save keys'; primary: true; enabled: root.keymapDirty && !(root.feedback.conflicts || []).length && ShellState.available('input.set'); onClicked: ShellState.action('input.set',{config:root.draft}) }
                        }
                        HudLabel { Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.draft ? 'Choose a binding, then press a key, chord, mouse button or wheel. × clears a binding, ↺ restores the default. Changes apply with Save keys.' : 'Key bindings need a core connection with input control.'; color: Tokens.muted; font.pixelSize: 12 }
                        RowLayout {
                            visible: !!root.draft
                            HudLabel { text: 'Input mode'; Layout.preferredWidth: 140 }
                            Choice { model: ['world','interactive','focus','menu']; currentIndex: model.indexOf(root.mode); onActivated: { root.pending = ''; root.mode = currentText; } }
                        }
                        Repeater {
                            id: bindingRows
                            model: root.actions
                            delegate: ColumnLayout {
                                required property string modelData
                                Layout.fillWidth: true
                                spacing: 8
                                Rectangle { Layout.fillWidth: true; height: 1; color: Tokens.line }
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 6
                                    Rectangle { width: 8; height: 8; radius: 4; color: root.rebound(modelData) ? Tokens.accent : 'transparent'; border.width: root.rebound(modelData) ? 0 : 1; border.color: Tokens.line }
                                    HudLabel { text: root.actionLabel(modelData); color: Tokens.text; Layout.fillWidth: true; wrapMode: Text.Wrap }
                                    ActionButton {
                                        implicitWidth: 36; leftPadding: 6; rightPadding: 6; text: '↺'
                                        enabled: root.rebound(modelData); opacity: root.rebound(modelData) ? 1 : .35
                                        Accessible.name: 'Default bindings'
                                        ToolTip.text: 'Default: ' + ((root.defaultBindings(modelData) || []).join(' / ') || 'unbound'); ToolTip.visible: hovered && root.rebound(modelData)
                                        onClicked: root.resetAction(modelData)
                                    }
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 12
                                    Repeater {
                                        model: 3
                                        delegate: RowLayout {
                                            required property int index
                                            Layout.fillWidth: true
                                            Layout.minimumWidth: 0
                                            Layout.preferredWidth: 1
                                            spacing: 4
                                            ActionButton {
                                                Layout.fillWidth: true
                                                Layout.minimumWidth: 0
                                                primary: root.pending === modelData + ':' + index
                                                text: root.pending === modelData + ':' + index ? 'Press input…' : root.draft.modes[root.mode][modelData][index] || 'Capture…'
                                                onClicked: {root.pending=modelData + ':' + index; root.lastCapture=''; ShellState.action('input.capture',{leaseId:ShellState.lease,mode:root.mode,action:modelData,slot:index});}
                                            }
                                            ActionButton { implicitWidth: 36; leftPadding: 6; rightPadding: 6; text: '×'; Accessible.name: 'Clear binding'; ToolTip.text: 'Clear binding'; ToolTip.visible: hovered; enabled: !!root.draft.modes[root.mode][modelData][index]; onClicked: root.change(modelData,index,'') }
                                        }
                                    }
                                }
                                HudLabel { Layout.fillWidth: true; text: root.details(modelData); color:Tokens.gold; font.pixelSize:12; wrapMode:Text.Wrap; visible:text.length > 0 }
                            }
                        }
                    }
                    // World & characters: the companion.
                    ColumnLayout {
                        visible: !root.query && root.category === 'world' && ShellState.companionSupported
                        Layout.fillWidth: true
                        Rectangle { Layout.fillWidth: true; height: 1; color: Tokens.line }
                        CompanionSettings { Layout.fillWidth: true }
                    }
                    // Data sources: they have a page of their own.
                    ColumnLayout {
                        visible: !root.query && root.category === 'data'
                        Layout.fillWidth: true
                        spacing: 10
                        HudLabel { Layout.fillWidth: true; wrapMode: Text.Wrap; text: 'Data sources feed live values (a command, a file or a web address) into gauges, screens and machines in the world. They are set up in Director > Objects > Data sources.'; color: Tokens.muted }
                        ActionButton { objectName: 'settings-open-data-sources'; text: 'Open Data sources'; onClicked: { ShellState.objectsView = 'sources'; ShellState.tab = ShellState.tabObjects; } }
                    }
                    // Recording: the debug recording (Ctrl+R).
                    ColumnLayout {
                        visible: !root.query && root.category === 'recording'
                        Layout.fillWidth: true
                        spacing: 10
                        HudLabel {
                            Layout.fillWidth: true; wrapMode: Text.Wrap
                            text: 'Press ' + root.recordKey() + ' in the world to record a debug stream: input, camera and frame timing, for measuring how motion feels. A red REC dot shows while it runs; on stop you can give it a label. Recordings are private files in ~/.local/state/hyprune/recordings/.'
                        }
                        ActionButton { text: 'Change the key'; onClicked: { root.mode = 'world'; root.show('controls'); } }
                        HudLabel { Layout.fillWidth: true; wrapMode: Text.Wrap; color: Tokens.muted; font.pixelSize: 12; text: 'Managing recordings here, video export and sharing are planned.' }
                    }
                    // Advanced: about.
                    ColumnLayout {
                        visible: !root.query && root.category === 'advanced'
                        Layout.fillWidth: true
                        spacing: 8
                        Rectangle { Layout.fillWidth: true; height: 1; color: Tokens.line }
                        HudLabel { text: 'ABOUT'; color: Tokens.gold; font.pixelSize: Tokens.caption; font.letterSpacing: 1.5 }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            BrandMark { id: aboutMark; objectName: 'brandMark:about'; size: 48; color: Tokens.accent; Layout.leftMargin: -inkLeft; Layout.alignment: Qt.AlignVCenter }
                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                spacing: 4
                                HudLabel { Layout.fillWidth: true; text: 'Hyprune shell ' + ShellState.shellVersion + '  ·  IPC ' + ShellState.protocol }
                                HudLabel { Layout.fillWidth: true; text: 'Shell MIT licence. Hyprune logo by Hyprune contributors, CC-BY-4.0.'; color: Tokens.muted; wrapMode: Text.Wrap; font.pixelSize: 12 }
                                HudLabel { Layout.fillWidth: true; visible: !!ShellState.settingsState; text: ShellState.settingsState ? 'Settings: ' + ShellState.settingsState.path : ''; color: Tokens.muted; wrapMode: Text.Wrap; font.pixelSize: 12 }
                            }
                        }
                    }
                    HudLabel { Layout.fillWidth: true; visible: text !== ''; text: ShellState.settingsState ? ShellState.settingsState.error : ''; color: Tokens.gold; font.pixelSize: 12; wrapMode: Text.Wrap }
                }
            }
        }
        RowLayout {
            visible: root.pending !== ''
            Layout.fillWidth: true
            HudLabel { Layout.fillWidth: true; text: 'Listening · ' + root.mode + ' / ' + root.pending.split(':')[0] + ' · press a key or chord…'; color: Tokens.gold }
            ActionButton { text: 'Cancel capture'; onClicked: root.pending = '' }
        }
        HudLabel { Layout.fillWidth: true; visible: text !== ''; text: ShellState.state && ShellState.state.keymap ? ShellState.state.keymap.error : ''; color:Tokens.gold; font.pixelSize:12; wrapMode: Text.Wrap }
    }
    function recordKey() {
        var k = ShellState.state && ShellState.state.keymap && ShellState.state.keymap.config.modes.world['record.toggle'];
        return k && k.length ? k.join(' / ').replace('Ctrl+r', 'Ctrl+R') : 'the record key (unbound)';
    }
}
