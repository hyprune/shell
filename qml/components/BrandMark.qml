import QtQuick
import QtQuick.Shapes
import "../theme"
import "brand/BrandMarks.js" as BrandMarks

// Hyprune mark in one ink, drawn from the vendored masters (brand/BRAND.md).
// `size` is the logical box edge; the drawing is picked by the rendered size in
// physical pixels (output scale times any ancestor `scale`, e.g. the Director's
// uiScale), per the brand size rule. The box is the master's full viewBox, which
// already holds the 32-unit clear space around the room drawings.
Item {
    id: root

    property real size: 48
    property color color: Tokens.accent
    // Logical -> physical pixels: output scale times every ancestor's scale.
    // The window's ratio is the fractional one (Screen rounds 1.25 up to 2 on Wayland).
    property real pixelRatio: {
        var ratio = (Window.window && Window.window.devicePixelRatio) || Screen.devicePixelRatio || 1;
        for (var item = root; item; item = item.parent) ratio *= item.scale;
        return ratio;
    }
    readonly property int physicalSize: Math.round(size * pixelRatio)
    readonly property string variant: BrandMarks.variantFor(physicalSize)
    readonly property var master: BrandMarks.masters[variant]
    readonly property var strokes: BrandMarks.strokeGroups(variant)
    readonly property string fills: BrandMarks.fillPath(variant)
    readonly property real unit: size / master.viewBox
    // Visible ink edges inside the box, in logical px (for aligning ink to text).
    readonly property real inkLeft: master.ink[0] * unit
    readonly property real inkRight: size - master.ink[2] * unit
    readonly property real inkTop: master.ink[1] * unit
    readonly property real inkBottom: size - master.ink[3] * unit

    // Box edge for a given room ink height (optical proportions, so a size
    // binding never depends on the variant it selects).
    function sizeForInkHeight(height) {
        var room = BrandMarks.masters.optical;
        return height * room.viewBox / (room.ink[3] - room.ink[1]);
    }

    implicitWidth: size
    implicitHeight: size
    Accessible.role: Accessible.Graphic
    Accessible.name: 'Hyprune'

    Shape {
        anchors.fill: parent
        // Analytic antialiasing that stays crisp at any scale without MSAA.
        preferredRendererType: Shape.CurveRenderer
        // README: opacity applies to the whole group so overlapping strokes don't darken.
        layer.enabled: root.opacity < 1
        layer.samples: 4

        ShapePath {
            scale: Qt.size(root.unit, root.unit)
            fillColor: 'transparent'
            strokeColor: root.color
            strokeWidth: root.strokes[0].width * root.unit
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            PathSvg { path: root.strokes[0].d }
        }

        ShapePath {
            scale: Qt.size(root.unit, root.unit)
            fillColor: 'transparent'
            strokeColor: root.strokes.length > 1 ? root.color : 'transparent'
            strokeWidth: root.strokes.length > 1 ? root.strokes[1].width * root.unit : 0
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            PathSvg { path: root.strokes.length > 1 ? root.strokes[1].d : '' }
        }

        ShapePath {
            scale: Qt.size(root.unit, root.unit)
            fillColor: root.fills ? root.color : 'transparent'
            fillRule: ShapePath.WindingFill
            strokeColor: 'transparent'
            strokeWidth: 0
            PathSvg { path: root.fills }
        }
    }
}
