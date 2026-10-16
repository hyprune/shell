import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../DataSources.js" as DS

// Director > Objects > Data sources (data sources phase 2, RFC-0013 draft): every source in
// sources.json. Left, the list with each source's state from the source helper; right, the
// editor of the chosen one: HTTP (method, URL, headers with secrets by name, body) or command,
// the output, the interval, and the gauge map (value from a path scaled from min..max to
// 0-100, a level by thresholds or matched text, a display template, a label). Test runs the
// definition as written (the helper publishes nothing) and shows the raw response beside the
// mapped values and a gauge preview. Secrets the source names are listed with where the
// helper finds them; a missing one is stored in the secrets file (0600) or the keyring.
// The bridge (bridge/sources.py) writes sources.json and the secrets; the shell never runs
// a source.
RowLayout {
    id: page
    objectName: 'dataSources'
    spacing: 16

    property var list: null            // the last sources.list answer
    property string selected: ''       // the id being edited ('' with a new one: see fresh)
    property string fresh: ''          // a new source's kind until it is saved
    property string previous: ''       // the id the edited entry had when loaded
    property var headers: []           // [{name, text, secret, prefix}] of the editor
    property var test: null            // DS.testView of the last test
    property var secretsFound: ({})    // name -> origin (helper secrets op / last test)
    property var feedback: null        // {level, text}
    property string busy: ''
    property int listSeq: 0
    property int testSeq: 0
    property int actionSeq: 0
    property int secretsSeq: 0
    property bool dirty: false
    readonly property var rows: DS.rows(list)
    readonly property var row: rows.find(r => r.id === selected) || null
    readonly property var entry: list && list.entries ? list.entries.find(e => e && e.id === selected) || null : null
    property string kind: 'http'
    property string method: 'GET'
    property string output: 'json'
    property string reduce: ''
    property string levelMode: 'none'
    property string otherwise: 'ok'
    property bool local: false
    property bool enabledSource: true
    property bool below: false
    property bool ofRaw: false
    property var names: []             // secret names the editor refers to
    property string freshName: ''      // a new source's id as typed (its list row)

    function refresh() { listSeq = ShellState.sourcesRequest('sources.list', {}); }
    function askSecrets() { secretsSeq = ShellState.sourcesRequest('sources.secrets', {}); }
    function open(id) {
        selected = id; fresh = ''; previous = id; test = null; feedback = null;
        load(DS.draft(list && list.entries ? list.entries.find(e => e && e.id === id) : null));
    }
    // Behaviours' Data source… (ShellState.sourcesFocus): this entry, or a new command entry with
    // that id. The page keeps its last list between visits, so an id it lacks (an entry proposed
    // since) waits for a list asked for after the focus before a new entry is made.
    property int focusSeq: 0
    function focusSource(fresh) {
        var id = ShellState.sourcesFocus;
        if (!id) return;
        if (list && list.entries && list.entries.some(e => e && e.id === id)) { ShellState.sourcesFocus = ''; open(id); }
        else if (fresh && list && list.entries) { ShellState.sourcesFocus = ''; create('command'); idField.text = id; edited(); }
        else if (!focusSeq) { refresh(); focusSeq = listSeq; }
    }
    Connections { target: ShellState; function onSourcesFocusChanged() { page.focusSeq = 0; page.focusSource(false); } }
    function create(k) {
        var id = DS.freeId(list, k);
        selected = id; fresh = k; previous = ''; test = null; feedback = null;
        load(DS.draft(null, k, id));
        dirty = true;
    }
    function load(d) {
        idField.text = d.id; kind = d.kind; enabledSource = d.enabled;
        commandField.text = d.command; argsField.text = d.args;
        urlField.text = d.url; method = d.method; headers = d.headers.slice(); local = d.local; bodyField.text = d.body;
        output = d.output; intervalField.text = d.interval; timeoutField.text = d.timeout;
        valueField.text = d.valuePath; reduce = d.reduce; minField.text = d.min; maxField.text = d.max;
        levelMode = d.levelMode; warnField.text = d.warn; failField.text = d.fail; below = d.below; ofRaw = d.ofRaw;
        matchPathField.text = d.matchPath; matchField.text = d.match; otherwise = d.otherwise;
        displayField.text = d.display; labelField.text = d.labelPath || d.label;
        dirty = false;
        updateNames();
    }
    function collect() {
        var label = labelField.text.trim();
        var path = /^(\$|\{|\/)/.test(label);
        return {id: idField.text.trim(), kind: kind, enabled: enabledSource, command: commandField.text, args: argsField.text,
                url: urlField.text, method: method, headers: headers, local: local, body: bodyField.text, output: output,
                interval: intervalField.text, timeout: timeoutField.text, valuePath: valueField.text, reduce: reduce,
                min: minField.text, max: maxField.text, levelMode: levelMode, warn: warnField.text, fail: failField.text,
                below: below, ofRaw: ofRaw, matchPath: matchPathField.text, match: matchField.text, otherwise: otherwise,
                display: displayField.text, labelPath: path ? label : '', label: path ? '' : label};
    }
    function edited() { dirty = true; updateNames(); if (fresh) freshName = idField.text.trim(); }
    function updateNames() { names = DS.secretNames({url: urlField.text, body: bodyField.text, headers: headers}); }
    function built() { return DS.entryFrom(collect()); }
    function runTest() {
        var b = built();
        if (b.error) { feedback = {level: 'warning', text: b.error}; return; }
        testSeq = ShellState.sourcesRequest('sources.testSource', {source: DS.testSource(b.entry)});
        if (testSeq) { busy = 'test'; feedback = null; busyTimer.restart(); }
    }
    function save() {
        var b = built();
        if (b.error) { feedback = {level: 'warning', text: b.error}; return; }
        actionSeq = ShellState.sourcesRequest('sources.put', {entry: b.entry, previous: previous || null});
        if (actionSeq) { busy = 'save'; feedback = null; busyTimer.restart(); }
    }
    function remove() {
        if (fresh) { selected = ''; fresh = ''; return; }
        actionSeq = ShellState.sourcesRequest('sources.remove', {id: previous});
        if (actionSeq) { busy = 'remove'; busyTimer.restart(); }
    }
    function storeSecret(name, value, store) {
        actionSeq = ShellState.sourcesRequest('sources.secretSet', {name: name, value: value, store: store});
        if (actionSeq) { busy = 'secret'; busyTimer.restart(); }
    }
    function setHeader(index, key, value) { headers[index][key] = value; edited(); }

    onVisibleChanged: { ShellState.sourcesWanted = visible; if (visible) { refresh(); askSecrets(); } }
    // Inside the editor, the Objects page's one-letter shortcuts (V, L, H, R, Delete) stay out.
    Keys.onPressed: (event) => {
        if (event.modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)) return;
        if ([Qt.Key_L, Qt.Key_H, Qt.Key_R, Qt.Key_V, Qt.Key_Delete].indexOf(event.key) >= 0) event.accepted = true;
    }
    Component.onDestruction: ShellState.sourcesWanted = false
    Timer { id: busyTimer; interval: 80000; onTriggered: page.busy = '' }
    Timer { interval: 3000; repeat: true; running: page.visible && !page.busy; onTriggered: page.refresh() }
    Connections {
        target: ShellState
        function onSourcesReply(reply) {
            if (reply.op === 'list' && reply.seq === page.listSeq) {
                page.list = reply.ok ? reply : page.list;
                if (reply.ok && ShellState.sourcesFocus) page.focusSource(!!page.focusSeq && reply.seq >= page.focusSeq);
                if (!reply.ok) page.feedback = {level: 'warning', text: reply.error};
                else if (!page.selected && page.rows.length) page.open(page.rows[0].id);
            } else if (reply.op === 'secrets' && reply.seq === page.secretsSeq && reply.ok) {
                page.secretsFound = reply.secrets.names || {};
            } else if (reply.op === 'testSource' && reply.seq === page.testSeq) {
                page.busy = '';
                if (!reply.ok) page.feedback = {level: 'warning', text: reply.error};
                else {
                    page.test = DS.testView(reply.result);
                    if (reply.result && reply.result.secrets) page.secretsFound = Object.assign({}, page.secretsFound, reply.result.secrets);
                }
            } else if (reply.seq === page.actionSeq && ['put', 'remove', 'secretSet'].indexOf(reply.op) >= 0) {
                page.busy = '';
                if (!reply.ok) { page.feedback = {level: 'warning', text: reply.error}; return; }
                if (reply.op === 'put') {
                    page.feedback = {level: 'ok', text: 'Saved ' + reply.entry.id + ' to ' + reply.path +
                                     (reply.reload && !reply.reload.ok ? ' (the helper did not reload: ' + reply.reload.error + ')' : '')};
                    page.selected = reply.entry.id; page.previous = reply.entry.id; page.fresh = ''; page.dirty = false;
                } else if (reply.op === 'remove') {
                    page.feedback = {level: 'ok', text: 'Removed ' + page.previous}; page.selected = ''; page.previous = '';
                } else {
                    page.feedback = {level: 'ok', text: 'Stored secret ' + reply.name + ' in the ' + (reply.store === 'keyring' ? 'keyring' : 'secrets file')};
                    page.askSecrets();
                }
                page.refresh();
            }
        }
    }

    component Field: TextField {
        implicitHeight: 36
        color: enabled ? Tokens.text : Tokens.muted
        placeholderTextColor: Tokens.muted
        selectionColor: Tokens.accent; selectedTextColor: Tokens.ink
        font.family: Tokens.mono; font.pixelSize: 13
        leftPadding: 10; rightPadding: 10
        background: Rectangle { radius: Tokens.radius; color: parent.enabled ? Tokens.panel : 'transparent'; border.width: parent.activeFocus ? 2 : 1; border.color: parent.activeFocus ? Tokens.gold : Tokens.line }
    }
    component Check: CheckBox {
        id: box
        indicator: Rectangle {
            implicitWidth: 18; implicitHeight: 18
            x: box.leftPadding; y: (box.height - height) / 2
            radius: 2; color: box.checked ? Tokens.accent : 'transparent'
            border.width: box.activeFocus ? 2 : 1
            border.color: box.activeFocus ? Tokens.gold : Tokens.line
            HudLabel { anchors.centerIn: parent; rightPadding: 0; visible: box.checked; text: '✓'; color: Tokens.ink; font.pixelSize: 13 }
        }
        contentItem: HudLabel { leftPadding: box.indicator.width + 8; text: box.text; font.pixelSize: 13; verticalAlignment: Text.AlignVCenter }
    }
    component Heading: HudLabel { Layout.fillWidth: true; Layout.topMargin: 6; color: Tokens.gold; font.pixelSize: 10; font.letterSpacing: 1.5 }
    component Caption: HudLabel { Layout.fillWidth: true; font.pixelSize: 11; color: Tokens.muted; wrapMode: Text.Wrap }
    component Area: Rectangle {
        id: areaRoot
        property alias text: area.text
        property string placeholder: ''
        signal edited()
        Layout.fillWidth: true
        radius: Tokens.radius; color: Tokens.panel
        border.width: area.activeFocus ? 2 : 1; border.color: area.activeFocus ? Tokens.gold : Tokens.line
        ScrollView {
            anchors.fill: parent; anchors.margins: 2; clip: true
            TextArea {
                id: area
                color: Tokens.text; placeholderText: areaRoot.placeholder; placeholderTextColor: Tokens.muted
                font.family: Tokens.mono; font.pixelSize: 13; wrapMode: TextEdit.WrapAnywhere
                onTextChanged: if (activeFocus) areaRoot.edited()
                background: null
            }
        }
    }

    // ---- The list ----
    ColumnLayout {
        Layout.preferredWidth: 330; Layout.minimumWidth: 330; Layout.maximumWidth: 330
        Layout.fillWidth: false
        Layout.fillHeight: true
        spacing: 8
        RowLayout {
            spacing: 8
            ActionButton { objectName: 'sources-new-http'; text: 'New HTTP'; onClicked: page.create('http') }
            ActionButton { objectName: 'sources-new-command'; text: 'New command'; onClicked: page.create('command') }
        }
        HudLabel {
            Layout.fillWidth: true
            text: !page.list ? 'Reading sources.json…' : !page.list.exists ? 'No sources.json yet: New adds one at ' + page.list.path
                : page.rows.length + (page.rows.length === 1 ? ' source' : ' sources') + ' · ' + page.list.path
            font.pixelSize: 11; color: Tokens.muted; wrapMode: Text.WrapAnywhere
        }
        ListView {
            id: listView
            objectName: 'sources-list'
            Layout.fillWidth: true; Layout.fillHeight: true
            clip: true; spacing: 4
            model: page.rows.concat(page.fresh && !page.rows.some(r => r.id === page.selected) ? [{id: page.selected, name: page.freshName, kindLabel: page.fresh === 'http' ? 'HTTP' : 'Command', target: 'new, not saved', state: 'new', editable: true}] : [])
            delegate: Rectangle {
                id: item
                required property var modelData
                objectName: 'source-row:' + modelData.id
                width: listView.width; height: 56; radius: 3
                color: modelData.id === page.selected ? Qt.rgba(Tokens.accent.r, Tokens.accent.g, Tokens.accent.b, .16) : Tokens.panel
                border.width: modelData.id === page.selected ? 1 : 0; border.color: Tokens.accent
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 8; spacing: 2
                    RowLayout {
                        HudLabel { Layout.fillWidth: true; text: item.modelData.name || item.modelData.id; font.pixelSize: 14; elide: Text.ElideRight }
                        HudLabel {
                            text: item.modelData.kindLabel + ' · ' + item.modelData.state
                            font.pixelSize: 11
                            color: item.modelData.state === 'ok' ? Tokens.positive : item.modelData.state === 'error' ? Tokens.warning : Tokens.muted
                        }
                    }
                    HudLabel { Layout.fillWidth: true; text: item.modelData.error || item.modelData.target; font.family: Tokens.mono; font.pixelSize: 11; color: item.modelData.error ? Tokens.warning : Tokens.muted; elide: Text.ElideRight }
                }
                MouseArea { anchors.fill: parent; enabled: item.modelData.editable; onClicked: if (item.modelData.id !== page.selected) page.open(item.modelData.id) }
            }
        }
    }

    // ---- The editor ----
    ScrollView {
        id: editorScroll
        Layout.fillWidth: true; Layout.fillHeight: true
        Layout.preferredWidth: 860
        Layout.maximumWidth: 900
        clip: true
        contentWidth: availableWidth
        visible: page.selected !== ''
        ColumnLayout {
            width: editorScroll.availableWidth - 12
            spacing: 6

            Heading { text: 'SOURCE' }
            // RFC-0016: an assistant's proposed command, shown with the exact argument vector.
            RowLayout {
                objectName: 'source-proposal'
                Layout.fillWidth: true; spacing: 10
                visible: !!page.entry && page.entry.confirm === 'pending'
                HudLabel { Layout.fillWidth: true; text: DS.proposalText(page.entry); wrapMode: Text.Wrap; font.pixelSize: 12; color: Tokens.gold }
                ActionButton {
                    objectName: 'source-allow'
                    text: 'Allow'
                    enabled: !page.busy
                    onClicked: { page.actionSeq = ShellState.sourcesRequest('sources.put', {entry: DS.allowEntry(page.entry), previous: page.previous || null}); if (page.actionSeq) { page.busy = 'save'; busyTimer.restart(); } }
                }
            }
            RowLayout {
                Layout.fillWidth: true; spacing: 10
                HudLabel { text: 'Id'; Layout.preferredWidth: 90 }
                Field { id: idField; objectName: 'source-id'; Layout.preferredWidth: 220; onTextEdited: page.edited() }
                Segmented { objectName: 'source-kind'; Layout.preferredWidth: 220; model: DS.KINDS; current: page.kind; onPicked: (id) => { page.kind = id; page.edited(); } }
                Check { objectName: 'source-enabled'; text: 'Enabled'; checked: page.enabledSource; onToggled: { page.enabledSource = checked; page.edited(); } }
                Item { Layout.fillWidth: true }
            }
            Caption { text: 'Publishes as com.hyprune.sources.' + idField.text + ' (bind a gauge or machine to it in Placed > Data source).' }

            // HTTP
            ColumnLayout {
                Layout.fillWidth: true; spacing: 6
                visible: page.kind === 'http'
                RowLayout {
                    Layout.fillWidth: true; spacing: 10
                    Choice { objectName: 'source-method'; implicitWidth: 110; model: DS.METHODS; currentIndex: DS.METHODS.indexOf(page.method); onActivated: (i) => { page.method = DS.METHODS[i]; page.edited(); } }
                    Field { id: urlField; objectName: 'source-url'; Layout.fillWidth: true; placeholderText: 'https://api.example.com/status?key={secret:api-key}'; onTextEdited: page.edited() }
                }
                Check { objectName: 'source-local'; text: 'Local network (plain http:// and private addresses)'; checked: page.local; onToggled: { page.local = checked; page.edited(); } }
                Caption { text: 'Headers: a text value, or a secret by name (the value never goes into sources.json). {secret:name} works in the URL, header text and body too.' }
                Repeater {
                    model: page.headers
                    delegate: RowLayout {
                        id: headerRow
                        required property var modelData
                        required property int index
                        Layout.fillWidth: true; spacing: 8
                        Field { objectName: 'header-name:' + headerRow.index; Layout.preferredWidth: 170; placeholderText: 'Authorization'; text: headerRow.modelData.name; onTextEdited: page.setHeader(headerRow.index, 'name', text) }
                        Field { objectName: 'header-prefix:' + headerRow.index; Layout.preferredWidth: 90; placeholderText: 'Bearer '; text: headerRow.modelData.prefix; visible: headerRow.modelData.secret !== '' || headerRow.modelData.text === ''; onTextEdited: page.setHeader(headerRow.index, 'prefix', text) }
                        Field { objectName: 'header-secret:' + headerRow.index; Layout.preferredWidth: 150; placeholderText: 'secret name'; text: headerRow.modelData.secret; onTextEdited: page.setHeader(headerRow.index, 'secret', text) }
                        Field { objectName: 'header-text:' + headerRow.index; Layout.fillWidth: true; placeholderText: 'or a text value'; text: headerRow.modelData.text; enabled: headerRow.modelData.secret === ''; onTextEdited: page.setHeader(headerRow.index, 'text', text) }
                        ActionButton { text: '−'; implicitWidth: 42; onClicked: { var h = page.headers.slice(); h.splice(headerRow.index, 1); page.headers = h; page.edited(); } }
                    }
                }
                ActionButton { objectName: 'source-add-header'; text: 'Add header'; onClicked: { page.headers = page.headers.concat([{name: '', text: '', secret: '', prefix: ''}]); page.edited(); } }
                Caption { visible: page.method !== 'GET'; text: 'Body: JSON (starting with { or [) or text.' }
                Area { id: bodyField; objectName: 'source-body'; visible: page.method !== 'GET'; Layout.preferredHeight: 90; placeholder: '{"query": "status"}'; onEdited: page.edited() }
            }
            // Command
            ColumnLayout {
                Layout.fillWidth: true; spacing: 6
                visible: page.kind === 'command'
                Caption { text: 'Command (run without a shell; it prints JSON, a number, text or lines)' }
                Field { id: commandField; objectName: 'source-command'; Layout.fillWidth: true; placeholderText: 'hyprune-system-gauges'; onTextEdited: page.edited() }
                Caption { text: 'Arguments (one per line)' }
                Area { id: argsField; objectName: 'source-args'; Layout.preferredHeight: 64; placeholder: 'ram'; onEdited: page.edited() }
            }
            RowLayout {
                Layout.fillWidth: true; spacing: 10
                HudLabel { text: 'Output'; Layout.preferredWidth: 90 }
                Segmented { objectName: 'source-output'; Layout.preferredWidth: 380; model: DS.OUTPUTS; current: page.output; onPicked: (id) => { page.output = id; page.edited(); } }
                Item { Layout.fillWidth: true }
            }
            RowLayout {
                Layout.fillWidth: true; spacing: 10
                HudLabel { text: 'Every'; Layout.preferredWidth: 90 }
                Field { id: intervalField; objectName: 'source-interval'; Layout.preferredWidth: 90; placeholderText: '60'; onTextEdited: page.edited() }
                HudLabel { text: 's   Timeout'; color: Tokens.muted }
                Field { id: timeoutField; objectName: 'source-timeout'; Layout.preferredWidth: 90; placeholderText: '10'; onTextEdited: page.edited() }
                HudLabel { text: 's'; color: Tokens.muted }
                Item { Layout.fillWidth: true }
            }

            Heading { text: 'GAUGE MAP' }
            Caption { text: 'Paths: $.a.b, $.items[0], $.items[*].lag, $..name, $.jobs[?(@.status == \'queued\')]; {value} for a number, text or line-count output.' }
            RowLayout {
                Layout.fillWidth: true; spacing: 8
                HudLabel { text: 'Value'; Layout.preferredWidth: 90 }
                Field { id: valueField; objectName: 'map-value'; Layout.fillWidth: true; placeholderText: '$.memory.used'; onTextEdited: page.edited() }
                Choice { objectName: 'map-reduce'; implicitWidth: 150; model: DS.REDUCES.map(r => r.label); currentIndex: Math.max(0, DS.REDUCES.findIndex(r => r.id === page.reduce)); onActivated: (i) => { page.reduce = DS.REDUCES[i].id; page.edited(); } }
            }
            RowLayout {
                Layout.fillWidth: true; spacing: 8
                HudLabel { text: 'Scale'; Layout.preferredWidth: 90 }
                Field { id: minField; objectName: 'map-min'; Layout.preferredWidth: 100; placeholderText: '0'; onTextEdited: page.edited() }
                HudLabel { text: '…'; color: Tokens.muted }
                Field { id: maxField; objectName: 'map-max'; Layout.preferredWidth: 100; placeholderText: '100'; onTextEdited: page.edited() }
                HudLabel { text: '→ 0–100'; color: Tokens.muted }
                Item { Layout.fillWidth: true }
            }
            RowLayout {
                Layout.fillWidth: true; spacing: 8
                HudLabel { text: 'Level'; Layout.preferredWidth: 90 }
                Segmented { objectName: 'map-level'; Layout.preferredWidth: 330; model: DS.LEVEL_MODES; current: page.levelMode; onPicked: (id) => { page.levelMode = id; page.edited(); } }
                Item { Layout.fillWidth: true }
            }
            RowLayout {
                Layout.fillWidth: true; spacing: 8
                visible: page.levelMode === 'thresholds'
                Item { Layout.preferredWidth: 90 }
                HudLabel { text: 'warn at'; color: Tokens.muted }
                Field { id: warnField; objectName: 'map-warn'; Layout.preferredWidth: 80; placeholderText: '70'; onTextEdited: page.edited() }
                HudLabel { text: 'fail at'; color: Tokens.muted }
                Field { id: failField; objectName: 'map-fail'; Layout.preferredWidth: 80; placeholderText: '90'; onTextEdited: page.edited() }
                Check { text: 'Low is bad'; checked: page.below; onToggled: { page.below = checked; page.edited(); } }
                Check { text: 'On the raw number'; checked: page.ofRaw; onToggled: { page.ofRaw = checked; page.edited(); } }
                Item { Layout.fillWidth: true }
            }
            RowLayout {
                Layout.fillWidth: true; spacing: 8
                visible: page.levelMode === 'match'
                Item { Layout.preferredWidth: 90 }
                Field { id: matchPathField; objectName: 'map-match-path'; Layout.preferredWidth: 220; placeholderText: '$.status'; onTextEdited: page.edited() }
                Field { id: matchField; objectName: 'map-match'; Layout.fillWidth: true; placeholderText: 'degraded=warn, down=fail'; onTextEdited: page.edited() }
                Choice { implicitWidth: 120; model: ['otherwise ok', 'otherwise warn', 'otherwise fail']; currentIndex: ['ok', 'warn', 'fail'].indexOf(page.otherwise); onActivated: (i) => { page.otherwise = ['ok', 'warn', 'fail'][i]; page.edited(); } }
            }
            RowLayout {
                Layout.fillWidth: true; spacing: 8
                HudLabel { text: 'Display'; Layout.preferredWidth: 90 }
                Field { id: displayField; objectName: 'map-display'; Layout.fillWidth: true; placeholderText: '{raw:.1f} of {$.memory.total} GB'; onTextEdited: page.edited() }
            }
            RowLayout {
                Layout.fillWidth: true; spacing: 8
                HudLabel { text: 'Label'; Layout.preferredWidth: 90 }
                Field { id: labelField; objectName: 'map-label'; Layout.fillWidth: true; placeholderText: 'RAM, or $.host for a path'; onTextEdited: page.edited() }
            }

            Heading { text: 'SECRETS'; visible: page.names.length > 0 }
            Repeater {
                model: DS.secretRows(page.names, page.secretsFound)
                delegate: RowLayout {
                    id: secretRow
                    required property var modelData
                    objectName: 'secret:' + modelData.name
                    Layout.fillWidth: true; spacing: 8
                    HudLabel { text: secretRow.modelData.name; Layout.preferredWidth: 150; font.family: Tokens.mono; font.pixelSize: 13 }
                    HudLabel { text: secretRow.modelData.text; Layout.preferredWidth: 190; font.pixelSize: 12; color: secretRow.modelData.origin ? Tokens.positive : secretRow.modelData.known ? Tokens.warning : Tokens.muted }
                    Field { id: secretValue; objectName: 'secret-value:' + secretRow.modelData.name; Layout.fillWidth: true; echoMode: TextInput.Password; placeholderText: secretRow.modelData.origin ? 'replace it' : 'paste the value'; Accessible.name: 'Value of secret ' + secretRow.modelData.name }
                    ActionButton { objectName: 'secret-file:' + secretRow.modelData.name; text: 'Store in file'; enabled: secretValue.text !== '' && !page.busy; onClicked: { page.storeSecret(secretRow.modelData.name, secretValue.text, 'file'); secretValue.text = ''; } }
                    ActionButton { objectName: 'secret-keyring:' + secretRow.modelData.name; text: 'Keyring'; enabled: secretValue.text !== '' && !page.busy; onClicked: { page.storeSecret(secretRow.modelData.name, secretValue.text, 'keyring'); secretValue.text = ''; } }
                }
            }

            RowLayout {
                Layout.fillWidth: true; Layout.topMargin: 8; spacing: 8
                ActionButton { objectName: 'source-test'; text: page.busy === 'test' ? 'Testing…' : 'Test'; primary: true; enabled: !page.busy; onClicked: page.runTest() }
                ActionButton { objectName: 'source-save'; text: page.busy === 'save' ? 'Saving…' : 'Save'; enabled: !page.busy && page.dirty; onClicked: page.save() }
                ActionButton { objectName: 'source-remove'; text: page.fresh ? 'Discard' : 'Remove'; enabled: !page.busy; onClicked: page.remove() }
                ActionButton { objectName: 'source-restart'; text: 'Run now'; enabled: !page.busy && !page.fresh && !page.dirty; onClicked: { page.actionSeq = ShellState.sourcesRequest('sources.restart', {id: page.previous}); } }
                Item { Layout.fillWidth: true }
            }
            HudLabel {
                objectName: 'sources-feedback'
                Layout.fillWidth: true
                visible: !!page.feedback
                text: page.feedback ? page.feedback.text : ''
                color: page.feedback && page.feedback.level === 'warning' ? Tokens.warning : Tokens.muted
                font.pixelSize: 12; wrapMode: Text.Wrap
            }
        }
    }

    // ---- Test result: the raw response beside the mapped values ----
    ScrollView {
        id: testScroll
        Layout.fillWidth: true; Layout.fillHeight: true
        Layout.preferredWidth: 520
        Layout.minimumWidth: 360
        clip: true
        contentWidth: availableWidth
        visible: page.selected !== '' && !!page.test
        ColumnLayout {
            width: testScroll.availableWidth - 8
            spacing: 6
            Heading { text: 'TEST'; visible: !!page.test }
            HudLabel {
                objectName: 'test-line'
                Layout.fillWidth: true; visible: !!page.test
                text: page.test ? page.test.line + (page.test.error ? '   ·   ' + page.test.error : '') : ''
                color: page.test && !page.test.ok ? Tokens.warning : Tokens.muted
                font.pixelSize: 12; wrapMode: Text.Wrap
            }
            ColumnLayout {
                Layout.fillWidth: true; spacing: 14
                visible: !!page.test
                ColumnLayout {
                    Layout.fillWidth: true; Layout.alignment: Qt.AlignTop
                    Caption { text: 'Raw response' + (page.test && page.test.truncated ? ' (first 4 KiB)' : '') }
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 220
                        radius: Tokens.radius; color: Tokens.panel; border.width: 1; border.color: Tokens.line
                        ScrollView {
                            anchors.fill: parent; anchors.margins: 6; clip: true
                            TextArea {
                                objectName: 'test-raw'
                                readOnly: true; selectByMouse: true
                                text: page.test ? page.test.raw : ''
                                color: Tokens.text; font.family: Tokens.mono; font.pixelSize: 12; wrapMode: TextEdit.WrapAnywhere
                                background: null
                            }
                        }
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true; Layout.alignment: Qt.AlignTop
                    Caption { text: 'Mapped (what publishes)' }
                    Repeater {
                        model: page.test ? page.test.rows : []
                        delegate: RowLayout {
                            id: mappedRow
                            required property var modelData
                            objectName: 'mapped:' + modelData.key
                            Layout.fillWidth: true
                            HudLabel { text: mappedRow.modelData.key; Layout.preferredWidth: 110; font.family: Tokens.mono; font.pixelSize: 13; color: mappedRow.modelData.gauge ? Tokens.gold : Tokens.muted }
                            HudLabel { Layout.fillWidth: true; text: mappedRow.modelData.value; font.family: Tokens.mono; font.pixelSize: 13; elide: Text.ElideRight }
                        }
                    }
                    // A gauge preview: the value as a bar in the level's colour, display and label.
                    ColumnLayout {
                        Layout.fillWidth: true; Layout.topMargin: 8
                        visible: !!page.test && page.test.preview.value !== null
                        HudLabel { text: page.test ? page.test.preview.label : ''; visible: text !== ''; font.pixelSize: 12; color: Tokens.muted }
                        Rectangle {
                            objectName: 'test-gauge'
                            Layout.fillWidth: true; height: 14; radius: 7; color: Tokens.raised
                            Rectangle {
                                width: page.test && page.test.preview.value !== null ? parent.width * page.test.preview.value / 100 : 0
                                height: parent.height; radius: 7
                                color: !page.test ? Tokens.accent : page.test.preview.level === 'fail' ? '#d9573b' : page.test.preview.level === 'warn' ? '#e2a33a' : Tokens.positive
                            }
                        }
                        HudLabel { text: page.test ? page.test.preview.display : ''; font.family: Tokens.mono; font.pixelSize: 14 }
                    }
                }
            }
        }
    }
    HudLabel {
        Layout.fillWidth: true
        visible: page.selected === ''
        text: 'Choose a source, or New HTTP / New command.'
        color: Tokens.muted
    }
}
