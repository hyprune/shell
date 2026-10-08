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
    property string pending: ''
    property string lastCapture: ''
    readonly property var actions: draft ? Object.keys(draft.modes[mode]) : []
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
    onVisibleChanged: if (visible) load()
    Component.onCompleted: load()
    Connections {
        target: ShellState
        function onBeginInputCapture(mode, action, slot) {
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
    ColumnLayout {
        anchors.fill: parent
        spacing: 12
        RowLayout {
            Text { text: 'INPUT / KEYMAP V2'; color: Tokens.text; font.family: Tokens.mono; font.pixelSize: 16 }
            Item { Layout.fillWidth:true }
            ComboBox { model:['world','interactive','focus','menu']; onActivated: root.mode = currentText }
            Button { text:'Revert'; onClicked: root.load() }
            Button { text:'Save'; enabled: !!root.draft && !(root.feedback.conflicts || []).length; onClicked: ShellState.action('input.set',{config:root.draft}) }
        }
        Text { text: 'Click a binding, then press a key, chord, mouse button or wheel. × clears it. Esc leaves the menu.'; color:Tokens.muted; font.pixelSize:12 }
        RowLayout {
            Text { text:'Long hold: ' + (root.draft ? root.draft.longHoldMs : 1000) + ' ms'; color:Tokens.text }
            Slider {
                Layout.fillWidth:true; from:100; to:5000; stepSize:50
                value:root.draft ? root.draft.longHoldMs : 1000
                onMoved: { var next=JSON.parse(JSON.stringify(root.draft));next.longHoldMs=Math.round(value);root.draft=next;root.preview(); }
            }
            CheckBox {
                text:'Scope vignette'; checked: root.draft ? root.draft.scopeVignette : true
                onClicked: { var next=JSON.parse(JSON.stringify(root.draft));next.scopeVignette=checked;root.draft=next;root.preview(); }
            }
        }
        ScrollView {
            Layout.fillWidth:true; Layout.fillHeight:true
            ColumnLayout {
                width: root.width - 24
                Repeater {
                    model:root.actions
                    delegate: ColumnLayout {
                        required property string modelData
                        Layout.fillWidth:true
                        RowLayout {
                            Text { text:modelData; color:Tokens.text; font.family:Tokens.mono; Layout.preferredWidth:160 }
                            Repeater {
                                model:3
                                delegate: RowLayout {
                                    required property int index
                                    Button {
                                        Layout.preferredWidth:170
                                        text: root.pending === modelData + ':' + index ? 'Press input…' : root.draft.modes[root.mode][modelData][index] || 'Capture…'
                                        onClicked: {root.pending=modelData + ':' + index; root.lastCapture=''; ShellState.action('input.capture',{leaseId:ShellState.lease,mode:root.mode,action:modelData,slot:index});}
                                    }
                                    Button {text:'×'; onClicked: root.change(modelData,index,'')}
                                }
                            }
                        }
                        Text { Layout.fillWidth:true; text:root.details(modelData); color:Tokens.gold; font.pixelSize:11; wrapMode:Text.Wrap; visible:text.length > 0 }
                    }
                }
            }
        }
        Text { text: ShellState.state && ShellState.state.keymap ? ShellState.state.keymap.path + (ShellState.state.keymap.error ? ' · ' + ShellState.state.keymap.error : '') : 'Core IPC 0.6 with input.control required'; color:Tokens.muted; font.pixelSize:10 }
    }
}
