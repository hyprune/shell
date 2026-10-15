import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../Shapes.js" as Shapes

// Director > Objects > Shapes (RFC-0014 amendment: primitives and materials, IPC 0.31): make a
// shape at exact sizes in a colour or material and place it with tool 5 (Make and place), and
// keep a library of materials (colour, texture, tile, glow, roughness, metalness). In a world
// folder they are saved in it (self-contained); elsewhere in your own folders, for any world.
// Saving a material rebuilds the shapes made with it and updates where they stand.
Item {
    id: root
    objectName: 'objectShapes'
    property var form: Shapes.newForm('box')
    property var material: null              // the material editor's form, null when closed
    property bool browsing: false
    readonly property var materialErrors: material ? Shapes.materialErrors(material) : []
    function focusFirst() { shapeForm.focusFirst(); }
    function make() { if (!Shapes.sizeErrors(form).length) ShellState.shapesMake(form); }
    onVisibleChanged: { if (visible) { ShellState.shapesLoadMaterials(); ShellState.builderLoadPresets(); } }
    Keys.onReturnPressed: make()
    Keys.onEnterPressed: make()

    component Field: TextField {
        Layout.fillWidth: true
        implicitHeight: 36
        color: Tokens.text
        placeholderTextColor: Tokens.muted
        selectionColor: Tokens.accent
        selectedTextColor: Tokens.ink
        font.family: Tokens.sans; font.pixelSize: 13
        leftPadding: 10; rightPadding: 10
        enabled: !ShellState.shapesBusy
        background: Rectangle { radius: Tokens.radius; color: Tokens.panel; border.width: parent.activeFocus ? 2 : 1; border.color: parent.activeFocus ? Tokens.gold : Tokens.line }
    }
    component Caption: HudLabel { font.pixelSize: 11; color: Tokens.gold; font.letterSpacing: 2 }
    component Note: HudLabel { Layout.fillWidth: true; font.pixelSize: 12; color: Tokens.muted; wrapMode: Text.Wrap }

    SourceFileBrowser {
        id: textureBrowser
        objectName: 'materialTextureBrowser'
        anchors.fill: parent
        z: 2
        visible: root.browsing
        extensions: ['png', 'jpg', 'jpeg']
        purpose: 'Choose a texture: an image that tiles (PNG or JPEG)'
        hint: 'Enter opens a folder or picks the image · Backspace goes up · Esc closes'
        onPicked: (path) => { root.browsing = false; root.material = Object.assign({}, root.material, {texture: {kind: 'image', path: path, license: '', author: '', source: ''}}); }
        onClosed: root.browsing = false
    }

    RowLayout {
        anchors.fill: parent
        visible: !root.browsing
        spacing: 20

        // ---- make a shape ----
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth
            clip: true
            ColumnLayout {
                width: parent.width - 12
                spacing: 12
                Caption { text: 'MAKE A SHAPE' }
                Note { text: ShellState.builderEditing ? 'Saved in this world\'s folder, so the world keeps working wherever it goes. Place it with tool 5, then move, turn and scale it with the gizmo (tool 4).'
                                                       : 'Saved in your own objects, for any world. Place it with tool 5, then move, turn and scale it with the gizmo (tool 4).' }
                ShapeForm {
                    id: shapeForm
                    Layout.fillWidth: true
                    value: root.form
                    onEdited: (v) => root.form = v
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    HudLabel { objectName: 'shapeSummary'; Layout.fillWidth: true; text: Shapes.summary(root.form, ShellState.shapesMaterials); font.pixelSize: 13; elide: Text.ElideRight }
                    ActionButton {
                        objectName: 'shape-make'
                        text: ShellState.shapesBusy && ShellState.shapesJob.kind === 'make' ? 'Making…' : 'Make and place  ·  Enter'
                        primary: true
                        enabled: !ShellState.shapesBusy && Shapes.sizeErrors(root.form).length === 0 && ShellState.objectsCan('objects.pocket')
                        onClicked: root.make()
                    }
                }
            }
        }

        // ---- materials ----
        Rectangle {
            Layout.preferredWidth: Math.min(460, root.width * .42)
            Layout.fillHeight: true
            color: Tokens.panel
            border.color: Tokens.line
            radius: 3
            ScrollView {
                anchors.fill: parent
                anchors.margins: 14
                contentWidth: availableWidth
                clip: true
                ColumnLayout {
                    width: parent.width - 8
                    spacing: 10
                    RowLayout {
                        Layout.fillWidth: true
                        Caption { text: 'MATERIALS  /  ' + ShellState.shapesMaterials.length; Layout.fillWidth: true }
                        ActionButton { objectName: 'material-new'; text: 'New material…'; enabled: !ShellState.shapesBusy; onClicked: root.material = Shapes.newMaterial('') }
                    }
                    Note { visible: !ShellState.shapesMaterials.length && !root.material; text: 'None yet. A material has a colour, and can have a texture that repeats every few metres, a glow, roughness and metalness. The built-in textures work as materials too.' }
                    Repeater {
                        model: root.material ? [] : ShellState.shapesMaterials
                        RowLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: 10
                            Rectangle {
                                width: 44; height: 30; radius: 2; color: modelData.colour
                                Image { anchors.fill: parent; source: modelData.swatch ? 'file://' + modelData.swatch : ''; fillMode: Image.PreserveAspectCrop; cache: false; asynchronous: true }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 0
                                HudLabel { text: modelData.name; font.pixelSize: 13 }
                                HudLabel { text: modelData.key + (modelData.textured ? '  ·  every ' + modelData.tile + ' m' : '') + '  ·  ' + modelData.license; font.pixelSize: 11; color: Tokens.muted; elide: Text.ElideRight; Layout.fillWidth: true }
                            }
                            ActionButton { objectName: 'material-edit:' + modelData.key; text: 'Edit'; implicitWidth: 72; enabled: !ShellState.shapesBusy; onClicked: root.material = Shapes.materialFrom(modelData) }
                        }
                    }

                    // -- the editor --
                    ColumnLayout {
                        objectName: 'materialEditor'
                        Layout.fillWidth: true
                        visible: !!root.material
                        spacing: 8
                        Field { objectName: 'materialKey'; placeholderText: 'Key (like oak-planks)'; enabled: !!root.material && root.material.fresh && !ShellState.shapesBusy; text: root.material ? root.material.key : ''; onTextEdited: root.material = Object.assign({}, root.material, {key: text.trim()}) }
                        Field { objectName: 'materialName'; placeholderText: 'Name'; text: root.material ? root.material.name : ''; onTextEdited: root.material = Object.assign({}, root.material, {name: text}) }
                        Field { objectName: 'materialColour'; placeholderText: 'Colour #rrggbb (tints the texture)'; text: root.material ? root.material.colour : ''; onTextEdited: root.material = Object.assign({}, root.material, {colour: text}) }
                        Segmented {
                            objectName: 'materialTexture'
                            Layout.fillWidth: true
                            model: [{id: 'keep', label: root.material && root.material.textured ? 'Keep texture' : 'No change'}, {id: 'none', label: 'No texture'}, {id: 'preset', label: 'Built in'}, {id: 'image', label: 'Image…'}]
                            current: root.material ? root.material.texture.kind : 'keep'
                            onPicked: (id) => {
                                if (id === 'image') { root.material = Object.assign({}, root.material, {texture: {kind: 'image', path: '', license: '', author: '', source: ''}}); root.browsing = true; textureBrowser.open(''); }
                                else root.material = Object.assign({}, root.material, {texture: id === 'preset' ? {kind: 'preset', preset: 'paving'} : {kind: id}});
                            }
                        }
                        Flow {
                            Layout.fillWidth: true
                            spacing: 6
                            visible: !!root.material && root.material.texture.kind === 'preset'
                            Repeater {
                                model: Shapes.BUILTIN
                                ActionButton {
                                    required property var modelData
                                    objectName: 'material-preset:' + modelData.key
                                    text: modelData.label
                                    implicitWidth: 110
                                    primary: !!root.material && root.material.texture.preset === modelData.key
                                    onClicked: root.material = Object.assign({}, root.material, {texture: {kind: 'preset', preset: modelData.key}})
                                }
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            visible: !!root.material && root.material.texture.kind === 'image'
                            spacing: 6
                            HudLabel { text: root.material && root.material.texture.path ? root.material.texture.path : 'No image chosen'; font.family: Tokens.mono; font.pixelSize: 11; color: Tokens.muted; elide: Text.ElideLeft; Layout.fillWidth: true }
                            Field { objectName: 'materialLicense'; placeholderText: 'Licence (SPDX, like CC0-1.0)'; onTextEdited: root.material = Object.assign({}, root.material, {texture: Object.assign({}, root.material.texture, {license: text})}) }
                            Field { objectName: 'materialAuthor'; placeholderText: 'Author'; onTextEdited: root.material = Object.assign({}, root.material, {texture: Object.assign({}, root.material.texture, {author: text})}) }
                            Field { objectName: 'materialSource'; placeholderText: 'Source (a link, or where it comes from)'; onTextEdited: root.material = Object.assign({}, root.material, {texture: Object.assign({}, root.material.texture, {source: text})}) }
                        }
                        RowLayout {
                            spacing: 8
                            Field { objectName: 'materialTile'; placeholderText: 'Tile (m)'; text: root.material ? String(root.material.tile) : ''; onTextEdited: root.material = Object.assign({}, root.material, {tile: text.trim()}) }
                            Field { objectName: 'materialRoughness'; placeholderText: 'Roughness 0-1'; text: root.material ? String(root.material.roughness) : ''; onTextEdited: root.material = Object.assign({}, root.material, {roughness: text.trim()}) }
                            Field { objectName: 'materialMetallic'; placeholderText: 'Metalness 0-1'; text: root.material ? String(root.material.metallic) : ''; onTextEdited: root.material = Object.assign({}, root.material, {metallic: text.trim()}) }
                        }
                        RowLayout {
                            spacing: 8
                            CheckBox {
                                objectName: 'materialGlow'
                                text: 'Glows'
                                checked: !!root.material && !!root.material.glow
                                onToggled: root.material = Object.assign({}, root.material, {glow: checked ? {colour: Shapes.hex(root.material.colour) || '#ffffff', strength: 2} : null, glowOff: !checked})
                            }
                            Field { objectName: 'materialGlowColour'; visible: !!root.material && !!root.material.glow; placeholderText: '#rrggbb'; text: root.material && root.material.glow ? root.material.glow.colour : ''; onTextEdited: root.material = Object.assign({}, root.material, {glow: Object.assign({}, root.material.glow, {colour: text})}) }
                            Field { objectName: 'materialGlowStrength'; visible: !!root.material && !!root.material.glow; placeholderText: '0-16'; text: root.material && root.material.glow ? String(root.material.glow.strength) : ''; onTextEdited: root.material = Object.assign({}, root.material, {glow: Object.assign({}, root.material.glow, {strength: text})}) }
                        }
                        Repeater {
                            model: root.materialErrors
                            HudLabel { required property string modelData; text: '· ' + modelData; font.pixelSize: 12; color: Tokens.warning; wrapMode: Text.Wrap; Layout.fillWidth: true }
                        }
                        RowLayout {
                            spacing: 8
                            ActionButton { objectName: 'material-save'; text: ShellState.shapesBusy ? 'Saving…' : 'Save material'; primary: true; enabled: !ShellState.shapesBusy && root.materialErrors.length === 0
                                           onClicked: { if (ShellState.shapesSaveMaterial(root.material)) root.material = null; } }
                            ActionButton { objectName: 'material-cancel'; text: 'Cancel'; onClicked: root.material = null }
                        }
                    }
                }
            }
        }
    }
}
