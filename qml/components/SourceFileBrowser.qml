import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../Sources.js" as Sources

// The Data source editor's command chooser: a folder listing inside the Director (the
// Director holds exclusive input, so a separate dialog window would never get the keyboard).
// The bridge lists folders (sources.browse); executables are marked. Keys: Up / Down move,
// Enter opens a folder or picks a file, Backspace goes up, a letter jumps to the next name
// with it, Esc closes.
Rectangle {
    id: browser
    objectName: 'sourceBrowser'
    property var listing: null
    property int seq: 0
    property bool hidden: false
    property string error: ''
    readonly property var rows: Sources.browseRows(listing)
    signal picked(string path)
    signal closed()

    implicitHeight: 320
    radius: 3
    color: Tokens.panel
    border.color: list.activeFocus ? Tokens.gold : Tokens.line

    function open(path) {
        load(path || '');
        list.forceActiveFocus();
    }
    function load(path) {
        error = '';
        seq = ShellState.sourcesRequest('sources.browse', {path: path, hidden: hidden});
        if (!seq) error = 'The shell bridge is not connected.';
    }
    function activate(index) {
        var row = rows[index];
        if (!row) return;
        if (row.dir) load(row.path);
        else picked(row.path);
    }
    function jump(letter) {
        var n = rows.length;
        for (var step = 1; step <= n; step++) {
            var i = (list.currentIndex + step) % n;
            if (rows[i].name.toLowerCase().indexOf(letter) === 0) { list.currentIndex = i; return; }
        }
    }
    Connections {
        target: ShellState
        function onSourcesReply(reply) {
            if (reply.op !== 'browse' || reply.seq !== browser.seq) return;
            if (!reply.ok) { browser.error = reply.error || 'Could not list that folder.'; return; }
            var previous = browser.listing ? browser.listing.path : '';
            browser.listing = reply;
            // Going up lands on the folder we came from; a file path lands on that file.
            var name = reply.selected || (previous.indexOf(reply.path) === 0 && previous !== reply.path ? previous.slice(reply.path.length).replace(/^\//, '').split('/')[0] : '');
            var index = name ? browser.rows.findIndex(r => r.name === name) : -1;
            list.currentIndex = index >= 0 ? index : (browser.rows.length > 1 && browser.rows[0].parent ? 1 : 0);
            list.positionViewAtIndex(list.currentIndex, ListView.Contain);
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            HudLabel {
                objectName: 'sourceBrowserPath'
                Layout.fillWidth: true
                text: browser.listing ? browser.listing.path : 'Loading…'
                elide: Text.ElideLeft
                font.family: Tokens.mono; font.pixelSize: 12; color: Tokens.muted
            }
            ActionButton {
                objectName: 'source-browser-hidden'
                implicitWidth: 130
                text: browser.hidden ? 'Hide dot files' : 'Show dot files'
                onClicked: { browser.hidden = !browser.hidden; browser.load(browser.listing ? browser.listing.path : ''); }
            }
            ActionButton {
                objectName: 'source-browser-close'
                implicitWidth: 90
                text: 'Close'
                onClicked: browser.closed()
            }
        }

        ListView {
            id: list
            objectName: 'sourceBrowserList'
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            focus: true
            model: browser.rows
            boundsBehavior: Flickable.StopAtBounds
            highlightMoveDuration: 0
            ScrollBar.vertical: ScrollBar {}
            Accessible.role: Accessible.List
            Accessible.name: 'Choose a command in ' + (browser.listing ? browser.listing.path : '')
            Keys.onReturnPressed: browser.activate(currentIndex)
            Keys.onEnterPressed: browser.activate(currentIndex)
            Keys.onEscapePressed: browser.closed()
            Keys.onPressed: (event) => {
                if (event.key === Qt.Key_Backspace) {
                    if (browser.listing && browser.listing.parent) browser.load(browser.listing.parent);
                    event.accepted = true;
                } else if (!(event.modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)) && /^[a-z0-9._-]$/i.test(event.text)) {
                    // Letters jump by name; they never reach the Objects page's L/H/R/V shortcuts.
                    browser.jump(event.text.toLowerCase());
                    event.accepted = true;
                } else if (event.key === Qt.Key_Delete) event.accepted = true;
            }
            delegate: Item {
                id: row
                required property var modelData
                required property int index
                readonly property bool current: ListView.isCurrentItem
                width: list.width - 8
                height: 30
                Accessible.role: Accessible.ListItem
                Accessible.name: modelData.name + (modelData.dir ? ' folder' : modelData.executable ? ' executable' : '')
                Accessible.selected: current
                Rectangle {
                    anchors.fill: parent
                    radius: 2
                    color: row.current ? Tokens.raised : 'transparent'
                    border.width: row.current && list.activeFocus ? 1 : 0
                    border.color: Tokens.gold
                }
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8; anchors.rightMargin: 8
                    spacing: 8
                    HudLabel {
                        Layout.preferredWidth: 18
                        text: row.modelData.parent ? '↰' : row.modelData.dir ? '▸' : row.modelData.executable ? '⚙' : '·'
                        color: row.modelData.executable ? Tokens.gold : Tokens.muted
                        font.pixelSize: 13
                    }
                    HudLabel {
                        Layout.fillWidth: true
                        text: row.modelData.name + (row.modelData.dir && !row.modelData.parent ? '/' : '')
                        font.family: Tokens.mono; font.pixelSize: 13
                        color: row.modelData.dir || row.modelData.executable ? Tokens.text : Tokens.muted
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: { list.currentIndex = row.index; list.forceActiveFocus(); }
                    onDoubleClicked: browser.activate(row.index)
                }
            }
        }

        HudLabel {
            Layout.fillWidth: true
            text: browser.error ? browser.error
                : (browser.listing && browser.listing.truncated ? 'Showing the first ' + browser.listing.entries.length + ' names.  ' : '')
                  + 'Enter opens a folder or picks a file · Backspace goes up · Esc closes · ⚙ executable'
            color: browser.error ? Tokens.warning : Tokens.muted
            font.pixelSize: 12; wrapMode: Text.Wrap
        }
    }
}
