import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"

Item {
    id: root
    property var draft: null
    property var feedback: ({conflicts:[], steals:[]})
    property string mode: 'world'
    property int section: 0
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
    function details(action) {
        var conflicts = (feedback.conflicts || []).filter(c => c.mode === mode && c.actions.indexOf(action) >= 0).map(c => 'Conflict: ' + c.binding + ' → ' + c.actions.join(' / '));
        var steals = (feedback.steals || []).filter(c => c.mode === mode && c.action === action).map(c => c.binding + ' — steals Hyprland: ' + c.description);
        return conflicts.concat(steals).join('   ·   ');
    }
    readonly property bool playerSection: section === 3 || section === 4
    onVisibleChanged: { if (visible) { load(); if (playerSection) ShellState.refreshPlayer(); if (section === 5) ShellState.refreshGuidance(); } else if (pending) pending = ''; }
    onPlayerSectionChanged: { if (playerSection && visible) ShellState.refreshPlayer(); }
    onSectionChanged: { if (section === 5 && visible) ShellState.refreshGuidance(); }
    Component.onCompleted: load()
    Connections {
        target: ShellState
        function onBrowseSettings(section) { if (section === 1) { ShellState.tab=ShellState.tabPerformance; return; } root.section = section; scroll.contentItem.contentY = 0; }
        function onScrollSettings(fraction) { scroll.contentItem.contentY = Math.max(0, scroll.contentItem.contentHeight - scroll.contentItem.height) * fraction; }
        function onBeginInputCapture(mode, action, slot) {
            root.section = 2;
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
    function option(name, value) {
        if (!draft) return;
        var next = JSON.parse(JSON.stringify(draft)); next[name] = value;
        draft = next; preview();
    }
    ColumnLayout {
        anchors.fill: parent
        spacing: 12
        RowLayout {
            Layout.fillWidth: true
            HudLabel { text: 'Settings'; font.pixelSize: Tokens.title; Layout.fillWidth: true }
            ActionButton { visible: root.section === 2; text: 'Revert'; enabled: !!root.draft; onClicked: root.load() }
            ActionButton { visible: root.section === 2; text: 'Save input'; primary: true; enabled: !!root.draft && !(root.feedback.conflicts || []).length && ShellState.available('input.set'); onClicked: ShellState.action('input.set',{config:root.draft}) }
        }
        RowLayout {
            Layout.fillWidth: true
            Repeater {
                // Movement and Reticle need IPC 0.19 player settings.
                model: [{name:'Appearance',section:0},{name:'Performance',section:1},{name:'Input bindings',section:2}]
                       .concat(ShellState.playerSupported ? [{name:'Movement',section:3},{name:'Reticle',section:4}] : [])
                       .concat(ShellState.available('guidance.get') ? [{name:'Guidance',section:5}] : [])
                       .concat(ShellState.companionSupported ? [{name:'Companion',section:6}] : [])
                ActionButton {
                    required property var modelData
                    objectName: 'settings-section-' + modelData.section
                    Layout.fillWidth: true; Layout.minimumWidth: 0; Layout.preferredWidth: 1
                    text: modelData.name; primary: root.section === modelData.section
                    onClicked: { if (modelData.section === 1) ShellState.tab = ShellState.tabPerformance; else root.section = modelData.section; }
                }
            }
        }
        ScrollView {
            id: scroll
            Layout.fillWidth: true; Layout.fillHeight: true
            contentWidth: availableWidth
            clip: true
            ColumnLayout {
                width: Math.min(scroll.availableWidth - 16, 1100)
                spacing: 16
                ColumnLayout {
                Layout.fillWidth: true; spacing: 16; visible: root.section === 0
                RowLayout {
                    Layout.fillWidth: true
                    HudLabel { text: 'HUD concept'; Layout.fillWidth: true }
                    Choice { Layout.preferredWidth: 250; model: ['Adventure','Instrument','Minimal']; currentIndex: model.indexOf(Tokens.hudConcept); onActivated: ShellState.setConcept(currentText) }
                }
                RowLayout {
                    Layout.fillWidth: true
                    HudLabel { text: 'Resource bar'; Layout.fillWidth: true }
                    Choice { Layout.preferredWidth: 250; property var values: ['gpu','cpu','ram','tool']; model: ['GPU frame budget','CPU render budget','RAM (GPU fallback)','Tool capacity']; currentIndex: values.indexOf(Tokens.hudResource); onActivated: ShellState.preference({resource:values[currentIndex]}) }
                }
                ActionButton { Layout.fillWidth:true; text:'Use world HUD styles · '+(Tokens.worldStyles ? 'On' : 'Off'); onClicked:ShellState.preference({worldStyles:!Tokens.worldStyles}) }
                HudLabel { text: 'PRESENTATION'; color: Tokens.gold; font.pixelSize: Tokens.caption; Layout.fillWidth: true }
                RowLayout {
                    Layout.fillWidth: true
                    ActionButton { Layout.fillWidth: true; Layout.minimumWidth: 0; text: Tokens.light ? 'Theme · Paper' : 'Theme · Night'; onClicked: Tokens.light = !Tokens.light }
                    ActionButton { Layout.fillWidth: true; Layout.minimumWidth: 0; text: Tokens.reducedMotion ? 'Reduced motion · On' : 'Reduced motion · Off'; onClicked: Tokens.reducedMotion = !Tokens.reducedMotion }
                    ActionButton { Layout.fillWidth: true; Layout.minimumWidth: 0; text: Tokens.hudCurved ? 'Curved HUD · On' : 'Curved HUD · Off'; onClicked: ShellState.preference({curved:!Tokens.hudCurved}) }
                }
                RowLayout {
                    Layout.fillWidth: true
                    HudLabel { text: 'HUD curvature'; Layout.preferredWidth: 140 }
                    SettingSlider { Layout.fillWidth: true; from: 0; to: 1; stepSize: 0.05; value: Tokens.hudCurvature; enabled: Tokens.hudCurved; onMoved: ShellState.preference({curvature:value}) }
                    HudLabel { text: Math.round(Tokens.hudCurvature * 100) + '%'; Layout.preferredWidth: 42 }
                }
                HudLabel { Layout.fillWidth: true; text: 'HUD concepts, curvature and resource selection are saved automatically. Perspective applies to the HUD only.'; color: Tokens.muted; wrapMode: Text.Wrap; font.pixelSize: 12 }
                HudLabel { text: 'ABOUT'; color: Tokens.gold; font.pixelSize: Tokens.caption; Layout.fillWidth: true; Layout.topMargin: 8 }
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
                    }
                }
                }
                ActionButton { visible: root.section === 1; text: 'Open Performance'; onClicked: ShellState.tab = ShellState.tabPerformance }
                HudLabel { Layout.fillWidth: true; visible: root.section === 1 && !ShellState.available('graphics.get'); text: 'Graphics controls require a core with graphics settings support.'; wrapMode: Text.Wrap; color: Tokens.muted }
                HudLabel { Layout.fillWidth: true; visible: root.playerSection && !ShellState.playerSupported; text: 'Movement and reticle settings require core IPC 0.19.'; wrapMode: Text.Wrap; color: Tokens.muted }
                MovementSettings { Layout.fillWidth: true; visible: root.section === 3 && ShellState.playerSupported }
                ReticleSettings { Layout.fillWidth: true; visible: root.section === 4 && ShellState.playerSupported }
                HudLabel { Layout.fillWidth: true; visible: root.section === 5 && !ShellState.available('guidance.get'); text: 'Guidance settings require core IPC 0.21.'; wrapMode: Text.Wrap; color: Tokens.muted }
                GuidanceSettings { Layout.fillWidth: true; visible: root.section === 5 && ShellState.available('guidance.get') }
                CompanionSettings { Layout.fillWidth: true; visible: root.section === 6 && ShellState.companionSupported }
                ColumnLayout {
                Layout.fillWidth: true; spacing: 16; visible: root.section === 2
                HudLabel { text: 'INPUT'; color: Tokens.gold; font.pixelSize: Tokens.caption; Layout.fillWidth: true }
                HudLabel { Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.draft ? 'Choose a binding, then press a key, chord, mouse button or wheel. Clear removes a binding. Changes apply with Save input.' : 'Input settings require a core connection with input control.'; color: Tokens.muted; font.pixelSize: 12 }
                RowLayout {
                    visible: !!root.draft
                    Layout.fillWidth: true
                    HudLabel { text: 'Long hold: ' + (root.draft ? root.draft.longHoldMs : 1000) + ' ms'; Layout.preferredWidth: 160 }
                    SettingSlider { Layout.fillWidth: true; from:100; to:5000; stepSize:50; value:root.draft ? root.draft.longHoldMs : 1000; onMoved: root.option('longHoldMs', Math.round(value)) }
                }
                Flow {
                    visible: !!root.draft
                    Layout.fillWidth: true
                    spacing: 12
                    ActionButton { text: 'Scope vignette · ' + (root.draft && root.draft.scopeVignette ? 'On' : 'Off'); onClicked: root.option('scopeVignette', !root.draft.scopeVignette) }
                    ActionButton { text: 'Invert Y · ' + (root.draft && root.draft.invert_y ? 'On' : 'Off'); onClicked: root.option('invert_y', !root.draft.invert_y) }
                    ActionButton { text: 'Area markers · ' + (root.draft && root.draft.show_area_markers ? 'On' : 'Off'); onClicked: root.option('show_area_markers', !root.draft.show_area_markers) }
                }
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
                        HudLabel { text: modelData.replace(/_/g, ' '); color: Tokens.text; Layout.fillWidth: true; wrapMode: Text.Wrap }
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
}
