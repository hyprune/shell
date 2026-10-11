import QtQuick
pragma Singleton

QtObject {
    property bool hudCurved: true
    property real hudCurvature: 0.8
    property string hudConcept: "Adventure"
    property string hudResource: "gpu"
    property bool worldStyles: true
    property var worldStyle: ({})
    readonly property var skin: worldStyles ? worldStyle : ({})
    function skinColor(key,fallback) { return skin.colors && skin.colors[key] ? skin.colors[key] : fallback; }
    property color hudAccent: skinColor('accent',hudConcept === 'Instrument' ? '#8be0df' : hudConcept === 'Minimal' ? '#ecede4' : '#dfbd68')
    property color hudTile: skinColor('tile',hudConcept === 'Instrument' ? '#207e91' : hudConcept === 'Minimal' ? '#506773' : '#177e88')
    property color hudWhite: skinColor('foreground','#f6f5ea')
    readonly property color hudForeground: skinColor('foreground','#f6f5ea') // unanimated target of hudWhite
    property color hudMuted: skinColor('muted','#c5d2d2')
    // In-world action feedback (core reticle valid/invalid via overlay.style, IPC 0.19).
    // World HUD styles can't override these yet (hud-style 1 has no such keys).
    readonly property color hudPositive: hudConcept === 'Instrument' ? '#74eec4' : hudConcept === 'Minimal' ? '#9fe3ad' : '#59f299'
    readonly property color hudWarning: hudConcept === 'Instrument' ? '#ffb35c' : hudConcept === 'Minimal' ? '#f2a777' : '#ff9e59'
    // RFC-0012 quests: tracker, toasts and banner accents; also core's overlay questColor (0.21).
    readonly property color hudQuest: '#ffc74d'
    // The same accent on Director panels (readable on Paper).
    readonly property color quest: light ? '#8a5a00' : '#ffc74d'
    // Focus session phases: the chip ring is the accent in work and this colour in breaks.
    readonly property color hudBreak: hudConcept === 'Instrument' ? '#9ad7ff' : hudConcept === 'Minimal' ? '#b9d8ee' : '#8fd3ff'
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
    readonly property color positive: light ? '#1d6b3a' : '#8fdcaa'
    readonly property color warning: light ? '#a63c06' : '#f3a46b'
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
