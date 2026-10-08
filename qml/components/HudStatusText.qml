import QtQuick
import QtQuick.Effects
import "../theme"

// Small labels on unbounded world backgrounds need a contrast floor. Core does
// not expose regional luminance, so use a fixed, tightly fitted feathered scrim.
Item {
    id: root
    property alias text: label.text
    property alias font: label.font
    property alias horizontalAlignment: label.horizontalAlignment
    // Only set by the development-only, verified nested capture endpoint.
    property string probeMode: 'normal'
    readonly property real inkWidth: Math.min(width, label.paintedWidth)
    readonly property real inkLeft: horizontalAlignment === Text.AlignRight ? width - inkWidth : 0
    implicitWidth: label.implicitWidth
    implicitHeight: label.implicitHeight

    Rectangle {
        x: root.inkLeft - 12; y: -8
        width: root.inkWidth + 24; height: root.height + 16
        radius: 8
        color: '#b8000000'
        visible: root.text !== '' && root.probeMode !== 'mask'
        layer.enabled: true
        layer.effect: MultiEffect { blurEnabled: true; blurMax: 12; blur: .7 }
    }
    HudText {
        id: label
        anchors.fill: parent
        visible: root.probeMode !== 'background' && root.probeMode !== 'white-background'
        color: root.probeMode === 'mask' ? '#ffffff' : Tokens.hudWhite
        shadowEnabled: root.probeMode !== 'mask'
    }
    function contrastRegion() {
        var r = label.mapToItem(null, Qt.rect(inkLeft-4, -2, inkWidth+8, height+4));
        var dpr = Screen.devicePixelRatio;
        return {name:objectName, text:text, x:r.x*dpr, y:r.y*dpr,
            width:r.width*dpr, height:r.height*dpr,
            foreground:[Tokens.hudWhite.r*255,Tokens.hudWhite.g*255,Tokens.hudWhite.b*255]};
    }
}
