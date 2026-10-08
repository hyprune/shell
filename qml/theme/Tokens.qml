import QtQuick
pragma Singleton

QtObject {
    property bool hudCurved: true
    property real hudCurvature: 0.8
    property string hudConcept: "Vanguard"
    property string hudResource: "gpu"
    property bool worldStyles: true
    property var worldStyle: ({})
    readonly property var skin: worldStyles ? worldStyle : ({})
    function skinColor(key,fallback) { return skin.colors && skin.colors[key] ? skin.colors[key] : fallback; }
    property color hudAccent: skinColor('accent',hudConcept === 'Instrument' ? '#8be0df' : hudConcept === 'Minimal' ? '#ecede4' : '#dfbd68')
    property color hudTile: skinColor('tile',hudConcept === 'Instrument' ? '#207e91' : hudConcept === 'Minimal' ? '#506773' : '#177e88')
    property color hudWhite: skinColor('foreground','#f6f5ea')
    property color hudMuted: skinColor('muted','#c5d2d2')
    readonly property color hudOutline: skinColor('outline','#081118')
    readonly property color hudScrim: skinColor('scrim','#101820')
    readonly property string hudCorners: skin.corners || 'square'
    readonly property string hudWarp: skin.warp || 'default'
    readonly property string hudFont: skin.font && skinFont.status === FontLoader.Ready ? skinFont.name : sans
    property FontLoader skinFont: FontLoader {}
    onSkinChanged: { if (skin.font) skinFont.source=skin.font; }
    Behavior on hudAccent { ColorAnimation { duration: Tokens.reducedMotion ? 0 : 420 } }
    Behavior on hudTile { ColorAnimation { duration: Tokens.reducedMotion ? 0 : 420 } }
    Behavior on hudWhite { ColorAnimation { duration: Tokens.reducedMotion ? 0 : 420 } }
    Behavior on hudMuted { ColorAnimation { duration: Tokens.reducedMotion ? 0 : 420 } }
    property bool light: false
    property bool reducedMotion: false
    property bool warpSoundEnabled: false
    readonly property color mission: '#456fae'
    readonly property color violet: '#b7a4de'
    readonly property color ink: light ? '#eff3ed' : '#0b1420'
    readonly property color panel: light ? '#e2e8e0' : '#122130'
    readonly property color raised: light ? '#d1ddd3' : '#1c3044'
    readonly property color line: light ? '#82938b' : '#3a5068'
    readonly property color text: light ? '#152e32' : '#f1f4fb'
    readonly property color muted: light ? '#455d59' : '#afbed1'
    readonly property color accent: light ? '#006957' : '#d7e6fa'
    readonly property color gold: light ? '#925211' : '#dec89a'
    readonly property string sans: 'DejaVu Sans'
    readonly property string mono: 'DejaVu Sans Mono'
    // Logical pixels: the compositor handles output scale, not a 1080p bitmap.
    readonly property int caption: 11
    readonly property int body: 14
    readonly property int title: 28
    readonly property int space: 8
    readonly property int gutter: 20
    readonly property int radius: 4
    readonly property int motion: reducedMotion ? 0 : 180
}
