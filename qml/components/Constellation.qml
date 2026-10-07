import "../theme"
import QtQuick

Canvas {
    id: root

    property bool planet: false
    property bool nightOnly: false
    readonly property bool paper: Tokens.light && !nightOnly

    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    Connections {target:Tokens;function onLightChanged(){root.requestPaint()}}
    onPaint: {
        var c = getContext('2d'), w = width, h = height;
        c.reset();
        if(w<4 || h<4)return;
        var fill = c.createLinearGradient(0, 0, w, h);
        fill.addColorStop(0, paper?'#eff3ed':'#0b1120');
        fill.addColorStop(0.55, paper?'#e1e7e1':'#152436');
        fill.addColorStop(1, paper?'#eff3ed':'#121421');
        c.fillStyle = fill;
        c.fillRect(0, 0, w, h);
        var haze = c.createRadialGradient(w * 0.7, h * 0.4, 0, w * 0.7, h * 0.4, w * 0.65);
        haze.addColorStop(0, '#253c5770');
        haze.addColorStop(1, '#00253755');
        c.fillStyle = haze;
        c.fillRect(0, 0, w, h);
        c.fillStyle = '#d0e1f5';
        for (var i = 0; i < 220; i++) {
            var x = ((i * 7919 + 73) % 1021) / 1021 * w, y = ((i * 2741 + 43) % 1031) / 1031 * h;
            c.globalAlpha = 0.1 + (i % 7) * 0.07;
            c.fillRect(x, y, i % 17 === 0 ? 2 : 1, i % 17 === 0 ? 2 : 1);
        }
        c.globalAlpha = 0.15;
        c.strokeStyle = '#7c9cba';
        c.lineWidth = 1;
        for (var j = 0; j < 4; j++) {
            c.beginPath();
            c.ellipse(w * 0.7, h * 0.36, h * (0.2 + j * 0.15), h * (0.2 + j * 0.15), 0, 0.2, Math.PI * 1.8);
            c.stroke();
        }
        c.globalAlpha = 0.09;
        for (var k = 0; k < 12; k++) {
            var a = k * Math.PI / 6;
            c.beginPath();
            c.moveTo(w * 0.7, h * 0.36);
            c.lineTo(w * 0.7 + Math.cos(a) * w, h * 0.36 + Math.sin(a) * w);
            c.stroke();
        }
        c.globalAlpha = 1;
        if (planet) {
            var py = h * 1.9, pr = h * 1.48;
            var atmosphere = c.createRadialGradient(w * 0.6, py, pr - 5, w * 0.6, py, pr + 75);
            atmosphere.addColorStop(0, '#668cb480');
            atmosphere.addColorStop(0.3, '#33588b50');
            atmosphere.addColorStop(1, '#00263b50');
            c.fillStyle = atmosphere;
            c.beginPath();
            c.arc(w * 0.6, py, pr + 75, 0, Math.PI * 2);
            c.fill();
            c.fillStyle = '#0b1423';
            c.beginPath();
            c.arc(w * 0.6, py, pr, 0, Math.PI * 2);
            c.fill();
            c.strokeStyle = '#597598';
            c.globalAlpha = 0.2;
            c.stroke();
        }
    }
}
