import QtQuick
import "../theme"
HudLabel {
    color: Tokens.hudWhite
    font.family: Tokens.hudFont
    style: Tokens.skin.stroke && Tokens.skin.stroke.style === 'shadow' ? Text.Raised : Text.Outline
    styleColor: Tokens.hudOutline
    font.weight: Font.Medium
}
