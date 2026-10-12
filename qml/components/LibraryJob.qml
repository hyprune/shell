import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../Library.js" as Library

// Director > Library: one install or update job (RFC-0015 Install pipeline). The plan from
// `--plan --json` is shown with the provenance items for every package (name, id, version and
// tag, type, source label and URL, creator and repository, licence wording, sizes, short hash,
// requirements, the data-only line) before anything is downloaded. Install runs with `--yes`;
// a source change needs a second, explicit confirmation before `--accept-source-change`.
// Then the stages and download progress from the JSON lines, and the result or the error with
// its rule. Keys: Enter confirms, Esc goes back (a running job keeps running).
FocusScope {
    id: root
    objectName: 'libraryJob'
    readonly property var job: ShellState.libraryJob
    readonly property string phase: job ? job.phase : ''
    readonly property var plan: job ? job.plan : null
    readonly property var main: plan && plan.packages && plan.packages.length ? plan.packages[0] : null
    readonly property var change: Library.sourceChange(plan)
    readonly property var reqs: Library.requirements(plan)
    readonly property var error: Library.errorText(job ? job.error : null)
    readonly property string verb: job && job.kind === 'update' ? 'Update' : 'Install'
    readonly property bool cancellable: phase === 'planning' || (phase === 'running' && (job.stage === '' || job.stage === 'resolving' || job.stage === 'downloading'))
    property bool changeAsked: false     // the source change's second confirmation is showing
    onPhaseChanged: { if (phase !== 'confirm') changeAsked = false; }

    function primary() {
        if (phase === 'confirm') {
            if (change && !changeAsked) { changeAsked = true; return; }
            ShellState.libraryConfirm(!!change && changeAsked);
        } else if (phase === 'done') openResult();
        else if (phase === 'failed') ShellState.libraryClose();
    }
    function openResult() {
        var type = job && job.result && job.result.type ? job.result.type : job ? job.target.type : '';
        if (type === 'library') { ShellState.libraryClose(); ShellState.objectsView = 'catalog'; ShellState.tab = ShellState.tabObjects; }
        else if (ShellState.available('world.load')) { ShellState.action('world.load', {worldId: job.target.id}); ShellState.libraryClose(); }
        else ShellState.libraryClose();
    }
    function back() {
        if (changeAsked) { changeAsked = false; return; }
        if (!ShellState.libraryBusy) ShellState.libraryClose();
    }

    Keys.onEscapePressed: (event) => { if (ShellState.libraryBusy) { event.accepted = false; return; } root.back(); }
    Keys.onReturnPressed: root.primary()
    Keys.onEnterPressed: root.primary()

    component Caption: HudLabel { Layout.fillWidth: true; color: Tokens.gold; font.pixelSize: Tokens.caption; font.letterSpacing: 1.5 }
    component Note: HudLabel { Layout.fillWidth: true; color: Tokens.muted; font.pixelSize: 12; wrapMode: Text.Wrap }

    Rectangle { anchors.fill: parent; color: Tokens.panel; border.color: Tokens.line; radius: 3 }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 14

        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                HudLabel {
                    Layout.fillWidth: true
                    text: (root.verb + (root.job && root.job.target.type ? ' ' + Library.typeLabel(root.job.target.type) : '')).toUpperCase()
                          + '  /  ' + (root.phase === 'planning' ? 'PLAN' : root.phase === 'confirm' ? 'CONFIRM' : root.phase === 'running' ? 'IN PROGRESS'
                                       : root.phase === 'done' ? 'DONE' : 'FAILED')
                    color: Tokens.gold; font.pixelSize: 11; font.letterSpacing: 1.8
                }
                HudLabel {
                    objectName: 'libraryJobTitle'
                    Layout.fillWidth: true
                    text: root.main && root.main.name ? root.main.name : root.job ? root.job.target.name : ''
                    font.pixelSize: 24; font.weight: Font.Light
                }
            }
            ActionButton {
                objectName: 'library-job-cancel'
                visible: ShellState.libraryBusy
                text: 'Cancel'
                enabled: root.cancellable
                onClicked: ShellState.libraryCancel()
            }
            ActionButton {
                objectName: 'library-job-back'
                visible: !ShellState.libraryBusy
                text: 'Back  ·  Esc'
                onClicked: root.back()
            }
        }

        // ---- Plan and confirmation ----
        ScrollView {
            id: planScroll
            objectName: 'libraryPlan'
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.phase === 'confirm'
            clip: true
            contentWidth: availableWidth
            ColumnLayout {
                width: Math.min(planScroll.availableWidth - 12, 980)
                spacing: 10

                Rectangle {
                    objectName: 'librarySourceChange'
                    Layout.fillWidth: true
                    Layout.preferredHeight: changeText.implicitHeight + 24
                    visible: !!root.change
                    radius: 3
                    color: Tokens.raised
                    border.color: Tokens.warning
                    border.width: root.changeAsked ? 2 : 1
                    HudLabel {
                        id: changeText
                        x: 14; y: 12; width: parent.width - 28
                        wrapMode: Text.Wrap
                        color: Tokens.warning
                        font.pixelSize: 13
                        text: !root.change ? '' : root.changeAsked
                            ? 'Install from ' + root.change.to + ' instead of ' + root.change.from + '? The install from ' + root.change.from
                              + ' is replaced, and updates come from ' + root.change.to + ' from now on.'
                            : 'Source change: ' + root.change.id + ' is installed from ' + root.change.from + '. This plan installs it from '
                              + root.change.to + '.'
                    }
                }

                Caption { text: 'PACKAGE' }
                GridLayout {
                    objectName: 'libraryProvenance'
                    Layout.fillWidth: true
                    columns: 2
                    columnSpacing: 16
                    rowSpacing: 6
                    Repeater {
                        model: Library.provenance(root.main, ShellState.librarySources)
                        delegate: HudLabel {
                            required property var modelData
                            required property int index
                            Layout.row: index
                            Layout.column: 0
                            Layout.preferredWidth: 110
                            Layout.alignment: Qt.AlignTop
                            text: modelData.label
                            color: Tokens.muted; font.pixelSize: 12
                        }
                    }
                    Repeater {
                        model: Library.provenance(root.main, ShellState.librarySources)
                        delegate: HudLabel {
                            required property var modelData
                            required property int index
                            objectName: 'libraryFact:' + modelData.id
                            Layout.row: index
                            Layout.column: 1
                            Layout.fillWidth: true
                            text: modelData.value
                            wrapMode: Text.Wrap
                            font.family: modelData.id === 'hash' || modelData.id === 'id' ? Tokens.mono : Tokens.sans
                            font.pixelSize: 13
                            color: modelData.id === 'licence' && root.main && root.main.licenceNote !== 'reviewed' ? Tokens.gold : Tokens.text
                        }
                    }
                }

                Caption { text: 'REQUIREMENTS'; visible: true }
                Note {
                    objectName: 'libraryRequirements'
                    text: root.reqs.length ? root.reqs.map(r => r.text).join('\n') : 'No libraries pulled in.'
                    color: Tokens.text
                }
                Note {
                    text: 'Download ' + Library.sizeText(Library.planTotal(root.plan))
                          + (root.plan && root.plan.diskFreeAfter ? '  ·  ' + Library.sizeText(root.plan.diskFreeAfter) + ' free after install' : '')
                }

                Rectangle {
                    objectName: 'libraryDataOnly'
                    Layout.fillWidth: true
                    Layout.preferredHeight: dataText.implicitHeight + 20
                    radius: 3
                    color: 'transparent'
                    border.color: Tokens.line
                    HudLabel {
                        id: dataText
                        x: 14; y: 10; width: parent.width - 28
                        wrapMode: Text.Wrap
                        text: Library.DATA_ONLY
                        color: Tokens.positive
                        font.pixelSize: 13
                    }
                }
            }
        }

        // ---- Stages, progress, result ----
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.phase !== 'confirm'
            spacing: 14

            RowLayout {
                objectName: 'libraryStages'
                Layout.fillWidth: true
                spacing: 6
                Repeater {
                    model: Library.stageRows(root.job)
                    delegate: Rectangle {
                        required property var modelData
                        objectName: 'libraryStage:' + modelData.id
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        Layout.preferredHeight: 40
                        radius: 3
                        color: modelData.state === 'current' ? Tokens.raised : 'transparent'
                        border.color: modelData.state === 'failed' ? Tokens.warning : modelData.state === 'current' ? Tokens.gold : Tokens.line
                        border.width: modelData.state === 'current' || modelData.state === 'failed' ? 2 : 1
                        HudLabel {
                            anchors.fill: parent
                            leftPadding: 10
                            verticalAlignment: Text.AlignVCenter
                            text: (parent.modelData.state === 'done' ? '✓  ' : parent.modelData.state === 'failed' ? '✕  ' : parent.modelData.state === 'current' ? '●  ' : '○  ')
                                  + parent.modelData.label
                            font.pixelSize: 12
                            color: parent.modelData.state === 'done' ? Tokens.positive : parent.modelData.state === 'failed' ? Tokens.warning
                                 : parent.modelData.state === 'current' ? Tokens.text : Tokens.muted
                        }
                    }
                }
            }

            ColumnLayout {
                objectName: 'libraryProgress'
                Layout.fillWidth: true
                visible: !!(root.job && root.job.progress) && root.phase === 'running'
                spacing: 6
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 8
                    radius: 4
                    color: Tokens.ink
                    border.color: Tokens.line
                    Rectangle {
                        width: parent.width * Library.progressFraction(root.job ? root.job.progress : null)
                        height: parent.height
                        radius: 4
                        color: Tokens.accent
                    }
                }
                HudLabel {
                    objectName: 'libraryProgressText'
                    Layout.fillWidth: true
                    text: Library.progressText(root.job ? root.job.progress : null)
                    font.family: Tokens.mono; font.pixelSize: 12; color: Tokens.muted
                }
            }

            HudLabel {
                Layout.fillWidth: true
                visible: root.phase === 'planning' || root.phase === 'running'
                text: root.phase === 'planning' ? 'Reading the source for a plan. Nothing is downloaded before you confirm.'
                    : root.job && root.job.stage === 'downloading' ? 'Downloading the release asset into the cache.'
                    : root.job && root.job.stage === 'committing' ? 'Committing: moving the checked package into place.'
                    : 'Checking the package before it is installed.'
                color: Tokens.muted; font.pixelSize: 13; wrapMode: Text.Wrap
            }

            Rectangle {
                objectName: 'libraryError'
                Layout.fillWidth: true
                Layout.preferredHeight: errorColumn.implicitHeight + 24
                visible: root.phase === 'failed'
                radius: 3
                color: Tokens.raised
                border.color: Tokens.warning
                Column {
                    id: errorColumn
                    x: 14; y: 12; width: parent.width - 28
                    spacing: 6
                    HudLabel { objectName: 'libraryErrorText'; width: parent.width; text: root.error.line; wrapMode: Text.Wrap; color: Tokens.warning; font.pixelSize: 14 }
                    HudLabel { objectName: 'libraryErrorRule'; width: parent.width; visible: text !== ''; text: root.error.detail; font.family: Tokens.mono; font.pixelSize: 12; color: Tokens.muted; wrapMode: Text.Wrap }
                    HudLabel { width: parent.width; text: 'Nothing was installed; what was there before is unchanged.'; visible: root.job && root.job.stage !== 'committing'; font.pixelSize: 12; color: Tokens.muted; wrapMode: Text.Wrap }
                }
            }

            HudLabel {
                objectName: 'libraryDone'
                Layout.fillWidth: true
                visible: root.phase === 'done'
                text: root.job ? Library.resultText(root.job, root.main && root.main.name ? root.main.name : root.job.target.name)
                                 + (root.job.target.type === 'library' ? ' Its objects are in Objects > Catalog.' : '') : ''
                color: Tokens.positive; font.pixelSize: 15; wrapMode: Text.Wrap
            }

            Item { Layout.fillHeight: true }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            visible: root.phase === 'confirm' || root.phase === 'done' || root.phase === 'failed'
            Item { Layout.fillWidth: true }
            ActionButton {
                objectName: 'library-job-secondary'
                visible: root.phase === 'confirm'
                text: root.changeAsked ? 'Keep ' + (root.change ? root.change.from : '') : 'Cancel'
                onClicked: root.back()
            }
            ActionButton {
                objectName: 'library-job-primary'
                primary: true
                visible: root.phase === 'confirm' || root.phase === 'done'
                text: root.phase === 'done' ? (root.job && (root.job.result && root.job.result.type === 'library' || root.job.target.type === 'library') ? 'Open in Objects'
                                                : ShellState.available('world.load') ? 'Load' : 'Done')
                    : root.change ? (root.changeAsked ? 'Yes, install from ' + root.change.to : 'Change source…')
                    : root.verb + (root.main ? ' ' + root.main.tag : '')
                onClicked: root.primary()
            }
        }
    }
}
