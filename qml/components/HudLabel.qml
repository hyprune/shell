import "../theme"
import QtQuick
import QtQuick.Controls

Text {
    id: root
    // Passive HoverHandler does not consume clicks or affect HUD input regions.
    HoverHandler { id: hover }
    ToolTip.visible: truncated && hover.hovered
    ToolTip.text: text
    ToolTip.delay: 500
    ToolTip.timeout: 10000
    color: Tokens.text
    font.family: Tokens.sans
    font.pixelSize: Tokens.body
    font.letterSpacing: 0.2
    // Reserve the final glyph bearing at fractional output/UI scales.
    rightPadding: 4
    elide: Text.ElideRight
    textFormat: Text.PlainText
}
