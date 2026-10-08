import QtQuick
pragma Singleton

QtObject {
    property bool hudCurved: true
    property real hudCurvature: 0.6
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
