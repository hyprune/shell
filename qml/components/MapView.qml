import ".."
import "../theme"
import QtQuick

Item {
    id: root

    property bool compact: false
    property var points: ShellState.places
    property string hoverName: ''
    property var selected: null
    readonly property real unit: Math.min(width, height) / (compact ? 60 : 90)

    signal selectedPoint(var point)
    signal travelRequested(var point)

    readonly property var map: ShellState.mapData
    readonly property real mapRatio: blueprint.implicitWidth > 0 ? blueprint.implicitWidth / blueprint.implicitHeight : 0.9
    readonly property real mapWidth: Math.min(width, height * mapRatio)
    readonly property real mapHeight: mapWidth / mapRatio
    function mapped(position) {
        var t = map.worldToMap;
        return [t[0]*position[0]+t[2]*position[2]+t[4], t[1]*position[0]+t[3]*position[2]+t[5]];
    }
    Image {
        id: blueprint
        anchors.fill: parent
        visible: root.map !== null
        source: root.map ? 'data:image/svg+xml,' + encodeURIComponent(root.map.svg) : ''
        fillMode: Image.PreserveAspectFit
        asynchronous: false
    }
    function px(position) {
        return map ? (width-mapWidth)/2 + mapped(position)[0]*mapWidth : width / 2 + position[0] * unit;
    }

    function py(position) {
        return map ? (height-mapHeight)/2 + mapped(position)[1]*mapHeight : height / 2 + position[2] * unit;
    }

    Canvas {
        id: chart
        visible: root.map === null

        anchors.fill: parent
        onPaint: {
            var c = getContext('2d');
            c.reset();
            var w = width, h = height, u = root.unit;
            c.fillStyle = Tokens.ink;
            c.fillRect(0, 0, w, h);
            c.lineWidth = 1;
            c.strokeStyle = Tokens.line;
            c.globalAlpha = 0.36;
            for (var x = w / 2 % (u * 5); x < w; x += u * 5) {
                c.beginPath();
                c.moveTo(x, 0);
                c.lineTo(x, h);
                c.stroke();
            }
            for (var y = h / 2 % (u * 5); y < h; y += u * 5) {
                c.beginPath();
                c.moveTo(0, y);
                c.lineTo(w, y);
                c.stroke();
            }
            c.globalAlpha = 1;
            // An original schematic; no implied geography beyond manifest spawn positions.
            c.translate(w / 2, h / 2);
            c.strokeStyle = Tokens.line;
            c.fillStyle = Tokens.panel;
            c.lineWidth = 2;
            c.beginPath();
            c.arc(0, 0, u * 16, 0, Math.PI * 2);
            c.fill();
            c.stroke();
            c.beginPath();
            c.arc(0, 0, u * 12, 0, Math.PI * 2);
            c.stroke();
            c.strokeStyle = Tokens.accent;
            c.globalAlpha = 0.2;
            for (var i = 0; i < 8; i++) {
                c.save();
                c.rotate(i * Math.PI / 4);
                c.strokeRect(-u * 3, -u * 28, u * 6, u * 9);
                c.beginPath();
                c.moveTo(0, -u * 19);
                c.lineTo(0, -u * 16);
                c.stroke();
                c.restore();
            }
            c.globalAlpha = 0.65;
            c.strokeStyle = Tokens.line;
            c.beginPath();
            c.arc(0, 0, u * 33, Math.PI * 0.08, Math.PI * 1.75);
            c.stroke();
            c.globalAlpha = 0.7;
            c.strokeStyle = Tokens.gold;
            c.setLineDash([3, 7]);
            c.lineWidth = 1;
            if (root.selected) {
                c.beginPath();
                c.moveTo(ShellState.pose[0] * u, ShellState.pose[2] * u);
                c.lineTo(root.selected.position[0] * u, root.selected.position[2] * u);
                c.stroke();
            }
        }
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()

        Connections {
            function onPoseChanged() {
                chart.requestPaint();
            }

            target: ShellState
        }

        Connections {
            function onSelectedChanged() {
                chart.requestPaint();
            }

            target: root
        }

        Connections {
            function onLightChanged() {
                chart.requestPaint();
            }

            target: Tokens
        }

    }

    Repeater {
        model: root.points

        delegate: Item {
            id: marker

            required property var modelData

            x: root.px(modelData.position) - 16
            y: root.py(modelData.position) - 16
            width: 32
            height: 32

            Rectangle {
                anchors.centerIn: parent
                width: root.compact ? 6 : mouse.containsMouse ? 22 : 15
                height: width
                rotation: 45
                radius: 2
                color: root.selected && root.selected.id === marker.modelData.id ? Tokens.gold : Tokens.panel
                border.color: Tokens.accent
                border.width: root.compact ? 1 : 2

                Behavior on width {
                    NumberAnimation {
                        duration: Tokens.motion
                    }

                }

            }

            HudLabel {
                visible: !root.compact && !root.map
                anchors.top: parent.bottom
                anchors.topMargin: 9
                anchors.horizontalCenter: parent.horizontalCenter
                width: Math.min(160, root.width / 3)
                text: marker.modelData.name.toUpperCase()
                font.pixelSize: 11
                font.letterSpacing: 1.8
                color: mouse.containsMouse ? Tokens.accent : Tokens.muted
            }

            MouseArea {
                id: mouse

                anchors.fill: parent
                enabled: !root.compact
                hoverEnabled: true
                onEntered: root.hoverName = marker.modelData.name
                onExited: root.hoverName = ''
                onClicked: {
                    root.selected = marker.modelData;
                    root.selectedPoint(marker.modelData);
                }
                onDoubleClicked: root.travelRequested(marker.modelData)
            }

        }

    }

    Item {
        x: root.px(ShellState.pose) - 9
        y: root.py(ShellState.pose) - 9
        width: 18
        height: 18
        rotation: ShellState.heading

        Canvas {
            anchors.fill: parent
            id:playerGlyph
            Connections{target:Tokens;function onLightChanged(){playerGlyph.requestPaint()}}
            onPaint: {
                var c = getContext('2d');
                c.fillStyle = Tokens.accent;
                c.beginPath();
                c.moveTo(9, 0);
                c.lineTo(16, 17);
                c.lineTo(9, 13);
                c.lineTo(2, 17);
                c.closePath();
                c.fill();
            }
        }

    }

    HudLabel {
        visible: !root.compact
        text: root.map ? 'WORLD MAP' : 'N ↑'
        font.family: Tokens.mono
        font.pixelSize: 12
        color: Tokens.accent

        anchors {
            top: parent.top
            right: parent.right
            margins: 18
        }

    }

    HudLabel {
        visible: !root.compact
        width: parent.width - 150
        text: root.map ? 'PACKAGE BLUEPRINT   /   METERS' : 'LOCAL SCHEMATIC   /   METERS'
        font.family: Tokens.mono
        font.pixelSize: 11
        font.letterSpacing: 1.2
        color: Tokens.muted

        anchors {
            bottom: parent.bottom
            left: parent.left
            margins: 24
        }

    }

    Rectangle {
        visible: !root.compact
        width: root.unit * 10
        height: 1
        color: Tokens.accent

        anchors {
            bottom: parent.bottom
            right: parent.right
            margins: 24
        }

        HudLabel {
            anchors.bottom: parent.top
            anchors.bottomMargin: 8
            anchors.horizontalCenter: parent.horizontalCenter
            text: '10 m'
            font.pixelSize: 11
            color: Tokens.muted
        }

    }

    Rectangle {
        visible: root.hoverName !== ''
        width: Math.min(320, root.width - 32)
        height: 74
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: 20
        color: Tokens.raised
        border.color: Tokens.accent
        radius: 3

        Column {
            anchors.centerIn: parent
            width: parent.width - 24
            spacing: 5

            HudLabel {
                width: parent.width
                text: root.hoverName
                font.pixelSize: 15
            }

            HudLabel {
                width: parent.width
                text: 'Select to inspect location'
                font.pixelSize: 11
                color: Tokens.muted
            }

        }

    }

}
