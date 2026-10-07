import "../theme"
import QtQuick

// An original orbital instrument, drawn here rather than importing game art.
Canvas {
    id: root

    property color tint: Tokens.accent
    property int variant: 0

    onTintChanged: requestPaint()
    onVariantChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onPaint: {
        var c = getContext('2d'), s = Math.min(width, height), r = s * 0.4;
        c.reset();
        c.translate(width / 2, height / 2);
        c.strokeStyle = tint;
        c.lineWidth = Math.max(1, s / 110);
        c.globalAlpha = 0.5;
        c.beginPath();
        c.arc(0, 0, r, 0, Math.PI * 2);
        c.stroke();
        c.globalAlpha = 1;
        for (var i = 0; i < 4; i++) {
            c.save();
            c.rotate(i * Math.PI / 2);
            c.beginPath();
            c.moveTo(-s * 0.06, -r);
            c.lineTo(0, -r - s * 0.05);
            c.lineTo(s * 0.06, -r);
            c.stroke();
            c.restore();
        }
        c.save();
        c.rotate(Math.PI / 4);
        c.strokeRect(-r * 0.53, -r * 0.53, r * 1.06, r * 1.06);
        c.restore();
        if (variant % 2 === 0) {
            c.beginPath();
            c.arc(0, 0, r * 0.38, 0, Math.PI * 2);
            c.stroke();
            c.beginPath();
            c.moveTo(-r * 0.75, 0);
            c.lineTo(r * 0.75, 0);
            c.stroke();
        } else {
            c.beginPath();
            c.moveTo(0, -r * 0.54);
            c.lineTo(r * 0.43, r * 0.23);
            c.lineTo(-r * 0.43, r * 0.23);
            c.closePath();
            c.stroke();
        }
        c.fillStyle = tint;
        c.fillRect(-2, -2, 4, 4);
    }
}
