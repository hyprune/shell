import QtQuick
import "../theme"
// Approximate live preview of the core reticle (core draws the real one at native resolution).
Rectangle {
    id: root
    property string style: 'cross_dot'
    property real size: 18
    property real thickness: 2
    property real gap: 4
    property real reticleOpacity: 0.9
    property bool outline: true
    property color colour: Tokens.hudForeground
    implicitWidth: 132; implicitHeight: 132
    radius: Tokens.radius
    border.color: Tokens.line
    // A neutral world-like backdrop: sky over ground, so the outline reads in both themes.
    gradient: Gradient {
        GradientStop { position: 0; color: '#7d9db4' }
        GradientStop { position: 0.55; color: '#a9b8b0' }
        GradientStop { position: 0.56; color: '#5d6b4f' }
        GradientStop { position: 1; color: '#3e4a37' }
    }
    onStyleChanged: canvas.requestPaint()
    onSizeChanged: canvas.requestPaint()
    onThicknessChanged: canvas.requestPaint()
    onGapChanged: canvas.requestPaint()
    onReticleOpacityChanged: canvas.requestPaint()
    onOutlineChanged: canvas.requestPaint()
    onColourChanged: canvas.requestPaint()
    Canvas {
        id: canvas
        objectName: 'reticlePreview'
        anchors.fill: parent
        onPaint: {
            var c = getContext('2d');
            c.reset();
            var cx = Math.round(width / 2), cy = Math.round(height / 2);
            var half = root.size / 2, gap = Math.min(root.gap, half - 1), t = root.thickness;
            var arms = [], ring = 0, dot = false;
            function arm(dx, dy) { arms.push([cx + dx * gap, cy + dy * gap, cx + dx * half, cy + dy * half]); }
            switch (root.style) {
            case 'cross_dot': arm(1, 0); arm(-1, 0); arm(0, 1); arm(0, -1); dot = true; break;
            case 't_dot': arm(1, 0); arm(-1, 0); arm(0, 1); dot = true; break;
            case 'circle_dot': ring = Math.max(gap + t, half - t / 2); dot = true; break;
            case 'dot': dot = true; break;
            case 'cross': arm(1, 0); arm(-1, 0); arm(0, 1); arm(0, -1); break;
            case 'chevron':
                arms.push([cx - half, cy + half * 0.6 + gap / 2, cx, cy + gap / 2]);
                arms.push([cx, cy + gap / 2, cx + half, cy + half * 0.6 + gap / 2]);
                break;
            }
            function draw(colour, width, grow) {
                c.strokeStyle = colour; c.fillStyle = colour; c.lineWidth = width; c.lineCap = 'butt';
                arms.forEach(function (a) {
                    var dx = Math.sign(a[2] - a[0]) * grow, dy = Math.sign(a[3] - a[1]) * grow;
                    c.beginPath(); c.moveTo(a[0] - dx, a[1] - dy); c.lineTo(a[2] + dx, a[3] + dy); c.stroke();
                });
                if (ring > 0) { c.beginPath(); c.arc(cx, cy, ring, 0, Math.PI * 2); c.stroke(); }
                if (dot) { c.beginPath(); c.arc(cx, cy, Math.max(1, t * 0.75) + grow, 0, Math.PI * 2); c.fill(); }
            }
            c.globalAlpha = root.reticleOpacity;
            if (root.outline) draw(Tokens.hudOutline, t + 2, 1);
            draw(root.colour, t, 0);
        }
    }
}
