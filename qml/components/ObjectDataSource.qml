pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../Sources.js" as Sources

// Director > Objects > Placed > Data source (RFC-0013 draft) for one machine instance:
//  - its inputs (IPC 0.24 catalog `machine.inputs`) with core's live values (state `live`):
//    value, raw, condition and age;
//  - the source it reads, that source's status and error, and the source helper's last run;
//  - the sources.json command editor: command (Choose… lists folders in the shell),
//    arguments one per line, interval, the exact argv ("Runs: …"), Test (the helper runs it
//    once and publishes nothing; the output is checked against the inputs), Save, Remove,
//    Restart (optionally resetting the running average) and Restart helper.
// bridge/sources.py writes the file and talks to the helper; the shell never runs a command.
// On IPC 0.23 (no `machine`, no `live`) it shows the source id and the editor.
ColumnLayout {
    id: body
    objectName: 'objectDataSourceBody'
    property var instance: null
    property var section: ({})
    readonly property string instanceId: instance ? instance.id : ''
    readonly property var source: section.source || null
    readonly property var machine: section.machine || null
    readonly property bool declared: !!section.declared
    readonly property var liveEntry: Sources.liveFor(ShellState.liveState, instanceId)
    readonly property string sourceId: Sources.sourceId(instanceId, liveEntry)
    readonly property var helper: Sources.helperState(ShellState.sourcesStatus)
    readonly property var limits: ShellState.sourcesStatus && ShellState.sourcesStatus.ok && ShellState.sourcesStatus.status.limits
                                  ? ShellState.sourcesStatus.status.limits : loaded ? loaded.limits : null
    readonly property var bounds: Sources.intervalBounds(limits, !!(loaded && loaded.dev))
    // The helper's view of the entry this editor writes, and of the source the machine reads.
    readonly property var ownSource: Sources.helperSource(ShellState.sourcesStatus, instanceId)
    readonly property string readSlug: Sources.helperSlug(sourceId)
    readonly property var readSource: Sources.helperSource(ShellState.sourcesStatus, readSlug)
    readonly property var lastRun: Sources.lastRunText(readSource || ownSource, now)
    readonly property var rows: Sources.liveRows(declared ? machine : null, liveEntry, now)
    property real now: Date.now()
    property var loaded: null          // the last sources.get answer for this instance
    readonly property var draft: Sources.draftFrom(loaded ? loaded.entry : null, bounds)
    readonly property bool editable: !!source && source.publishable && draft.editable
    readonly property var argv: Sources.buildArgv(scriptField.text, argsField.text)
    readonly property string problem: Sources.draftError(argv, intervalField.text, bounds)
    property var test: null            // the last test answer
    readonly property var validation: test && test.ok ? Sources.validateTest(test.result, declared ? machine : null) : null
    property var feedback: null        // {level, text}
    property bool dirty: false
    property int getSeq: 0
    property int testSeq: 0
    property int actionSeq: 0
    property string busy: ''           // the op in flight: test | save | remove | restart | restartAll
    property string confirm: ''        // 'remove' | 'restartAll' waiting for a second press
    spacing: 10

    function focusFirst() {
        if (!editable) return false;
        scriptField.forceActiveFocus();
        return true;
    }
    function load() {
        loaded = null; test = null; feedback = null; dirty = false; confirm = ''; busy = '';
        browser.visible = false;
        fill(Sources.draftFrom(null, bounds));
        if (instanceId && source && source.publishable) getSeq = ShellState.sourcesRequest('sources.get', {id: instanceId});
    }
    function fill(d) {
        scriptField.text = d.script;
        argsField.text = d.args;
        intervalField.text = String(d.intervalS);
        dirty = false;
    }
    function stepInterval(delta) {
        intervalField.text = String(Sources.clampInterval(Number(intervalField.text) + delta, bounds, draft.intervalS));
        dirty = true;
    }
    function settleInterval() {
        var next = String(Sources.clampInterval(intervalField.text, bounds, draft.intervalS));
        if (next !== intervalField.text) { intervalField.text = next; dirty = true; }
    }
    function request(op, type, payload) {
        actionSeq = ShellState.sourcesRequest(type, payload);
        if (!actionSeq) { feedback = {level: 'warning', text: 'The shell bridge is not connected.'}; return; }
        busy = op; feedback = null; busyTimer.restart();
    }
    function runTest() {
        settleInterval();
        if (problem || busy) return;
        testSeq = ShellState.sourcesRequest('sources.test', {id: instanceId, argv: argv});
        if (testSeq) { busy = 'test'; test = null; feedback = null; busyTimer.restart(); }
    }
    function save() {
        settleInterval();
        if (problem || busy || !editable) return;
        request('save', 'sources.save', {id: instanceId, argv: argv, intervalS: Number(intervalField.text)});
    }
    function confirmed(kind, run) {
        if (confirm === kind) { confirm = ''; run(); }
        else { confirm = kind; confirmTimer.restart(); }
    }

    onInstanceIdChanged: load()
    Component.onCompleted: load()
    onVisibleChanged: {
        ShellState.sourcesWanted = visible;
        if (visible && !dirty) load();
    }
    Component.onDestruction: ShellState.sourcesWanted = false
    Timer { interval: 1000; repeat: true; running: body.visible; onTriggered: body.now = Date.now() }
    Timer { id: confirmTimer; interval: 6000; onTriggered: body.confirm = '' }
    Timer { id: busyTimer; interval: 80000; onTriggered: body.busy = '' }  // the bridge always answers; never stay stuck
    Connections {
        target: ShellState
        function onSourcesReply(reply) {
            if (reply.id !== undefined && reply.id !== body.instanceId) return;
            if (reply.op === 'get' && reply.seq === body.getSeq) {
                body.loaded = reply.ok ? reply : null;
                if (!reply.ok) body.feedback = {level: 'warning', text: reply.error};
                else if (!body.dirty) body.fill(Sources.draftFrom(reply.entry, Sources.intervalBounds(reply.limits, reply.dev)));
            } else if (reply.op === 'test' && reply.seq === body.testSeq) {
                body.test = reply; body.busy = '';
                if (!reply.ok) body.feedback = {level: 'warning', text: reply.error};
            } else if (reply.seq === body.actionSeq && ['save', 'remove', 'restart', 'restartAll'].indexOf(reply.op) >= 0) {
                body.busy = '';
                body.feedback = Sources.resultText(reply);
                if (reply.ok && (reply.op === 'save' || reply.op === 'remove')) {
                    body.dirty = false;
                    body.getSeq = ShellState.sourcesRequest('sources.get', {id: body.instanceId});
                    ShellState.pollSources();
                }
            }
        }
    }
    // Inside the editor, the Objects page's one-letter shortcuts (L, H, R, V, Delete) stay out.
    Keys.onPressed: (event) => {
        if (event.modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)) return;
        if ([Qt.Key_L, Qt.Key_H, Qt.Key_R, Qt.Key_V, Qt.Key_Delete].indexOf(event.key) >= 0) event.accepted = true;
    }

    component Caption: HudLabel { Layout.fillWidth: true; font.pixelSize: 11; color: Tokens.muted }
    component Field: TextField {
        implicitHeight: 38
        color: enabled ? Tokens.text : Tokens.muted
        placeholderTextColor: Tokens.muted
        selectionColor: Tokens.accent
        selectedTextColor: Tokens.ink
        font.family: Tokens.mono; font.pixelSize: 13
        leftPadding: 10; rightPadding: 10
        background: Rectangle {
            radius: Tokens.radius
            color: parent.enabled ? Tokens.panel : 'transparent'
            border.width: parent.activeFocus ? 2 : 1
            border.color: parent.activeFocus ? Tokens.gold : Tokens.line
        }
    }
    component Heading: HudLabel { Layout.fillWidth: true; Layout.topMargin: 4; color: Tokens.gold; font.pixelSize: 10; font.letterSpacing: 1.5 }

    // ---- The source it reads ----
    HudLabel {
        objectName: 'objectDataSource'
        Layout.fillWidth: true
        text: body.source ? body.source.line : ''
        font.family: Tokens.mono; font.pixelSize: 13
    }
    HudLabel {
        objectName: 'objectDataReads'
        Layout.fillWidth: true
        text: !body.instanceId ? '' : body.sourceId ? 'Reads  ' + body.sourceId : 'Reads several sources: see each input.'
        font.family: Tokens.mono; font.pixelSize: 12; color: Tokens.muted
        wrapMode: Text.WrapAnywhere
    }
    HudLabel {
        objectName: 'objectDataStatus'
        Layout.fillWidth: true
        visible: !!body.liveEntry
        text: !body.liveEntry ? '' : body.liveEntry.status === 'error' ? 'Source status: error' + (body.liveEntry.error ? ' · ' + body.liveEntry.error : '')
            : body.liveEntry.status === 'ok' ? 'Source status: ok' + (body.liveEntry.stale ? ' · stale' : '') : 'Source status: no data yet'
        color: body.liveEntry && body.liveEntry.status === 'error' ? Tokens.warning : body.liveEntry && body.liveEntry.status === 'ok' && !body.liveEntry.stale ? Tokens.positive : Tokens.muted
        font.pixelSize: 13; wrapMode: Text.Wrap
    }
    HudLabel {
        objectName: 'objectDataHint'
        Layout.fillWidth: true
        visible: !!body.source && !body.source.publishable
        text: body.source ? body.source.hint : ''
        color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap
    }

    // ---- Inputs and live values ----
    Heading { text: 'INPUTS' }
    HudLabel {
        objectName: 'objectDataNoInputs'
        Layout.fillWidth: true
        visible: !body.declared || !body.rows.length || !body.liveEntry
        text: !body.declared ? 'Inputs and live values need core IPC 0.24.'
            : !body.rows.length ? 'This machine declares no inputs.' : 'Core has no live values for it yet.'
        color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap
    }
    Repeater {
        model: body.rows
        delegate: ColumnLayout {
            id: inputRow
            required property var modelData
            objectName: 'objectInput:' + modelData.key
            Layout.fillWidth: true
            spacing: 2
            Accessible.role: Accessible.StaticText
            Accessible.name: modelData.label + ': ' + modelData.value + (modelData.condition ? ', ' + modelData.condition : '')
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                HudLabel { Layout.fillWidth: true; text: inputRow.modelData.label + (inputRow.modelData.primary ? '  · primary' : ''); font.pixelSize: 14 }
                HudLabel {
                    Layout.maximumWidth: body.width * .4
                    text: inputRow.modelData.value
                    font.family: Tokens.mono; font.pixelSize: 14
                    color: inputRow.modelData.level === 'ok' ? Tokens.text : inputRow.modelData.level === 'warning' ? Tokens.warning : Tokens.muted
                }
                HudLabel {
                    Layout.preferredWidth: 130
                    horizontalAlignment: Text.AlignRight
                    text: [inputRow.modelData.condition, inputRow.modelData.age].filter(v => v).join(' · ')
                    font.pixelSize: 12
                    color: inputRow.modelData.condition === 'fresh' ? Tokens.positive : inputRow.modelData.condition === 'error' ? Tokens.warning : Tokens.muted
                }
            }
            HudLabel {
                Layout.fillWidth: true
                text: [inputRow.modelData.key, inputRow.modelData.range, inputRow.modelData.raw ? 'raw ' + inputRow.modelData.raw : '',
                       inputRow.modelData.source && inputRow.modelData.source !== body.sourceId ? inputRow.modelData.source + ' · ' + inputRow.modelData.sourceKey : ''].filter(v => v).join('  ·  ')
                font.family: Tokens.mono; font.pixelSize: 11; color: Tokens.muted
            }
            HudLabel {
                Layout.fillWidth: true
                visible: text !== ''
                text: inputRow.modelData.explain
                font.pixelSize: 12; color: Tokens.muted; wrapMode: Text.Wrap
            }
        }
    }

    // ---- Source helper ----
    Heading { text: 'SOURCE HELPER' }
    HudLabel {
        objectName: 'objectDataHelper'
        Layout.fillWidth: true
        text: body.helper.text
        color: body.helper.state === 'ok' ? Tokens.muted : body.helper.state === 'unknown' ? Tokens.muted : Tokens.warning
        font.pixelSize: 13; wrapMode: Text.Wrap
    }
    HudLabel {
        objectName: 'objectDataLastRun'
        Layout.fillWidth: true
        visible: text !== ''
        text: body.lastRun ? body.lastRun.line
            : body.helper.state === 'ok' || body.helper.state === 'disconnected' ? 'sources.json has no entry ' + body.instanceId + ' yet.' : ''
        color: body.lastRun && body.lastRun.level === 'warning' ? Tokens.warning : Tokens.muted
        font.pixelSize: 12; wrapMode: Text.Wrap
    }
    HudLabel {
        Layout.fillWidth: true
        visible: !!body.lastRun && body.lastRun.values !== ''
        text: body.lastRun ? body.lastRun.values : ''
        font.family: Tokens.mono; font.pixelSize: 12; wrapMode: Text.Wrap
    }
    HudLabel {
        Layout.fillWidth: true
        visible: !!body.lastRun && body.lastRun.error !== ''
        text: body.lastRun ? body.lastRun.error : ''
        color: Tokens.warning; font.pixelSize: 12; wrapMode: Text.Wrap
    }

    // ---- Editor: the sources.json entry with this instance's id ----
    ColumnLayout {
        Layout.fillWidth: true
        visible: !!body.source && body.source.publishable
        spacing: 8

        Heading { text: 'COMMAND  ·  SOURCES.JSON ENTRY ' + body.instanceId.toUpperCase() }
        HudLabel {
            Layout.fillWidth: true
            visible: text !== ''
            text: body.draft.note || (body.loaded ? (body.loaded.entry ? '' : 'No entry yet: Save adds one to ') + (body.loaded.entry ? '' : body.loaded.path) : '')
            color: body.draft.note ? Tokens.warning : Tokens.muted; font.pixelSize: 12; wrapMode: Text.WrapAnywhere
        }
        Caption { text: 'Command (a script or program; it prints one JSON object)' }
        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Field {
                id: scriptField
                objectName: 'source-command'
                Layout.fillWidth: true
                enabled: body.editable
                placeholderText: '/home/you/bin/ram-gauge'
                Accessible.name: 'Command path'
                onTextEdited: body.dirty = true
                onAccepted: body.save()
            }
            ActionButton {
                objectName: 'source-choose'
                text: 'Choose…'
                enabled: body.editable
                onClicked: {
                    browser.visible = true;
                    var path = scriptField.text.trim();
                    browser.open(path.charAt(0) === '/' ? path : '');
                }
            }
        }
        SourceFileBrowser {
            id: browser
            Layout.fillWidth: true
            visible: false
            onPicked: (path) => { scriptField.text = path; body.dirty = true; visible = false; scriptField.forceActiveFocus(); }
            onClosed: { visible = false; chooseFocus.restart(); }
            Timer { id: chooseFocus; interval: 0; onTriggered: scriptField.forceActiveFocus() }
        }
        Caption { text: 'Arguments (optional, one per line)' }
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 76
            radius: Tokens.radius; color: argsField.enabled ? Tokens.panel : 'transparent'
            border.width: argsField.activeFocus ? 2 : 1; border.color: argsField.activeFocus ? Tokens.gold : Tokens.line
            ScrollView {
                anchors.fill: parent; anchors.margins: 2
                clip: true
                TextArea {
                    id: argsField
                    objectName: 'source-args'
                    enabled: body.editable
                    color: Tokens.text
                    placeholderText: '--json'
                    placeholderTextColor: Tokens.muted
                    selectionColor: Tokens.accent
                    selectedTextColor: Tokens.ink
                    font.family: Tokens.mono; font.pixelSize: 13
                    wrapMode: TextEdit.NoWrap
                    background: null
                    Accessible.name: 'Arguments, one per line'
                    onTextChanged: { if (activeFocus) body.dirty = true; }
                    KeyNavigation.priority: KeyNavigation.BeforeItem
                    KeyNavigation.tab: intervalField
                }
            }
        }
        Caption { text: 'Every' }
        RowLayout {
            Layout.fillWidth: true
            spacing: 6
            ActionButton { objectName: 'source-interval-down'; implicitWidth: 42; text: '−'; enabled: body.editable; Accessible.name: 'Shorter interval'; onClicked: body.stepInterval(-1) }
            Field {
                id: intervalField
                objectName: 'source-interval'
                Layout.preferredWidth: 110
                enabled: body.editable
                horizontalAlignment: TextInput.AlignHCenter
                inputMethodHints: Qt.ImhDigitsOnly
                validator: IntValidator { bottom: 0; top: 999999 }
                Accessible.name: 'Interval in seconds, ' + body.bounds.min + ' to ' + body.bounds.max
                onTextEdited: body.dirty = true
                onEditingFinished: body.settleInterval()
                onAccepted: body.save()
                Keys.onUpPressed: body.stepInterval(1)
                Keys.onDownPressed: body.stepInterval(-1)
                Keys.onPressed: (event) => {
                    if (event.key === Qt.Key_PageUp) { body.stepInterval(60); event.accepted = true; }
                    else if (event.key === Qt.Key_PageDown) { body.stepInterval(-60); event.accepted = true; }
                }
            }
            ActionButton { objectName: 'source-interval-up'; implicitWidth: 42; text: '+'; enabled: body.editable; Accessible.name: 'Longer interval'; onClicked: body.stepInterval(1) }
            HudLabel {
                Layout.fillWidth: true
                text: 's  ·  ' + Sources.intervalText(Number(intervalField.text)) + '  ·  ' + body.bounds.min + '–' + body.bounds.max + ' s'
                color: Tokens.muted; font.pixelSize: 12
            }
        }
        HudLabel {
            objectName: 'sourceRuns'
            Layout.fillWidth: true
            text: Sources.runsText(body.argv) || 'Runs: (choose a command)'
            font.family: Tokens.mono; font.pixelSize: 12
            color: body.argv.length ? Tokens.text : Tokens.muted
            wrapMode: Text.WrapAnywhere; elide: Text.ElideNone
        }
        HudLabel {
            Layout.fillWidth: true
            visible: body.editable && body.problem !== '' && body.dirty
            text: body.problem
            color: Tokens.warning; font.pixelSize: 12; wrapMode: Text.Wrap
        }
        Flow {
            Layout.fillWidth: true
            spacing: 8
            ActionButton {
                objectName: 'source-test'
                text: body.busy === 'test' ? 'Testing…' : 'Test'
                enabled: body.editable && !body.problem && !body.busy && body.helper.canTest
                onClicked: body.runTest()
            }
            ActionButton {
                objectName: 'source-save'
                primary: true
                text: body.busy === 'save' ? 'Saving…' : 'Save'
                enabled: body.editable && !body.problem && !body.busy
                onClicked: body.save()
            }
            ActionButton {
                objectName: 'source-remove'
                text: body.confirm === 'remove' ? 'Remove the entry? Press again' : 'Remove'
                enabled: body.editable && !body.busy && !!body.loaded && !!body.loaded.entry
                onClicked: body.confirmed('remove', () => body.request('remove', 'sources.remove', {id: body.instanceId}))
            }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            CheckBox {
                id: resetAverage
                objectName: 'source-reset-average'
                text: 'Reset average'
                Accessible.name: 'Reset the running average on restart'
                indicator: Rectangle {
                    implicitWidth: 18; implicitHeight: 18
                    x: resetAverage.leftPadding; y: (resetAverage.height - height) / 2
                    radius: 2; color: resetAverage.checked ? Tokens.accent : 'transparent'
                    border.width: resetAverage.activeFocus ? 2 : 1
                    border.color: resetAverage.activeFocus ? Tokens.gold : Tokens.line
                    HudLabel { anchors.centerIn: parent; rightPadding: 0; visible: resetAverage.checked; text: '✓'; color: Tokens.ink; font.pixelSize: 13 }
                }
                contentItem: HudLabel {
                    leftPadding: resetAverage.indicator.width + 8
                    text: resetAverage.text; font.pixelSize: 13; verticalAlignment: Text.AlignVCenter
                }
            }
            ActionButton {
                objectName: 'source-restart'
                text: body.busy === 'restart' ? 'Restarting…' : 'Restart'
                enabled: !body.busy && body.helper.canRestart && !!body.ownSource
                onClicked: body.request('restart', 'sources.restart', {id: body.instanceId, resetAverage: resetAverage.checked})
            }
            ActionButton {
                objectName: 'source-restart-helper'
                text: body.confirm === 'restartAll' ? 'Restart every source? Press again' : body.busy === 'restartAll' ? 'Restarting…' : 'Restart helper'
                enabled: !body.busy && body.helper.canRestart
                onClicked: body.confirmed('restartAll', () => body.request('restartAll', 'sources.restartAll', {}))
            }
            Item { Layout.fillWidth: true }
        }
        HudLabel {
            objectName: 'sourceFeedback'
            Layout.fillWidth: true
            visible: text !== ''
            text: body.feedback ? body.feedback.text : ''
            color: body.feedback && body.feedback.level === 'warning' ? Tokens.warning : Tokens.positive
            font.pixelSize: 13; wrapMode: Text.WrapAnywhere
        }
        HudLabel {
            Layout.fillWidth: true
            text: 'Test runs the command once through the source helper and publishes nothing. Save writes sources.json; the helper picks it up at once. Restart helper stops every source, re-reads the file and reconnects.'
            color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap
        }
    }

    // ---- Test output ----
    ColumnLayout {
        objectName: 'sourceTest'
        Layout.fillWidth: true
        visible: !!body.test && body.test.ok
        spacing: 6
        Heading { text: 'TEST' }
        HudLabel {
            objectName: 'sourceTestSummary'
            Layout.fillWidth: true
            text: body.validation ? body.validation.summary : ''
            color: body.validation && body.validation.ok ? Tokens.positive : Tokens.warning
            font.pixelSize: 13; wrapMode: Text.Wrap
        }
        Repeater {
            model: body.validation ? body.validation.rows : []
            delegate: RowLayout {
                id: check
                required property var modelData
                objectName: 'sourceCheck:' + modelData.key
                Layout.fillWidth: true
                spacing: 10
                HudLabel { text: check.modelData.level === 'ok' ? '✓' : check.modelData.level === 'warning' ? '!' : '✕'; Layout.preferredWidth: 14
                           color: check.modelData.level === 'ok' ? Tokens.positive : Tokens.warning; font.pixelSize: 13 }
                HudLabel { Layout.preferredWidth: 160; text: check.modelData.label; font.pixelSize: 13 }
                HudLabel { Layout.preferredWidth: 160; text: check.modelData.value; font.family: Tokens.mono; font.pixelSize: 13 }
                HudLabel { Layout.fillWidth: true; text: check.modelData.problems.join('; '); color: Tokens.warning; font.pixelSize: 12; wrapMode: Text.Wrap }
            }
        }
        HudLabel {
            Layout.fillWidth: true
            visible: !!body.validation && body.validation.unknown.length > 0
            text: body.validation ? 'No input reads: ' + body.validation.unknown.join(', ') : ''
            color: Tokens.warning; font.family: Tokens.mono; font.pixelSize: 12; wrapMode: Text.Wrap
        }
        HudLabel {
            Layout.fillWidth: true
            visible: !!body.test && !!body.test.result && (body.test.result.error || body.test.result.exitCode !== 0)
            text: body.test && body.test.result ? [body.test.result.error || '', typeof body.test.result.exitCode === 'number' ? 'exit code ' + body.test.result.exitCode : '',
                                                   typeof body.test.result.durationMs === 'number' ? body.test.result.durationMs + ' ms' : ''].filter(v => v).join(' · ') : ''
            color: Tokens.warning; font.pixelSize: 12; wrapMode: Text.Wrap
        }
        Caption { text: 'Printed' }
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(220, printed.implicitHeight + 16)
            radius: Tokens.radius; color: Tokens.panel; border.color: Tokens.line
            ScrollView {
                anchors.fill: parent; anchors.margins: 8
                clip: true
                HudLabel {
                    id: printed
                    objectName: 'sourceTestPrinted'
                    text: Sources.printedText(body.test ? body.test.result : null) || '(nothing on stdout)'
                    font.family: Tokens.mono; font.pixelSize: 12; elide: Text.ElideNone
                }
            }
        }
        HudLabel {
            Layout.fillWidth: true
            visible: !!body.test && !!body.test.result && !!body.test.result.stderr
            text: body.test && body.test.result && body.test.result.stderr ? 'stderr: ' + String(body.test.result.stderr).replace(/\s+$/, '') : ''
            color: Tokens.muted; font.family: Tokens.mono; font.pixelSize: 11; wrapMode: Text.WrapAnywhere
            maximumLineCount: 8
        }
    }
}
