import QtQuick
import QtQuick.Effects
import "../theme"
HudLabel {
    id: root
    property bool smallText: true
    readonly property bool outlined: !!Tokens.skin.stroke && Tokens.skin.stroke.style === 'outline'
    readonly property real rasterScale: {
        var item = parent;
        while (item) {
            if (item.uiScale !== undefined) return item.uiScale * Screen.devicePixelRatio;
            item = item.parent;
        }
        return Screen.devicePixelRatio;
    }
    color: Tokens.hudWhite
    font.family: Tokens.hudFont
    style: outlined ? Text.Outline : Text.Normal
    styleColor: Tokens.hudOutline
    font.weight: !outlined && smallText ? Font.DemiBold : Font.Medium
    // Curve coverage avoids coloured subpixel fringes in transparent textures.
    renderType: outlined ? Text.QtRendering : Text.CurveRendering
    // Blur only the shadow. The solid glyph remains sharp, supersampled before
    // any parent perspective. Explicit world outlines use the native path.
    layer.enabled: !outlined
    layer.textureSize: Qt.size(Math.ceil(width * rasterScale * 2), Math.ceil(height * rasterScale * 2))
    layer.smooth: true
    layer.effect: MultiEffect {
        shadowEnabled: true
        blurMax: 2
        shadowBlur: .75
        shadowOpacity: .5
        shadowColor: Tokens.hudOutline
        shadowHorizontalOffset: 0
        shadowVerticalOffset: .5
    }
}
