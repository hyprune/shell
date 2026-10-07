import QtQuick
import Quickshell
import Quickshell.Wayland

ShellRoot {
    Variants {
        model: Quickshell.screens

        delegate: PanelWindow {
            required property var modelData

            screen: modelData
            exclusionMode: ExclusionMode.Ignore
            WlrLayershell.layer: WlrLayer.Background
            color: '#0d171e'

            anchors {
                left: true
                right: true
                top: true
                bottom: true
            }

            Canvas {
                anchors.fill: parent
                onPaint: {
                    var c = getContext('2d'), w = width, h = height;
                    if(w<2 || h<2)return;
                    var sky = c.createLinearGradient(0, 0, 0, h);
                    sky.addColorStop(0, '#0e1d2c');
                    sky.addColorStop(0.55, '#40555b');
                    sky.addColorStop(1, '#132b31');
                    c.fillStyle = sky;
                    c.fillRect(0, 0, w, h);
                    c.fillStyle = '#a0b9b2';
                    c.globalAlpha = 0.25;
                    for (var i = 0; i < 130; i++) {
                        var sx = ((i * 7919) % 1000) / 1000 * w, sy = ((i * 2741) % 500) / 1000 * h;
                        c.fillRect(sx, sy, i % 7 === 0 ? 2 : 1, 1);
                    }
                    c.globalAlpha = 1;
                    c.strokeStyle = '#839891';
                    c.globalAlpha = 0.25;
                    c.lineWidth = 1;
                    for (var r = 0; r < 5; r++) {
                        c.beginPath();
                        c.ellipse(w * 0.47, h * 0.29, w * (0.09 + r * 0.011), h * (0.15 + r * 0.015), -0.4, 0, Math.PI * 2);
                        c.stroke();
                    }
                    c.globalAlpha = 1;
                    // Original abstract observatory: perspective paving, monoliths and garden beds.
                    c.fillStyle = '#192c33';
                    c.beginPath();
                    c.moveTo(0, h * 0.58);
                    c.lineTo(w * 0.5, h * 0.48);
                    c.lineTo(w, h * 0.56);
                    c.lineTo(w, h);
                    c.lineTo(0, h);
                    c.closePath();
                    c.fill();
                    c.strokeStyle = '#44595c';
                    c.globalAlpha = 0.5;
                    for (var j = -10; j < 12; j++) {
                        c.beginPath();
                        c.moveTo(w * 0.5 + j * 15, h * 0.49);
                        c.lineTo(w * 0.5 + j * 210, h);
                        c.stroke();
                    }
                    for (var k = 1; k < 12; k++) {
                        var y = h * 0.49 + (k * k / 144) * h * 0.51;
                        c.beginPath();
                        c.moveTo(0, y);
                        c.lineTo(w, y);
                        c.stroke();
                    }
                    c.globalAlpha = 1;
                    tower(c, w * 0.25, h * 0.36, w * 0.035, h * 0.26);
                    tower(c, w * 0.31, h * 0.42, w * 0.025, h * 0.16);
                    tower(c, w * 0.67, h * 0.26, w * 0.045, h * 0.36);
                    tower(c, w * 0.77, h * 0.38, w * 0.035, h * 0.27);
                    c.strokeStyle = '#a1baa8';
                    c.lineWidth = 2;
                    c.globalAlpha = 0.35;
                    c.beginPath();
                    c.ellipse(w * 0.5, h * 0.77, w * 0.18, h * 0.085, 0, 0, Math.PI * 2);
                    c.stroke();
                    c.beginPath();
                    c.ellipse(w * 0.5, h * 0.77, w * 0.145, h * 0.06, 0, 0, Math.PI * 2);
                    c.stroke();
                    c.globalAlpha = 1;
                    c.fillStyle = '#152b30';
                    c.beginPath();
                    c.moveTo(0, h * 0.76);
                    c.lineTo(w * 0.2, h * 0.63);
                    c.lineTo(w * 0.34, h * 0.77);
                    c.lineTo(w * 0.18, h);
                    c.lineTo(0, h);
                    c.fill();
                    c.fillStyle = '#203b37';
                    c.beginPath();
                    c.moveTo(w, h * 0.75);
                    c.lineTo(w * 0.84, h * 0.67);
                    c.lineTo(w * 0.7, h * 0.8);
                    c.lineTo(w * 0.88, h);
                    c.lineTo(w, h);
                    c.fill();
                    var vignette = c.createRadialGradient(w * 0.5, h * 0.5, h * 0.15, w * 0.5, h * 0.5, w * 0.6);
                    vignette.addColorStop(0, '#00000000');
                    vignette.addColorStop(1, '#b000080e');
                    c.fillStyle = vignette;
                    c.fillRect(0, 0, w, h);
                }

                function tower(c, x, y, bw, bh) {
                    c.fillStyle = '#243840';
                    c.fillRect(x, y, bw, bh);
                    c.fillStyle = '#1a2c33';
                    c.beginPath();
                    c.moveTo(x + bw, y);
                    c.lineTo(x + bw + 22, y - 15);
                    c.lineTo(x + bw + 22, y + bh - 15);
                    c.lineTo(x + bw, y + bh);
                    c.fill();
                    c.fillStyle = '#587773';
                    c.fillRect(x + 8, y + 12, 2, bh - 25);
                    c.fillStyle = '#718a80';
                    c.fillRect(x, y, bw, 2);
                }

            }

        }

    }

}
