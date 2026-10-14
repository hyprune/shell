import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../Builder.js" as Builder

// Director > Builder (RFC-0014 phase 1 as amended): "Build a world" asks for a name and creates a
// world folder (a git repository with the Flat land starter), then opens it in editor mode. In
// a folder: the unsaved-changes count, Save with an optional message (one commit), Release (a
// version tag; with a remote, a push and the release files), the sky (an equirectangular image
// with its provenance) and the remote. Objects are placed from the Objects tab; core copies
// them into the folder. Every action is the hyprune CLI's `builder` command.
Item {
    id: root
    objectName: 'directorBuilder'
    readonly property var job: ShellState.builderJob
    readonly property var b: ShellState.builderState
    readonly property var status: ShellState.builderStatus
    readonly property var sky: ShellState.builderSky
    readonly property bool choosingSky: sky !== null && !sky.path
    property bool browsing: false

    Keys.onPressed: (event) => {
        if (event.modifiers !== Qt.NoModifier || ShellState.builderBusy) return;
        if (!root.b && event.key === Qt.Key_N) { nameField.forceActiveFocus(); event.accepted = true; }
        else if (root.b && event.key === Qt.Key_S) { messageField.forceActiveFocus(); event.accepted = true; }
        else if (root.b && event.key === Qt.Key_R) { versionField.forceActiveFocus(); event.accepted = true; }
        else if (root.b && event.key === Qt.Key_K) { root.browsing = true; skyBrowser.open(''); event.accepted = true; }
    }
    function openSkyBrowser(path) { browsing = true; skyBrowser.open(path || ''); }

    component Field: TextField {
        Layout.fillWidth: true
        implicitHeight: 38
        color: Tokens.text
        placeholderTextColor: Tokens.muted
        selectionColor: Tokens.accent
        selectedTextColor: Tokens.ink
        font.family: Tokens.sans; font.pixelSize: 13
        leftPadding: 10; rightPadding: 10
        enabled: !ShellState.builderBusy
        background: Rectangle { radius: Tokens.radius; color: Tokens.panel; border.width: parent.activeFocus ? 2 : 1; border.color: parent.activeFocus ? Tokens.gold : Tokens.line }
    }
    component Caption: HudLabel { font.pixelSize: 11; color: Tokens.gold; font.letterSpacing: 2 }
    component Note: HudLabel { Layout.fillWidth: true; font.pixelSize: 12; color: Tokens.muted; wrapMode: Text.Wrap }

    // ---- choosing a sky image (in-Director file browser, PNG or JPEG) ----
    SourceFileBrowser {
        id: skyBrowser
        objectName: 'builderSkyBrowser'
        anchors.fill: parent
        z: 2
        visible: root.browsing
        extensions: Builder.SKY_FORMATS
        purpose: 'Choose a sky: an equirectangular image (2:1, 1,024 to 8,192 px wide)'
        hint: 'Enter opens a folder or picks the image · Backspace goes up · Esc closes · PNG or JPEG'
        onPicked: (path) => { root.browsing = false; ShellState.builderSkyPick(path); Qt.callLater(() => licenseField.forceActiveFocus()); }
        onClosed: root.browsing = false
    }

    ScrollView {
        anchors.fill: parent
        visible: !root.browsing
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: 14

            // ---- job feedback ----
            HudLabel {
                objectName: 'builderFeedback'
                Layout.fillWidth: true
                visible: text !== ''
                wrapMode: Text.Wrap
                font.pixelSize: 13
                color: root.job && root.job.phase === 'failed' ? Tokens.warning : Tokens.text
                text: !root.job ? '' : root.job.phase === 'running' ? Builder.busyText(root.job)
                      : root.job.phase === 'failed' ? Builder.errorText(root.job.error) : Builder.resultText(root.job)
            }
            Repeater {
                model: Builder.warningsOf(root.job)
                Note { required property string modelData; text: '⚠ ' + modelData }
            }

            // ======== not in a world folder: build one, or open one ========
            ColumnLayout {
                Layout.fillWidth: true
                visible: !root.b
                spacing: 10
                Caption { text: 'BUILD A WORLD' }
                Note { text: 'A big flat plain with a sky you can change, in a folder of its own. Place your objects, imports and workspace screens on it from Objects. Save keeps your changes as a version in the folder\'s history (git); Release gives the world a version number.' }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Field {
                        id: nameField
                        objectName: 'builderName'
                        placeholderText: 'Name your world'
                        maximumLength: Builder.NAME_MAX
                        onAccepted: createButton.clicked()
                    }
                    ActionButton {
                        id: createButton
                        objectName: 'builder-create'
                        text: 'Build'
                        enabled: !ShellState.builderBusy && !Builder.nameError(nameField.text) && Builder.identityErrors(ShellState.builderIdentity).length === 0
                        onClicked: ShellState.builderCreate(nameField.text)
                    }
                }
                // git has no commit identity: asked once, stored in the new folder only.
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: ShellState.builderIdentity !== null
                    spacing: 8
                    Note { text: 'Your saves are signed with a name and an email address. They stay in this world\'s folder (and travel with it if you publish it).' }
                    Field { objectName: 'builderGitName'; placeholderText: 'Your name'; onTextEdited: ShellState.builderIdentity = Object.assign({}, ShellState.builderIdentity, {name: text}) }
                    Field { objectName: 'builderGitEmail'; placeholderText: 'Your email address'; onTextEdited: ShellState.builderIdentity = Object.assign({}, ShellState.builderIdentity, {email: text}) }
                }

                Caption { text: 'MY WORLDS'; Layout.topMargin: 8 }
                Note { visible: ShellState.builderProjects.length === 0; text: 'No worlds yet.' }
                Repeater {
                    model: ShellState.builderProjects
                    delegate: Rectangle {
                        required property var modelData
                        Layout.fillWidth: true
                        implicitHeight: 58
                        radius: Tokens.radius
                        color: Tokens.panel
                        border.width: 1; border.color: Tokens.line
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 12
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                HudLabel { text: modelData.name; font.pixelSize: 14; color: Tokens.text; elide: Text.ElideRight; Layout.fillWidth: true }
                                HudLabel { text: Builder.pendingText(modelData) + '  ·  ' + Builder.versionText(modelData); font.pixelSize: 11; color: Tokens.muted; elide: Text.ElideRight; Layout.fillWidth: true }
                            }
                            ActionButton {
                                objectName: 'builder-edit:' + modelData.projectId
                                text: 'Edit'
                                enabled: ShellState.available('world.load')
                                onClicked: ShellState.builderOpen(modelData.projectId)
                            }
                        }
                    }
                }
            }

            // ======== a world folder in editor mode ========
            ColumnLayout {
                Layout.fillWidth: true
                visible: !!root.b
                spacing: 10
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Caption { text: 'BUILDING' }
                        HudLabel { objectName: 'builderWorldName'; text: root.b ? root.b.name : ''; font.pixelSize: 18; color: Tokens.text }
                        HudLabel { text: root.b ? root.b.folder : ''; font.family: Tokens.mono; font.pixelSize: 11; color: Tokens.muted; elide: Text.ElideLeft; Layout.fillWidth: true }
                    }
                    ColumnLayout {
                        spacing: 2
                        HudLabel {
                            objectName: 'builderPending'
                            Layout.alignment: Qt.AlignRight
                            text: Builder.pendingText(root.status)
                            font.pixelSize: 13
                            color: root.status && root.status.pending.total ? Tokens.gold : Tokens.muted
                        }
                        HudLabel { Layout.alignment: Qt.AlignRight; text: Builder.lastSaveText(root.status); font.pixelSize: 11; color: Tokens.muted }
                    }
                }
                Note { visible: !!(root.b && root.b.error); color: Tokens.warning; text: root.b && root.b.error ? root.b.error : '' }
                Note { text: 'Place objects, your imports and workspace screens from Objects: each is copied into this world\'s folder, so the world keeps working wherever the folder goes.' }

                Caption { text: 'SAVE'; Layout.topMargin: 6 }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Field {
                        id: messageField
                        objectName: 'builderMessage'
                        placeholderText: 'What changed? (optional)'
                        maximumLength: Builder.MESSAGE_MAX
                        onAccepted: saveButton.clicked()
                    }
                    ActionButton {
                        id: saveButton
                        objectName: 'builder-save'
                        text: 'Save'
                        enabled: !ShellState.builderBusy && !!root.status && root.status.pending.total > 0
                        onClicked: { if (ShellState.builderSave(messageField.text)) messageField.text = ''; }
                    }
                }

                Caption { text: 'RELEASE'; Layout.topMargin: 6 }
                Note { text: Builder.versionText(root.status) + '. ' + Builder.remoteText(root.status) }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Field {
                        id: versionField
                        objectName: 'builderVersion'
                        Layout.fillWidth: false
                        Layout.preferredWidth: 140
                        placeholderText: root.status ? root.status.suggestedVersion : '0.1.0'
                    }
                    Field { id: notesField; objectName: 'builderNotes'; placeholderText: 'Release notes (optional)'; maximumLength: Builder.NOTES_MAX }
                    ActionButton {
                        objectName: 'builder-release'
                        text: 'Release'
                        enabled: !ShellState.builderBusy && !!root.status && root.status.pending.total === 0 && !Builder.versionError(versionField.text)
                        onClicked: { if (ShellState.builderRelease(versionField.text, notesField.text)) { versionField.text = ''; notesField.text = ''; } }
                    }
                }
                Note { visible: !!root.status && root.status.pending.total > 0; text: 'Save first: a release is made from the saved world.' }

                Caption { text: 'SKY'; Layout.topMargin: 6 }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    HudLabel { Layout.fillWidth: true; text: root.status && root.status.sky ? root.status.sky.image + ' · ' + root.status.sky.license + ' · ' + root.status.sky.author : ''; font.pixelSize: 12; color: Tokens.muted; elide: Text.ElideRight }
                    ActionButton { objectName: 'builder-sky'; text: 'Choose image…'; enabled: !ShellState.builderBusy; onClicked: root.openSkyBrowser('') }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: root.sky !== null
                    spacing: 8
                    HudLabel { text: root.sky ? root.sky.path : ''; font.family: Tokens.mono; font.pixelSize: 11; color: Tokens.muted; elide: Text.ElideLeft; Layout.fillWidth: true }
                    Field { id: licenseField; objectName: 'builderSkyLicense'; placeholderText: 'Licence (SPDX, like CC0-1.0)'; onTextEdited: ShellState.builderSkyForm({license: text}) }
                    Field { objectName: 'builderSkyAuthor'; placeholderText: 'Author'; onTextEdited: ShellState.builderSkyForm({author: text}) }
                    Field { objectName: 'builderSkySource'; placeholderText: 'Source (a link, or where it comes from)'; onTextEdited: ShellState.builderSkyForm({source: text}) }
                    RowLayout {
                        spacing: 10
                        ActionButton { objectName: 'builder-sky-apply'; text: 'Use this sky'; enabled: !ShellState.builderBusy && Builder.skyErrors(root.sky).length === 0; onClicked: ShellState.builderSkyApply() }
                        ActionButton { text: 'Cancel'; onClicked: ShellState.builderSky = null }
                    }
                }

                Caption { text: 'REMOTE'; Layout.topMargin: 6 }
                Note { text: 'Optional: an empty repository you created (for GitHub, named hyprune-world-<name>). Release then pushes to it and publishes the release files.' }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Field { id: remoteField; objectName: 'builderRemote'; placeholderText: root.status && root.status.remote ? root.status.remote.url : 'git@github.com:you/hyprune-world-name.git' }
                    ActionButton { objectName: 'builder-remote-set'; text: 'Set'; enabled: !ShellState.builderBusy && remoteField.text.trim() !== '' && !Builder.remoteError(remoteField.text); onClicked: { if (ShellState.builderRemote(remoteField.text)) remoteField.text = ''; } }
                    ActionButton { objectName: 'builder-remote-clear'; text: 'Clear'; enabled: !ShellState.builderBusy && !!root.status && !!root.status.remote; onClicked: ShellState.builderRemote('') }
                }
            }
        }
    }
}
