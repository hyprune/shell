import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../Builder.js" as Builder

// Director > Builder (RFC-0014 phase 1 and the world wizard as amended): New world walks through
// a name (and the Open Plain starter), a sky (a built-in one or the user's panorama), a floor (a
// built-in one or the user's tileable image) and where you start, then creates the world folder
// (a git repository) and opens it in editor mode. In a folder: the unsaved-changes count, Save
// with an optional message (one commit), Release (a version tag; with a remote, a push and the
// release files), the sky and the floor (the wizard's choices) and the remote. Objects are
// placed from the Objects tab; core copies them into the folder. Every action is the hyprune
// CLI's `builder` command.
Item {
    id: root
    objectName: 'directorBuilder'
    readonly property var job: ShellState.builderJob
    readonly property var b: ShellState.builderState
    readonly property var status: ShellState.builderStatus
    readonly property var sky: ShellState.builderSky
    readonly property var wizard: ShellState.builderWizard
    readonly property string step: Builder.wizardStep(wizard)
    readonly property var wizardErrors: wizard ? Builder.wizardErrors(wizard, ShellState.builderIdentity) : []
    readonly property var floorForm: ShellState.builderFloor
    property bool browsing: false
    property string browseFor: 'sky'   // sky, floor, wizard-sky, wizard-floor

    Keys.onPressed: (event) => {
        if (event.modifiers !== Qt.NoModifier || ShellState.builderBusy) return;
        if (!root.b && !root.wizard && event.key === Qt.Key_N) { ShellState.builderWizardStart(); Qt.callLater(() => nameField.forceActiveFocus()); event.accepted = true; }
        else if (root.b && event.key === Qt.Key_S) { messageField.forceActiveFocus(); event.accepted = true; }
        else if (root.b && event.key === Qt.Key_R) { versionField.forceActiveFocus(); event.accepted = true; }
        else if (root.b && event.key === Qt.Key_K) { root.openSkyBrowser(''); event.accepted = true; }
    }
    function openBrowser(target, path) { browseFor = target; browsing = true; skyBrowser.open(path || ''); }
    function openSkyBrowser(path) { openBrowser(root.wizard ? 'wizard-sky' : 'sky', path); }
    function openFloorBrowser(path) { openBrowser(root.wizard ? 'wizard-floor' : 'floor', path); }

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
    // A built-in sky or floor: its thumbnail and name; gold when chosen.
    component PresetTile: AbstractButton {
        id: tile
        property string thumbnail: ''
        property string label: ''
        property bool chosen: false
        property int imageWidth: 192
        property int imageHeight: 96
        implicitWidth: imageWidth + 12
        implicitHeight: imageHeight + 36
        enabled: !ShellState.builderBusy
        focusPolicy: Qt.StrongFocus
        background: Rectangle {
            radius: Tokens.radius
            color: tile.hovered ? Tokens.raised : Tokens.panel
            border.width: tile.chosen || tile.activeFocus ? 2 : 1
            border.color: tile.chosen ? Tokens.gold : tile.activeFocus ? Tokens.accent : Tokens.line
        }
        contentItem: Column {
            spacing: 4
            leftPadding: 6; topPadding: 6
            Rectangle {
                width: tile.imageWidth; height: tile.imageHeight
                color: Tokens.ink
                Image { anchors.fill: parent; source: tile.thumbnail ? 'file://' + tile.thumbnail : ''; fillMode: Image.PreserveAspectCrop; asynchronous: true; visible: tile.thumbnail !== '' }
                HudLabel { anchors.centerIn: parent; visible: !tile.thumbnail; text: '…'; color: Tokens.muted }
            }
            HudLabel { text: tile.label; width: tile.imageWidth; elide: Text.ElideRight; font.pixelSize: 12; color: tile.chosen ? Tokens.gold : Tokens.text }
        }
    }
    // "Use my image…": a tile that opens the file browser.
    component ImageTile: AbstractButton {
        id: own
        property string label: 'Use my image…'
        property bool chosen: false
        property int imageWidth: 192
        property int imageHeight: 96
        implicitWidth: imageWidth + 12
        implicitHeight: imageHeight + 36
        enabled: !ShellState.builderBusy
        focusPolicy: Qt.StrongFocus
        background: Rectangle {
            radius: Tokens.radius
            color: own.hovered ? Tokens.raised : 'transparent'
            border.width: own.chosen || own.activeFocus ? 2 : 1
            border.color: own.chosen ? Tokens.gold : own.activeFocus ? Tokens.accent : Tokens.line
        }
        contentItem: Item {
            HudLabel { anchors.centerIn: parent; text: '+\n' + own.label; horizontalAlignment: Text.AlignHCenter; font.pixelSize: 13; color: own.chosen ? Tokens.gold : Tokens.text }
        }
    }

    // ---- choosing a sky image (in-Director file browser, PNG or JPEG) ----
    SourceFileBrowser {
        id: skyBrowser
        objectName: 'builderSkyBrowser'
        anchors.fill: parent
        z: 2
        visible: root.browsing
        readonly property bool forSky: root.browseFor === 'sky' || root.browseFor === 'wizard-sky'
        extensions: forSky ? Builder.SKY_FORMATS : Builder.FLOOR_FORMATS
        purpose: forSky ? 'Choose a sky: a 360° panorama (equirectangular, 2:1, 1,024 to 8,192 px wide)' : 'Choose a floor texture: a tileable image'
        hint: 'Enter opens a folder or picks the image · Backspace goes up · Esc closes · ' + (forSky ? 'PNG, JPEG, EXR or HDR' : 'PNG or JPEG')
        onPicked: (path) => {
            root.browsing = false;
            if (root.browseFor === 'wizard-sky') ShellState.builderWizardSet({sky: {path: path, license: '', author: '', source: ''}});
            else if (root.browseFor === 'wizard-floor') ShellState.builderWizardSet({floor: {path: path, license: '', author: '', source: '', tile: 2}});
            else if (root.browseFor === 'floor') ShellState.builderFloorPick(path);
            else { ShellState.builderSkyPick(path); Qt.callLater(() => licenseField.forceActiveFocus()); }
        }
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

            // ======== New world: the wizard ========
            ColumnLayout {
                objectName: 'builderWizard'
                Layout.fillWidth: true
                visible: !root.b && !!root.wizard
                spacing: 10
                RowLayout {
                    Layout.fillWidth: true
                    Caption { text: 'NEW WORLD · ' + (root.wizard ? root.wizard.step + 1 : 1) + ' OF ' + Builder.WIZARD_STEPS.length + ' · ' + String(Builder.STEP_TITLES[root.step]).toUpperCase(); Layout.fillWidth: true }
                    ActionButton { objectName: 'builder-wizard-cancel'; text: 'Cancel'; enabled: !ShellState.builderBusy; onClicked: ShellState.builderWizard = null }
                }

                // -- 1. name and starter --
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: root.step === 'name'
                    spacing: 8
                    Field {
                        id: nameField
                        objectName: 'builderName'
                        placeholderText: 'Name your world'
                        maximumLength: Builder.NAME_MAX
                        text: root.wizard ? root.wizard.name : ''
                        onTextEdited: ShellState.builderWizardSet({name: text})
                        onAccepted: nextButton.clicked()
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: starterText.implicitHeight + 20
                        radius: Tokens.radius
                        color: Tokens.panel
                        border.width: 2; border.color: Tokens.gold
                        ColumnLayout {
                            id: starterText
                            anchors.fill: parent; anchors.margins: 10
                            spacing: 2
                            HudLabel { text: 'Open Plain'; font.pixelSize: 14; color: Tokens.gold }
                            Note { text: 'A big flat plain, 2 km across, with the floor and sky you choose next: an empty place to make your own. Place objects, your imports and workspace screens on it from Objects.' }
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
                }

                // -- 2. sky --
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: root.step === 'sky'
                    spacing: 8
                    Note { text: 'The sky lights the world too. Pick one, or use your own 360° panorama (equirectangular PNG, JPEG, EXR or HDR).' }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Repeater {
                            model: ShellState.builderSkies
                            PresetTile {
                                required property var modelData
                                objectName: 'builder-sky-preset:' + modelData.id
                                thumbnail: modelData.thumbnail || ''
                                label: modelData.name
                                chosen: !!root.wizard && root.wizard.sky.preset === modelData.id
                                onClicked: ShellState.builderWizardSet({sky: {preset: modelData.id}})
                            }
                        }
                        ImageTile {
                            objectName: 'builder-wizard-sky-image'
                            chosen: !!root.wizard && !root.wizard.sky.preset
                            onClicked: root.openBrowser('wizard-sky', '')
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        visible: !!root.wizard && !root.wizard.sky.preset
                        spacing: 8
                        HudLabel { text: root.wizard && root.wizard.sky.path ? root.wizard.sky.path : 'No image chosen yet'; font.family: Tokens.mono; font.pixelSize: 11; color: Tokens.muted; elide: Text.ElideLeft; Layout.fillWidth: true }
                        Field { objectName: 'builderWizardSkyLicense'; placeholderText: 'Licence (SPDX, like CC0-1.0)'; text: root.wizard && root.wizard.sky.license || ''; onTextEdited: ShellState.builderWizardSet({sky: Object.assign({}, root.wizard.sky, {license: text})}) }
                        Field { objectName: 'builderWizardSkyAuthor'; placeholderText: 'Author'; text: root.wizard && root.wizard.sky.author || ''; onTextEdited: ShellState.builderWizardSet({sky: Object.assign({}, root.wizard.sky, {author: text})}) }
                        Field { objectName: 'builderWizardSkySource'; placeholderText: 'Source (a link, or where it comes from)'; text: root.wizard && root.wizard.sky.source || ''; onTextEdited: ShellState.builderWizardSet({sky: Object.assign({}, root.wizard.sky, {source: text})}) }
                    }
                }

                // -- 3. floor --
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: root.step === 'floor'
                    spacing: 8
                    Note { text: 'The ground of the plain. Pick one, or use your own tileable texture (PNG or JPEG); the tile is how many metres one copy covers.' }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Repeater {
                            model: ShellState.builderFloors
                            PresetTile {
                                required property var modelData
                                objectName: 'builder-floor-preset:' + modelData.id
                                imageWidth: 112; imageHeight: 112
                                thumbnail: modelData.thumbnail || ''
                                label: modelData.name
                                chosen: !!root.wizard && root.wizard.floor.preset === modelData.id
                                onClicked: ShellState.builderWizardSet({floor: {preset: modelData.id, tile: null}})
                            }
                        }
                        ImageTile {
                            objectName: 'builder-wizard-floor-image'
                            imageWidth: 112; imageHeight: 112
                            chosen: !!root.wizard && !root.wizard.floor.preset
                            onClicked: root.openBrowser('wizard-floor', '')
                        }
                    }
                    RowLayout {
                        spacing: 10
                        HudLabel { text: 'Tile (metres)'; font.pixelSize: 12; color: Tokens.muted }
                        Field {
                            objectName: 'builderTile'
                            Layout.fillWidth: false; Layout.preferredWidth: 110
                            placeholderText: {
                                var w = root.wizard, f = w ? ShellState.builderFloors.filter(p => p.id === w.floor.preset)[0] : null;
                                return f ? String(f.tile) : '2';
                            }
                            text: root.wizard && root.wizard.floor.tile !== null && root.wizard.floor.tile !== undefined ? String(root.wizard.floor.tile) : ''
                            onTextEdited: ShellState.builderWizardSet({floor: Object.assign({}, root.wizard.floor, {tile: text.trim() === '' ? null : text.trim()})})
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        visible: !!root.wizard && !root.wizard.floor.preset
                        spacing: 8
                        HudLabel { text: root.wizard && root.wizard.floor.path ? root.wizard.floor.path : 'No image chosen yet'; font.family: Tokens.mono; font.pixelSize: 11; color: Tokens.muted; elide: Text.ElideLeft; Layout.fillWidth: true }
                        Field { objectName: 'builderWizardFloorLicense'; placeholderText: 'Licence (SPDX, like CC0-1.0)'; text: root.wizard && root.wizard.floor.license || ''; onTextEdited: ShellState.builderWizardSet({floor: Object.assign({}, root.wizard.floor, {license: text})}) }
                        Field { objectName: 'builderWizardFloorAuthor'; placeholderText: 'Author'; text: root.wizard && root.wizard.floor.author || ''; onTextEdited: ShellState.builderWizardSet({floor: Object.assign({}, root.wizard.floor, {author: text})}) }
                        Field { objectName: 'builderWizardFloorSource'; placeholderText: 'Source (a link, or where it comes from)'; text: root.wizard && root.wizard.floor.source || ''; onTextEdited: ShellState.builderWizardSet({floor: Object.assign({}, root.wizard.floor, {source: text})}) }
                    }
                }

                // -- 4. where you start --
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: root.step === 'spawn'
                    spacing: 8
                    Note { text: 'You start in the middle of the plain. Which way do you face?' }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Repeater {
                            model: Builder.FACINGS
                            ActionButton {
                                required property var modelData
                                objectName: 'builder-facing:' + modelData.id
                                text: (root.wizard && root.wizard.facing === modelData.id ? '● ' : '') + modelData.label
                                primary: !!root.wizard && root.wizard.facing === modelData.id
                                enabled: !ShellState.builderBusy
                                onClicked: ShellState.builderWizardSet({facing: modelData.id})
                            }
                        }
                    }
                    Note { objectName: 'builderWizardSummary'; color: Tokens.text; text: Builder.wizardSummary(root.wizard, ShellState.builderSkies, ShellState.builderFloors) }
                }

                Repeater {
                    model: root.wizardErrors
                    Note { required property string modelData; visible: root.step !== 'name' || (root.wizard && root.wizard.name !== ''); text: '· ' + modelData }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Item { Layout.fillWidth: true }
                    ActionButton { objectName: 'builder-wizard-back'; text: 'Back'; enabled: !ShellState.builderBusy && !!root.wizard && root.wizard.step > 0; onClicked: ShellState.builderWizardMove(-1) }
                    ActionButton {
                        id: nextButton
                        objectName: 'builder-wizard-next'
                        text: 'Next'
                        visible: !Builder.wizardLast(root.wizard)
                        enabled: !ShellState.builderBusy && root.wizardErrors.length === 0
                        onClicked: ShellState.builderWizardMove(1)
                    }
                    ActionButton {
                        objectName: 'builder-create'
                        text: 'Create and go there'
                        primary: true
                        visible: Builder.wizardLast(root.wizard)
                        enabled: !ShellState.builderBusy && root.wizardErrors.length === 0
                        onClicked: ShellState.builderWizardCreate()
                    }
                }
            }

            // ======== not in a world folder: start one, or open one ========
            ColumnLayout {
                Layout.fillWidth: true
                visible: !root.b && !root.wizard
                spacing: 10
                Caption { text: 'BUILD A WORLD' }
                Note { text: 'Start from Open Plain, a big flat plain with the sky and floor you choose, in a folder of its own. Place your objects, imports and workspace screens on it from Objects. Save keeps your changes as a version in the folder\'s history (git); Release gives the world a version number.' }
                ActionButton {
                    objectName: 'builder-new'
                    text: 'New world…'
                    primary: true
                    enabled: !ShellState.builderBusy
                    onClicked: { ShellState.builderWizardStart(); Qt.callLater(() => nameField.forceActiveFocus()); }
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

                Caption { text: 'CHECKLIST'; Layout.topMargin: 6 }
                HudLabel {
                    objectName: 'builderCheckSummary'
                    text: Builder.checkSummary(ShellState.builderCheck)
                    font.pixelSize: 13
                    color: Builder.checkBlocking(ShellState.builderCheck).length ? Tokens.gold : Tokens.muted
                }
                Repeater {
                    model: ShellState.builderCheck ? ShellState.builderCheck.items : []
                    RowLayout {
                        required property var modelData
                        objectName: 'builderCheck:' + modelData.id + (modelData.target ? ':' + modelData.target : '')
                        Layout.fillWidth: true
                        spacing: 8
                        HudLabel {
                            Layout.alignment: Qt.AlignTop
                            Layout.preferredWidth: 14
                            text: Builder.checkMark(modelData)
                            font.pixelSize: 13
                            color: modelData.done && modelData.level !== 'warning' ? Tokens.positive : modelData.blocks ? Tokens.warning : Tokens.gold
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 1
                            HudLabel { text: modelData.label; font.pixelSize: 12; color: Tokens.text; Layout.fillWidth: true; elide: Text.ElideRight }
                            HudLabel {
                                visible: !modelData.done || modelData.level === 'warning'
                                text: modelData.message + (modelData.hint ? ' ' + modelData.hint + '.' : '')
                                font.pixelSize: 11; color: Tokens.muted; wrapMode: Text.Wrap; Layout.fillWidth: true
                            }
                        }
                        ActionButton {
                            visible: !!modelData.show && (!modelData.done || modelData.level === 'warning')
                            objectName: 'builder-show:' + modelData.id + (modelData.target ? ':' + modelData.target : '')
                            text: 'Show me'
                            onClicked: ShellState.builderShow(modelData)
                        }
                    }
                }

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
                Note {
                    visible: Builder.checkBlocking(ShellState.builderCheck).length > 0
                    color: Tokens.gold
                    text: 'Release waits for the checklist: ' + Builder.checkBlocking(ShellState.builderCheck).map(function (i) { return i.label; }).join('; ') + '.'
                }
                RowLayout {
                    visible: Builder.releaseRefused(root.job)
                    spacing: 10
                    Note { Layout.fillWidth: true; text: 'The made world would strand players there. Fix the items above, or release it as it is.' }
                    ActionButton {
                        objectName: 'builder-release-anyway'
                        text: 'Release anyway'
                        enabled: !ShellState.builderBusy && !!root.job
                        onClicked: ShellState.builderRelease(root.job.version || '', root.job.notes || '', true)
                    }
                }
                Note {
                    objectName: 'builderPublishing'
                    visible: !!(root.job && root.job.kind === 'release' && root.job.phase === 'done' && root.job.result && root.job.result.publishing)
                    text: visible ? Builder.publishingText(root.job.result) : ''
                }

                Caption { text: 'SKY'; Layout.topMargin: 6 }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    HudLabel { Layout.fillWidth: true; text: root.status && root.status.sky ? (root.status.sky.preset ? Builder.skyLabel(root.status.sky, ShellState.builderSkies) + ' (built in)' : root.status.sky.image + ' · ' + root.status.sky.license + ' · ' + root.status.sky.author) : ''; font.pixelSize: 12; color: Tokens.muted; elide: Text.ElideRight }
                    ActionButton { objectName: 'builder-sky'; text: 'Choose image…'; enabled: !ShellState.builderBusy; onClicked: root.openBrowser('sky', '') }
                }
                Flow {
                    Layout.fillWidth: true
                    spacing: 8
                    Repeater {
                        model: ShellState.builderSkies
                        PresetTile {
                            required property var modelData
                            objectName: 'builder-set-sky:' + modelData.id
                            imageWidth: 128; imageHeight: 64
                            thumbnail: modelData.thumbnail || ''
                            label: modelData.name
                            chosen: !!root.status && !!root.status.sky && root.status.sky.preset === modelData.id
                            onClicked: ShellState.builderSkyPreset(modelData.id)
                        }
                    }
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

                Caption { text: 'FLOOR'; Layout.topMargin: 6 }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    HudLabel {
                        Layout.fillWidth: true
                        text: root.status && root.status.floor ? Builder.floorLabel(root.status.floor, ShellState.builderFloors) + (root.status.floor.preset ? '' : ' · ' + root.status.floor.license + ' · ' + root.status.floor.author)
                              : 'Grid, every 10 m'
                        font.pixelSize: 12; color: Tokens.muted; elide: Text.ElideRight
                    }
                    Field {
                        id: floorTileField
                        objectName: 'builderFloorTile'
                        Layout.fillWidth: false; Layout.preferredWidth: 110
                        placeholderText: root.status && root.status.floor ? String(root.status.floor.tile) + ' m' : '10 m'
                    }
                    ActionButton {
                        objectName: 'builder-floor-tile-apply'
                        text: 'Set tile'
                        enabled: !ShellState.builderBusy && floorTileField.text.trim() !== '' && !Builder.tileError(floorTileField.text)
                        onClicked: { if (ShellState.builderFloorApply({tile: floorTileField.text.trim()})) floorTileField.text = ''; }
                    }
                    ActionButton { objectName: 'builder-floor-image'; text: 'Choose image…'; enabled: !ShellState.builderBusy; onClicked: root.openBrowser('floor', '') }
                }
                Flow {
                    Layout.fillWidth: true
                    spacing: 8
                    Repeater {
                        model: ShellState.builderFloors
                        PresetTile {
                            required property var modelData
                            objectName: 'builder-set-floor:' + modelData.id
                            imageWidth: 64; imageHeight: 64
                            thumbnail: modelData.thumbnail || ''
                            label: modelData.name
                            chosen: !!root.status && !!root.status.floor && root.status.floor.preset === modelData.id
                            onClicked: ShellState.builderFloorApply({preset: modelData.id})
                        }
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: root.floorForm !== null && !!root.floorForm && !!root.floorForm.path
                    spacing: 8
                    HudLabel { text: root.floorForm ? root.floorForm.path || '' : ''; font.family: Tokens.mono; font.pixelSize: 11; color: Tokens.muted; elide: Text.ElideLeft; Layout.fillWidth: true }
                    Field { objectName: 'builderFloorLicense'; placeholderText: 'Licence (SPDX, like CC0-1.0)'; onTextEdited: ShellState.builderFloorForm({license: text}) }
                    Field { objectName: 'builderFloorAuthor'; placeholderText: 'Author'; onTextEdited: ShellState.builderFloorForm({author: text}) }
                    Field { objectName: 'builderFloorSource'; placeholderText: 'Source (a link, or where it comes from)'; onTextEdited: ShellState.builderFloorForm({source: text}) }
                    Field { objectName: 'builderFloorImageTile'; placeholderText: 'Tile in metres (2)'; Layout.fillWidth: false; Layout.preferredWidth: 160; onTextEdited: ShellState.builderFloorForm({tile: text.trim() === '' ? 2 : text.trim()}) }
                    RowLayout {
                        spacing: 10
                        ActionButton { objectName: 'builder-floor-apply'; text: 'Use this floor'; enabled: !ShellState.builderBusy && Builder.floorErrors(root.floorForm).length === 0; onClicked: ShellState.builderFloorApply() }
                        ActionButton { text: 'Cancel'; onClicked: ShellState.builderFloor = null }
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
