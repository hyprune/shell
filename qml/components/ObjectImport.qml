import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../Import.js" as Import
import "../Objects.js" as Objects

// Director > Objects > Import… (RFC-0014 as amended): choose a model with the in-Director file
// browser, review what the importer measured (units guess and the resulting size, triangles,
// textures) with the options and the provenance, import it (the hyprune CLI, stages shown),
// then put it in the pocket. Nothing is written before Import; a licence never blocks it.
Rectangle {
    id: panel
    objectName: 'objectImport'
    readonly property var job: ShellState.importJob
    readonly property string phase: job ? job.phase : ''
    readonly property var form: job && job.form ? job.form : Import.defaultForm(null)
    readonly property var inspection: job ? job.inspection : null
    readonly property var dims: Import.sizeMetres(inspection, form)
    readonly property var errors: phase === 'review' ? Import.formErrors(form) : []
    color: 'transparent'
    function set(key, value) { var patch = {}; patch[key] = value; ShellState.importForm(patch); }
    function focusFirst() { if (phase === 'browse') browser.open(''); else if (phase === 'review') nameField.forceActiveFocus(); }
    onPhaseChanged: if (phase === 'browse') Qt.callLater(() => browser.open(''))
    Component.onCompleted: if (phase === 'browse') browser.open('')
    Keys.onEscapePressed: ShellState.importClose()

    component Field: TextField {
        Layout.fillWidth: true
        implicitHeight: 38
        color: Tokens.text
        placeholderTextColor: Tokens.muted
        selectionColor: Tokens.accent
        selectedTextColor: Tokens.ink
        font.family: Tokens.sans; font.pixelSize: 13
        leftPadding: 10; rightPadding: 10
        background: Rectangle { radius: Tokens.radius; color: Tokens.panel; border.width: parent.activeFocus ? 2 : 1; border.color: parent.activeFocus ? Tokens.gold : Tokens.line }
    }
    component Caption: HudLabel { font.pixelSize: 11; color: Tokens.muted; font.letterSpacing: 1.2 }
    component Note: HudLabel { Layout.fillWidth: true; font.pixelSize: 12; color: Tokens.muted; wrapMode: Text.Wrap }

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            HudLabel { text: 'IMPORT A MODEL'; color: Tokens.gold; font.pixelSize: 12; font.letterSpacing: 2 }
            HudLabel {
                objectName: 'importFile'
                Layout.fillWidth: true
                text: panel.job && panel.job.path ? panel.job.path : 'glTF, GLB, OBJ, FBX, DAE, 3DS, PLY or STL'
                font.family: Tokens.mono; font.pixelSize: 12; color: Tokens.muted; elide: Text.ElideLeft
            }
            ActionButton { objectName: 'import-close'; text: ShellState.importBusy ? 'Cancel' : 'Close'; onClicked: ShellState.importClose() }
        }

        // ---- 1. Choose a file ----
        SourceFileBrowser {
            id: browser
            objectName: 'importBrowser'
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: panel.phase === 'browse'
            extensions: Import.FORMATS
            purpose: 'Choose a model to import'
            hint: 'Enter opens a folder or imports a model · Backspace goes up · Esc closes · glTF, GLB, OBJ, FBX, DAE, 3DS, PLY, STL'
            onPicked: (path) => ShellState.importPick(path)
            onClosed: ShellState.importClose()
        }

        // ---- Busy: measuring, or importing stage by stage ----
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: panel.phase === 'inspecting' || panel.phase === 'running'
            spacing: 10
            HudLabel {
                Layout.fillWidth: true
                text: panel.phase === 'inspecting' ? 'Reading the model…' : 'Importing ' + (panel.form.name || '') + '…'
                font.pixelSize: Tokens.title; font.weight: Font.Light
            }
            Flow {
                objectName: 'importStages'
                Layout.fillWidth: true
                visible: panel.phase === 'running'
                spacing: 8
                Repeater {
                    model: Import.stageRows(panel.job)
                    delegate: Rectangle {
                        required property var modelData
                        width: stageText.implicitWidth + 20; height: 28; radius: 3
                        color: modelData.state === 'current' ? Tokens.raised : 'transparent'
                        border.color: modelData.state === 'waiting' ? Tokens.line : Tokens.gold
                        HudLabel { id: stageText; anchors.centerIn: parent; text: (modelData.state === 'done' ? '✓ ' : '') + modelData.label; font.pixelSize: 12
                                   color: modelData.state === 'waiting' ? Tokens.muted : Tokens.text }
                    }
                }
            }
            Note { text: panel.job && panel.job.message ? panel.job.message : 'This runs on this computer, without Blender. Cancel stops it and writes nothing.' }
            Item { Layout.fillHeight: true }
        }

        // ---- 2. Review ----
        ScrollView {
            id: review
            objectName: 'importReview'
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: panel.phase === 'review'
            clip: true
            contentWidth: availableWidth
            ColumnLayout {
                width: review.availableWidth
                spacing: 12
                GridLayout {
                    Layout.fillWidth: true
                    columns: review.availableWidth < 900 ? 1 : 2
                    columnSpacing: 28; rowSpacing: 12
                    // What the file holds.
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        spacing: 6
                        Caption { text: 'IN THE FILE' }
                        HudLabel {
                            objectName: 'importFacts'
                            Layout.fillWidth: true
                            text: panel.inspection ? [panel.inspection.format.toUpperCase() + (panel.inspection.backend === 'assimp' ? ' (through Assimp)' : ''),
                                   Import.count(panel.inspection.triangles) + ' triangles', panel.inspection.meshes + ' meshes', panel.inspection.materials + ' materials',
                                   panel.inspection.textures.length ? panel.inspection.textures.length + ' textures, largest ' + panel.inspection.maxTexture + ' px' : 'no textures',
                                   Import.fileSize(panel.inspection.bytes) + (panel.inspection.format === 'gltf' ? ' (the .gltf alone)' : '')].join('  ·  ') : ''
                            wrapMode: Text.Wrap; font.pixelSize: 13
                        }
                        Repeater {
                            model: panel.inspection ? panel.inspection.warnings : []
                            delegate: Note { required property var modelData; text: '⚠ ' + modelData; color: Tokens.warning }
                        }
                        Caption { text: 'SIZE'; Layout.topMargin: 8 }
                        HudLabel {
                            objectName: 'importSize'
                            Layout.fillWidth: true
                            text: Import.sizeText(panel.dims)
                            font.pixelSize: 18; font.weight: Font.Light
                        }
                        Note { objectName: 'importSizeWarning'; text: Import.sizeWarning(panel.dims); color: Tokens.warning; visible: text !== '' }
                        Caption { text: 'UNITS IN THE FILE' }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Choice {
                                objectName: 'importUnits'
                                Layout.preferredWidth: 180
                                model: Import.UNITS.map(u => u.label)
                                currentIndex: Import.UNITS.findIndex(u => u.id === panel.form.units)
                                onActivated: (index) => panel.set('units', Import.UNITS[index].id)
                            }
                            Segmented { objectName: 'importUp'; Layout.preferredWidth: 180; model: Import.UP; current: panel.form.up; onPicked: (id) => panel.set('up', id) }
                        }
                        Note { text: Import.unitsNote(panel.inspection, panel.form) + '. Check the size above: that is what you confirm with Import.' }
                        Caption { text: 'TURN' }
                        Segmented { objectName: 'importYaw'; Layout.preferredWidth: 300; model: Import.YAW; current: panel.form.yaw; onPicked: (id) => panel.set('yaw', id) }
                        Caption { text: 'STANDS ON' }
                        Segmented { objectName: 'importSurface'; Layout.preferredWidth: 360; model: Import.SURFACES; current: panel.form.surface; onPicked: (id) => panel.set('surface', id) }
                        Note { text: 'The pivot goes to the base (floor), the back (wall), the top (ceiling) or the centre (floats).' }
                    }
                    // Options and provenance.
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        spacing: 6
                        Caption { text: 'NAME' }
                        Field { id: nameField; objectName: 'import-name'; text: panel.form.name; maximumLength: 64; onTextEdited: panel.set('name', text) }
                        Caption { text: 'CATEGORY' }
                        Choice {
                            objectName: 'importCategory'
                            Layout.preferredWidth: 220
                            model: Import.CATEGORIES.map(c => Objects.categoryLabel(c))
                            currentIndex: Import.CATEGORIES.indexOf(panel.form.category)
                            onActivated: (index) => panel.set('category', Import.CATEGORIES[index])
                        }
                        Caption { text: 'TRIANGLES (TARGET)' }
                        RowLayout {
                            spacing: 8
                            Field { objectName: 'import-triangles'; Layout.preferredWidth: 140; Layout.fillWidth: false; text: panel.form.maxTriangles; inputMethodHints: Qt.ImhDigitsOnly; onTextEdited: panel.set('maxTriangles', text.replace(/[^0-9]/g, '')) }
                            Note { text: Import.trianglesNote(panel.inspection, panel.form) }
                        }
                        Caption { text: 'TEXTURES AT MOST' }
                        Segmented { objectName: 'importTextures'; Layout.preferredWidth: 330; model: Import.TEXTURES; current: panel.form.maxTexture; onPicked: (id) => panel.set('maxTexture', id) }
                        Caption { text: 'COLLISION' }
                        Segmented { objectName: 'importCollision'; Layout.preferredWidth: 330; model: Import.COLLISION; current: panel.form.collision; onPicked: (id) => panel.set('collision', id) }
                        Caption { text: 'LIGHTING' }
                        Segmented { objectName: 'importLighting'; Layout.preferredWidth: 330; model: Import.LIGHTING; current: panel.form.lighting; onPicked: (id) => panel.set('lighting', id) }
                        Caption { text: 'LICENCE, AUTHOR, SOURCE (RECORDED, NEVER REQUIRED)'; Layout.topMargin: 8 }
                        Note { objectName: 'importArchive'; visible: text !== ''; text: Import.archiveNote(panel.inspection) }
                        Repeater {
                            model: Import.licenceHints(panel.inspection)
                            delegate: Note { required property var modelData; text: 'Found in the archive (a suggestion): ' + modelData }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Choice {
                                objectName: 'importLicence'
                                Layout.preferredWidth: 220
                                model: Import.LICENCES.map(l => l.label)
                                currentIndex: Import.LICENCES.findIndex(l => l.id === panel.form.licence)
                                onActivated: (index) => panel.set('licence', Import.LICENCES[index].id)
                            }
                            Field { objectName: 'import-licence-other'; visible: panel.form.licence === 'other'; placeholderText: 'SPDX, e.g. MIT OR CC-BY-4.0'; text: panel.form.licenceOther; onTextEdited: panel.set('licenceOther', text) }
                        }
                        Field { objectName: 'import-author'; placeholderText: 'Author (empty: unknown)'; text: panel.form.author; maximumLength: 256; onTextEdited: panel.set('author', text) }
                        Field { objectName: 'import-source'; placeholderText: 'Source: a link or "my own work" (empty: unknown)'; text: panel.form.source; maximumLength: 1024; onTextEdited: panel.set('source', text) }
                    }
                }
                Repeater {
                    model: panel.errors
                    delegate: Note { required property var modelData; text: modelData; color: Tokens.warning }
                }
                RowLayout {
                    spacing: 8
                    ActionButton { objectName: 'import-run'; primary: true; text: 'Import'; enabled: !panel.errors.length; onClicked: ShellState.importRun() }
                    ActionButton { objectName: 'import-another'; text: 'Choose another file'; onClicked: ShellState.importOpen() }
                }
            }
        }

        // ---- A .zip with several models: choose one ----
        ColumnLayout {
            Layout.fillWidth: true
            visible: panel.phase === 'choose'
            spacing: 8
            HudLabel { Layout.fillWidth: true; text: 'This archive holds more than one model. Which one?'; font.pixelSize: 15; wrapMode: Text.Wrap }
            Repeater {
                model: panel.phase === 'choose' && panel.job ? panel.job.models : []
                delegate: ActionButton {
                    required property var modelData
                    objectName: 'import-entry:' + modelData
                    Layout.fillWidth: true
                    text: modelData
                    onClicked: ShellState.importChoose(modelData)
                }
            }
        }

        // ---- 3. Done or failed ----
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: panel.phase === 'done' || panel.phase === 'failed'
            spacing: 24
            Image {
                objectName: 'importThumbnail'
                Layout.preferredWidth: 256; Layout.preferredHeight: 256
                Layout.alignment: Qt.AlignTop
                visible: panel.phase === 'done'
                source: panel.phase === 'done' && panel.job.result ? 'file://' + panel.job.result.path + '/thumbnail.png' : ''
                fillMode: Image.PreserveAspectFit
                cache: false
            }
            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                spacing: 8
                HudLabel {
                    objectName: 'importOutcome'
                    Layout.fillWidth: true
                    text: panel.phase === 'done' ? (panel.job.result.manifest ? panel.job.result.manifest.name : 'Imported') : 'The import stopped'
                    font.pixelSize: Tokens.title; font.weight: Font.Light; wrapMode: Text.Wrap
                }
                Repeater {
                    model: panel.phase === 'done' ? Import.resultLines(panel.job.result) : []
                    delegate: HudLabel { required property var modelData; Layout.fillWidth: true; text: modelData; font.pixelSize: 13; wrapMode: Text.Wrap }
                }
                Repeater {
                    model: panel.phase === 'done' ? panel.job.result.warnings : []
                    delegate: Note { required property var modelData; text: '⚠ ' + modelData; color: Tokens.warning }
                }
                Note { visible: panel.phase === 'failed'; objectName: 'importError'; text: Import.errorText(panel.job ? panel.job.error : null); color: Tokens.warning }
                Note { visible: panel.phase === 'done'; text: ShellState.importListed ? 'It is in the catalog under Mine.' : 'Waiting for the catalog to list it…' }
                RowLayout {
                    spacing: 8
                    ActionButton { objectName: 'import-pocket'; primary: true; visible: panel.phase === 'done'; text: 'Add to pocket'; enabled: ShellState.importListed && ShellState.objectsCan('objects.pocket'); onClicked: ShellState.importPocket() }
                    ActionButton { objectName: 'import-back'; visible: panel.phase === 'failed' && !!(panel.job && panel.job.inspection); text: 'Back to the form'; onClicked: ShellState.importBack() }
                    ActionButton { objectName: 'import-next'; text: 'Import another'; onClicked: ShellState.importOpen() }
                }
            }
        }
    }
}
