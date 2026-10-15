import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "../Shapes.js" as Shapes

// A shape's form (RFC-0014 amendment: primitives and materials): the shape (optional), its
// width, height and depth in metres (steps for stairs) and its material: a plain colour with an
// optional glow, a library material or a built-in texture. Used by Objects > Shapes to make one
// and by a placed primitive's panel to change it. `prefix` names the controls for automation.
ColumnLayout {
    id: form
    property var value: Shapes.newForm('box')
    property bool showShapes: true
    property string prefix: 'shape'
    signal edited(var value)
    spacing: 10
    function set(patch) { edited(Object.assign({}, value, patch)); }
    function setMaterial(patch) { edited(Object.assign({}, value, {material: Object.assign({}, value.material, patch)})); }
    function focusFirst() { sizeX.forceActiveFocus(); return true; }

    component Field: TextField {
        Layout.fillWidth: true
        Layout.preferredWidth: 1
        implicitHeight: 36
        color: Tokens.text
        selectionColor: Tokens.accent
        selectedTextColor: Tokens.ink
        font.family: Tokens.mono; font.pixelSize: 13
        leftPadding: 10; rightPadding: 10
        enabled: !ShellState.shapesBusy
        background: Rectangle { radius: Tokens.radius; color: Tokens.panel; border.width: parent.activeFocus ? 2 : 1; border.color: parent.activeFocus ? Tokens.gold : Tokens.line }
    }
    component Caption: HudLabel { font.pixelSize: 11; color: Tokens.muted }
    component Swatch: AbstractButton {
        id: sw
        property string colour: '#ffffff'
        property bool chosen: false
        implicitWidth: 28; implicitHeight: 28
        background: Rectangle { radius: 3; color: sw.colour; border.width: sw.chosen || sw.activeFocus ? 2 : 1; border.color: sw.chosen ? Tokens.gold : sw.activeFocus ? Tokens.accent : Tokens.line }
    }
    component MaterialTile: AbstractButton {
        id: mt
        property string label: ''
        property string swatch: ''
        property string colour: ''
        property bool chosen: false
        implicitWidth: 92; implicitHeight: 82
        enabled: !ShellState.shapesBusy
        background: Rectangle { radius: Tokens.radius; color: mt.hovered ? Tokens.raised : Tokens.panel; border.width: mt.chosen || mt.activeFocus ? 2 : 1; border.color: mt.chosen ? Tokens.gold : mt.activeFocus ? Tokens.accent : Tokens.line }
        contentItem: Column {
            spacing: 4; leftPadding: 6; topPadding: 6
            Rectangle {
                width: 80; height: 48; color: mt.colour || Tokens.ink
                Image { anchors.fill: parent; source: mt.swatch ? 'file://' + mt.swatch : ''; visible: mt.swatch !== ''; fillMode: Image.PreserveAspectCrop; asynchronous: true; cache: false }
            }
            HudLabel { width: 80; text: mt.label; elide: Text.ElideRight; font.pixelSize: 11; color: mt.chosen ? Tokens.gold : Tokens.text }
        }
    }

    // ---- shape ----
    Flow {
        Layout.fillWidth: true
        spacing: 8
        visible: form.showShapes
        Repeater {
            model: Shapes.SHAPES
            ActionButton {
                required property var modelData
                objectName: form.prefix + ':' + modelData.id
                text: modelData.label
                primary: form.value.shape === modelData.id
                implicitWidth: 104
                enabled: !ShellState.shapesBusy
                onClicked: form.edited(Shapes.withShape(form.value, modelData.id))
            }
        }
    }
    HudLabel { visible: form.showShapes; text: (Shapes.shape(form.value.shape) || {}).hint || ''; font.pixelSize: 12; color: Tokens.muted }

    // ---- size ----
    RowLayout {
        Layout.fillWidth: true
        spacing: 10
        Repeater {
            model: 3
            ColumnLayout {
                required property int index
                Layout.fillWidth: true
                spacing: 4
                Caption { text: Shapes.AXES[index] + ' (m)' }
                Field {
                    id: axisField
                    objectName: form.prefix + 'Size' + 'XYZ'[index]
                    text: String(form.value.size[index])
                    onTextEdited: form.edited(Shapes.setSize(form.value, index, text))
                    Component.onCompleted: { if (index === 0) form.sizeXField = axisField; }
                }
            }
        }
        ColumnLayout {
            visible: form.value.shape === 'stairs'
            Layout.preferredWidth: 110
            spacing: 4
            Caption { text: 'Steps' }
            Field {
                objectName: form.prefix + 'Steps'
                placeholderText: String(Shapes.stepsFor(form.value))
                text: form.value.steps ? String(form.value.steps) : ''
                onTextEdited: form.set({steps: text.trim() === '' ? null : text.trim()})
            }
        }
    }
    property var sizeXField: null
    readonly property var sizeX: sizeXField

    // ---- material ----
    Segmented {
        objectName: form.prefix + 'MaterialKind'
        Layout.preferredWidth: 320
        model: [{id: 'colour', label: 'Colour'}, {id: 'key', label: 'Material'}]
        current: form.value.material.kind
        onPicked: (id) => form.setMaterial({kind: id})
    }
    ColumnLayout {
        Layout.fillWidth: true
        visible: form.value.material.kind === 'colour'
        spacing: 8
        Flow {
            Layout.fillWidth: true
            spacing: 6
            Repeater {
                model: Shapes.SWATCHES
                Swatch {
                    required property string modelData
                    objectName: form.prefix + '-colour:' + modelData
                    colour: modelData
                    chosen: Shapes.hex(form.value.material.colour) === modelData
                    onClicked: form.setMaterial({colour: modelData})
                }
            }
        }
        RowLayout {
            spacing: 10
            Field { objectName: form.prefix + 'Colour'; Layout.preferredWidth: 140; Layout.fillWidth: false; text: form.value.material.colour; placeholderText: '#rrggbb'; onTextEdited: form.setMaterial({colour: text}) }
            CheckBox {
                objectName: form.prefix + 'Glow'
                text: 'Glows'
                checked: !!form.value.material.glow
                onToggled: form.setMaterial({glow: checked ? {colour: Shapes.hex(form.value.material.colour) || '#ffffff', strength: 2} : null})
            }
            Field {
                objectName: form.prefix + 'GlowColour'
                visible: !!form.value.material.glow
                Layout.preferredWidth: 120; Layout.fillWidth: false
                text: form.value.material.glow ? form.value.material.glow.colour : ''
                placeholderText: 'glow #rrggbb'
                onTextEdited: form.setMaterial({glow: Object.assign({}, form.value.material.glow, {colour: text})})
            }
            Field {
                objectName: form.prefix + 'GlowStrength'
                visible: !!form.value.material.glow
                Layout.preferredWidth: 90; Layout.fillWidth: false
                text: form.value.material.glow ? String(form.value.material.glow.strength) : ''
                placeholderText: '0-16'
                onTextEdited: form.setMaterial({glow: Object.assign({}, form.value.material.glow, {strength: text})})
            }
        }
    }
    Flow {
        Layout.fillWidth: true
        visible: form.value.material.kind === 'key'
        spacing: 8
        Repeater {
            model: ShellState.shapesMaterials
            MaterialTile {
                required property var modelData
                objectName: form.prefix + '-material:' + modelData.key
                label: modelData.name
                swatch: modelData.swatch || ''
                colour: modelData.colour
                chosen: form.value.material.key === modelData.key
                onClicked: form.setMaterial({key: modelData.key})
            }
        }
        Repeater {
            model: Shapes.BUILTIN.filter(b => !ShellState.shapesMaterials.some(m => m.key === b.key))
            MaterialTile {
                required property var modelData
                objectName: form.prefix + '-material:' + modelData.key
                label: modelData.label + ' (built in)'
                swatch: ((ShellState.builderFloors || []).filter(f => f.id === modelData.key)[0] || {}).thumbnail || ''
                chosen: form.value.material.key === modelData.key
                onClicked: form.setMaterial({key: modelData.key})
            }
        }
    }
    Repeater {
        model: Shapes.sizeErrors(form.value)
        HudLabel { required property string modelData; text: '· ' + modelData; font.pixelSize: 12; color: Tokens.warning }
    }
}
