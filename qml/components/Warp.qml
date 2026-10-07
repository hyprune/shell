import ".."
import "../theme"
import QtQuick
import Quickshell

Item {
    id: root

    property real flight: 0
    property bool activeOutput: true
    property real intensity: 0
    property real shownProgress: ShellState.transition.progress
    readonly property string phase: ShellState.transition.phase
    readonly property bool moving: !Tokens.reducedMotion && ShellState.warpActive && phase !== 'arrived'
    readonly property real speed: phase === 'loading' ? 0.8 : phase === 'departing' ? 0.18 : phase === 'approach' ? 0.7 : 1

    opacity: ShellState.warpActive ? 1 : 0
    clip: true
    onPhaseChanged: {
        if (phase === 'arrived')
            arrival.restart();

    }

    Connections {
        function onWarpStarted(sequence) {
            if (!root.activeOutput)
                return;
            root.flight = 0;
            root.intensity = 0;
            launch.restart();
            var sound = Quickshell.env('HYPRUNE_WARP_SOUND');
            if (Tokens.warpSoundEnabled && sound !== '')
                Quickshell.execDetached(['pw-play', sound]);

        }

        target: ShellState
    }

    NumberAnimation {
        id: launch

        target: root
        property: 'intensity'
        to: 1
        duration: Tokens.reducedMotion ? 0 : 1200
        easing.type: Easing.InCubic
    }

    NumberAnimation {
        id: arrival

        target: root
        property: 'intensity'
        to: 0
        duration: Tokens.reducedMotion ? 0 : 600
        easing.type: Easing.OutCubic
    }

    Timer {
        interval: 16
        repeat: true
        running: root.activeOutput && root.opacity > 0
        onTriggered: {
            root.flight += 0.016 * root.speed;
            stars.requestPaint();
        }
    }

    Constellation {
        anchors.fill: parent
        planet: true
        nightOnly: true
    }

    Canvas {
        id: stars

        anchors.fill: parent
        onPaint: {
            var c = getContext('2d'), w = width, h = height;
            c.reset();
            var cx = w * 0.65, cy = h * 0.39, spread = Math.sqrt(w * w + h * h);
            if (Tokens.reducedMotion)
                return ;

            for (var i = 0; i < 150; i++) {
                var a = ((i * 359 + 17) % 997) / 997 * Math.PI * 2;
                var life = ((root.flight * (0.55 + (i % 11) * 0.028) + ((i * 137) % 1009) / 1009) % 1);
                var radius = Math.pow(life, 2.3) * spread * 0.8 + 12;
                var tail = radius * (0.08 + root.intensity * 0.38) * (phase === 'approach' ? 0.7 : 1);
                var x = cx + Math.cos(a) * radius, y = cy + Math.sin(a) * radius * 0.72;
                var tx = cx + Math.cos(a) * Math.max(0, radius - tail), ty = cy + Math.sin(a) * Math.max(0, radius - tail) * 0.72;
                var alpha = Math.min(0.8, life * life) * root.intensity;
                if (x < -100 || x > w + 100 || y < -100 || y > h + 100)
                    continue;

                c.globalAlpha = alpha * 0.1;
                c.strokeStyle = '#adc8ee';
                c.lineWidth = 7 + life * 5;
                c.beginPath();
                c.moveTo(tx, ty);
                c.lineTo(x, y);
                c.stroke();
                c.globalAlpha = alpha * 0.3;
                c.strokeStyle = '#729bec';
                c.lineWidth = 2.5;
                c.beginPath();
                c.moveTo(tx - 1.4, ty);
                c.lineTo(x - 1.4, y);
                c.stroke();
                c.strokeStyle = '#c79ecb';
                c.beginPath();
                c.moveTo(tx + 1.4, ty);
                c.lineTo(x + 1.4, y);
                c.stroke();
                c.globalAlpha = alpha;
                c.strokeStyle = '#deedff';
                c.lineWidth = 0.7 + life * 0.9;
                c.beginPath();
                c.moveTo(tx, ty);
                c.lineTo(x, y);
                c.stroke();
            }
            c.globalAlpha = 0.14 * root.intensity;
            c.strokeStyle = '#aac9ee';
            c.lineWidth = 1;
            for (var j = 0; j < 4; j++) {
                var r = ((root.flight * 0.13 + j * 0.25) % 1) * h * 0.8;
                c.beginPath();
                c.ellipse(cx, cy, r, r * 0.72, 0, 0, Math.PI * 2);
                c.stroke();
            }
            c.globalAlpha = 1;
            var veil = c.createLinearGradient(0, 0, w * 0.75, 0);
            veil.addColorStop(0, '#e60a101c');
            veil.addColorStop(0.52, '#9e0b1323');
            veil.addColorStop(1, '#000b1323');
            c.fillStyle = veil;
            c.fillRect(0, 0, w, h);
        }
    }

    Seal {
        x: parent.width * 0.65 - 60
        y: parent.height * 0.39 - 60
        width: 120
        height: 120
        opacity: phase === 'arrived' ? 0.7 : 0.26
        rotation: Tokens.reducedMotion ? 0 : root.flight * 3
        tint: "#d7e6fa"
    }

    Reveal {
        x: parent.width * 0.075
        y: parent.height * 0.53
        width: parent.width * 0.75
        height: 250
        shown: ShellState.warpActive

        Column {
            spacing: 24

            HudLabel {
                text: phase === 'arrived' ? 'JUMP COMPLETE' : phase === 'loading' ? 'PREPARING DESTINATION' : 'IN TRANSIT'
                font.pixelSize: 12
                font.letterSpacing: 6
                color: "#d7e6fa"
            }

            HudLabel {
                color:"#f1f4fb"
                text: ShellState.transition.to.name.toUpperCase()
                font.pixelSize: 56
                font.weight: Font.Light
                font.letterSpacing: 8
                width: root.width * 0.8
            }

            HudLabel {
                text: ShellState.transition.to.subtitle.toUpperCase()
                font.pixelSize: 15
                font.letterSpacing: 4
                color: "#afbed1"
            }

        }

    }

    Rectangle {
        x: parent.width * 0.075
        y: parent.height * 0.83
        width: parent.width * 0.85
        height: 1
        color: Tokens.line

        Rectangle {
            width: parent.width * (ShellState.transition.indeterminate ? 0.08 : root.shownProgress)
            height: 2
            color: "#d7e6fa"
        }

        HudLabel {
            anchors.top: parent.bottom
            anchors.topMargin: 22
            text: phase === 'arrived' ? 'DESTINATION REACHED' : phase === 'loading' ? 'WAITING FOR CORE READINESS' : phase === 'departing' ? 'ESTABLISHING JUMP VECTOR' : phase === 'approach' ? 'APPROACHING DESTINATION' : 'CROSSING THE QUIET'
            font.pixelSize: 10
            font.letterSpacing: 3
            color: "#afbed1"
        }

        HudLabel {
            anchors.right: parent.right
            anchors.top: parent.bottom
            anchors.topMargin: 20
            text: ShellState.transition.indeterminate ? 'LOADING' : Math.round(root.shownProgress * 100) + ' %'
            font.family: Tokens.mono
            font.pixelSize: 15
            font.letterSpacing: 3
            color: "#d7e6fa"
        }

    }

    HudLabel {
        x: parent.width * 0.075
        y: parent.height * 0.08
        text: 'H Y P R U N E   /   LOCATION TRANSIT'
        font.pixelSize: 11
        font.letterSpacing: 3
        color: "#afbed1"
    }

    HudLabel {
        text: ShellState.presentation.dev ? 'SDK MOCK / IPC 0.2' : ''
        font.pixelSize: 9
        font.letterSpacing: 2
        color: "#afbed1"

        anchors {
            right: parent.right
            bottom: parent.bottom
            margins: 48
        }

    }

    Behavior on opacity {
        NumberAnimation {
            duration: Tokens.reducedMotion ? 100 : 340
            easing.type: Easing.InOutSine
        }

    }

    Behavior on shownProgress {
        NumberAnimation {
            duration: Tokens.reducedMotion ? 0 : 320
            easing.type: Easing.OutCubic
        }

    }

}
