import ".."
import "../theme"
import "../Blueprint.js" as Blueprint
import "../Quests.js" as Quests
import QtQuick
import QtQuick.Layouts

Item {
    id: root
    objectName: 'mapView'

    property bool compact: false
    property var points: ShellState.places
    property string hoverName: ''
    property var selected: null
    readonly property real unit: Math.min(width, height) / (compact ? 60 : 90)

    signal selectedPoint(var point)
    signal travelRequested(var point)

    readonly property var map: ShellState.mapData
    // IPC 0.20 blueprint levels: auto-follow the player's feet until the user picks one.
    readonly property var levels: map && map.levels ? map.levels : []
    property string pickedLevel: ''
    onLevelsChanged: { if (pickedLevel && !levels.some(l => l.id === pickedLevel)) pickedLevel = ''; }
    readonly property int autoLevel: Blueprint.levelFor(levels, ShellState.pose[1])
    readonly property int levelIndex: Blueprint.shownLevel(levels, pickedLevel, ShellState.pose[1])
    readonly property var level: levelIndex >= 0 ? levels[levelIndex] : null
    // Themed data URLs are cached per level content and theme colours; never rebuilt per frame.
    // The colours are binding inputs (not read inside) so a theme switch never sees stale tokens.
    readonly property var themeColours: ({text: String(Tokens.text), muted: String(Tokens.muted), accent: String(Tokens.accent),
        gold: String(Tokens.gold), line: String(Tokens.line), ink: String(Tokens.ink), positive: String(Tokens.positive), warning: String(Tokens.warning)})
    property var sourceCache: ({})
    function levelSource(level, colours) {
        var key = level.sha256 + JSON.stringify(colours);
        if (sourceCache[key] === undefined) {
            if (Object.keys(sourceCache).length > 24) sourceCache = ({});
            sourceCache[key] = Blueprint.dataUrl(level.svg, Blueprint.palette(colours));
        }
        return sourceCache[key];
    }
    readonly property string themedLevel: level ? levelSource(level, themeColours) : ''
    readonly property bool showingLevel: themedLevel !== ''
    readonly property string overviewSource: map ? 'data:image/svg+xml,' + encodeURIComponent(map.svg) : ''
    readonly property real mapRatio: map ? Blueprint.viewBoxRatio(map.svg, 0.9) : 0.9

    // Pan (pixels, map centre from view centre) and zoom (1 = whole map in view).
    property real zoom: 1
    property real panX: 0
    property real panY: 0
    readonly property bool interactive: map !== null && !compact
    function setView(nextZoom, nextPan) {
        zoom = Blueprint.clampZoom(nextZoom);
        var p = Blueprint.clampPan(nextPan, zoom, mapWidth, mapHeight);
        panX = p[0]; panY = p[1];
    }
    function zoomBy(factor, x, y) {
        var at = x === undefined ? [0, 0] : [x - width / 2, y - height / 2];
        var next = Blueprint.zoomAt([panX, panY], zoom, zoom * factor, at);
        setView(next.zoom, next.pan);
    }
    function resetView() { setView(1, [0, 0]); }
    // Centre the view on a world position (the player), zooming in to at least 2x.
    function centreOn(position, minZoom) {
        if (!map) return;
        var z = Blueprint.clampZoom(Math.max(zoom, minZoom || 2)), m = mapped(position);
        setView(z, [mapWidth * z * (0.5 - m[0]), mapHeight * z * (0.5 - m[1])]);
    }
    onMapChanged: resetView()
    Connections {
        target: ShellState
        function onMapFocusChanged() { if (ShellState.mapFocus && !root.compact) Qt.callLater(() => root.centreOn(ShellState.mapFocus.position, 2)); }
    }

    readonly property real mapWidth: Math.min(width, height * mapRatio)
    readonly property real mapHeight: mapWidth / mapRatio
    readonly property real drawWidth: mapWidth * zoom
    readonly property real drawHeight: mapHeight * zoom
    readonly property real originX: (width - drawWidth) / 2 + panX
    readonly property real originY: (height - drawHeight) / 2 + panY
    readonly property real pxPerMeter: map ? Math.hypot(map.worldToMap[0] * drawWidth, map.worldToMap[1] * drawHeight) : unit
    readonly property var scaleBar: Blueprint.scaleBar(pxPerMeter)

    function mapped(position) {
        var t = map.worldToMap;
        return [t[0]*position[0]+t[2]*position[2]+t[4], t[1]*position[0]+t[3]*position[2]+t[5]];
    }
    function px(position) {
        return map ? originX + mapped(position)[0] * drawWidth : width / 2 + position[0] * unit;
    }
    function py(position) {
        return map ? originY + mapped(position)[1] * drawHeight : height / 2 + position[2] * unit;
    }
    // Places and the player on another level than the one shown are dimmed.
    function onShownLevel(position) {
        return !showingLevel || Blueprint.levelFor(levels, position[1]) === levelIndex;
    }

    Rectangle {
        anchors.fill: parent
        visible: root.showingLevel
        color: Tokens.ink
    }

    // Drag pans, wheel and pinch zoom about the pointer. Markers above take their own clicks.
    MouseArea {
        id: panArea
        anchors.fill: parent
        enabled: root.interactive
        property point last
        cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
        onPressed: (mouse) => last = Qt.point(mouse.x, mouse.y)
        onPositionChanged: (mouse) => {
            root.setView(root.zoom, [root.panX + mouse.x - last.x, root.panY + mouse.y - last.y]);
            last = Qt.point(mouse.x, mouse.y);
        }
        onDoubleClicked: (mouse) => root.zoomBy(2, mouse.x, mouse.y)
        onWheel: (wheel) => {
            var steps = (wheel.angleDelta.y || wheel.pixelDelta.y / 8) / 120;
            if (steps) root.zoomBy(Math.pow(1.25, steps), wheel.x, wheel.y);
        }
    }

    PinchHandler {
        id: pinch
        target: null
        enabled: root.interactive
        property real startZoom: 1
        onActiveChanged: { if (active) startZoom = root.zoom; }
        onActiveScaleChanged: root.zoomBy(startZoom * activeScale / root.zoom, centroid.position.x, centroid.position.y)
    }

    Item {
        anchors.fill: parent
        clip: true

        Image {
            id: blueprint
            visible: root.map !== null
            x: root.originX
            y: root.originY
            width: root.drawWidth
            height: root.drawHeight
            source: root.showingLevel ? root.themedLevel : root.overviewSource
            // Re-rasterised only at zoom steps (1, 2, 4, 8), capped at 4096 px.
            sourceSize.width: Math.min(4096, Math.ceil(root.mapWidth * Math.pow(2, Math.ceil(Math.log(root.zoom) / Math.LN2 - 0.01))))
            fillMode: Image.Stretch
            smooth: true
            asynchronous: false
        }
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
                if (chart.visible) chart.requestPaint();
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

    Item {
        anchors.fill: parent
        clip: true

        Repeater {
            model: root.points

            delegate: Item {
                id: marker

                required property var modelData

                x: root.px(modelData.position) - 16
                y: root.py(modelData.position) - 16
                width: 32
                height: 32
                opacity: root.onShownLevel(modelData.position) ? 1 : 0.35

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

        // RFC-0012 map markers: core's resolved markers on the shown level, styled like the
        // world markers (tier 1 ringed and labelled, homes labelled, tracked on top).
        Repeater {
            model: root.compact || !root.map ? [] : Quests.mapMarkers(ShellState.markersState, root.showingLevel ? root.levelIndex : -1,
                                                                        y => Blueprint.levelFor(root.levels, y))
            delegate: Item {
                id: guide
                required property var modelData
                readonly property color tone: modelData.role === 'quest' ? Tokens.quest : modelData.role === 'accent' ? Tokens.accent : Tokens.muted
                objectName: 'mapMarker:' + modelData.id
                opacity: modelData.dim ? 0.4 : 1
                x: root.px(modelData.position) - width / 2
                y: root.py(modelData.position) - height / 2
                width: 32; height: 32
                Rectangle {
                    visible: guide.modelData.ring
                    anchors.centerIn: parent
                    width: guide.modelData.size + 12; height: width; radius: width / 2
                    color: 'transparent'; border.width: guide.modelData.tracked ? 2 : 1.5
                    border.color: guide.modelData.tracked ? Tokens.quest : guide.tone
                }
                Rectangle {
                    anchors.centerIn: parent
                    width: guide.modelData.size; height: width
                    rotation: guide.modelData.shape === 'diamond' ? 45 : 0
                    radius: guide.modelData.shape === 'diamond' ? 2 : 1
                    color: guide.modelData.shape === 'square' ? Tokens.panel : guide.tone
                    border.width: guide.modelData.shape === 'square' ? 2 : 1
                    border.color: guide.modelData.shape === 'square' ? guide.tone : Tokens.ink
                }
                HudLabel {
                    visible: guide.modelData.showLabel && guide.modelData.label !== ''
                    anchors.top: parent.bottom; anchors.topMargin: 2
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: Math.min(180, root.width / 4)
                    horizontalAlignment: Text.AlignHCenter
                    text: guide.modelData.label
                    font.pixelSize: 11
                    color: guide.modelData.tracked ? Tokens.quest : Tokens.text
                }
                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.NoButton
                    onEntered: root.hoverName = guide.modelData.label
                    onExited: root.hoverName = ''
                }
            }
        }

        // Quests > Show on map (RFC-0012): the quest target the view was centred on.
        Item {
            objectName: 'mapQuestFocus'
            readonly property var spot: ShellState.mapFocus
            visible: !root.compact && !!spot && !!root.map
            x: spot ? root.px(spot.position) - 16 : 0
            y: spot ? root.py(spot.position) - 16 : 0
            width: 32; height: 32
            Rectangle { anchors.centerIn: parent; width: 18; height: 18; rotation: 45; radius: 2; color: Tokens.quest; border.color: Tokens.ink; border.width: 2 }
            Rectangle { anchors.centerIn: parent; width: 32; height: 32; radius: 16; color: 'transparent'; border.color: Tokens.quest; border.width: 2 }
            HudLabel {
                anchors.top: parent.bottom; anchors.topMargin: 6
                anchors.horizontalCenter: parent.horizontalCenter
                width: Math.min(220, root.width / 3)
                horizontalAlignment: Text.AlignHCenter
                text: parent.spot ? parent.spot.label : ''
                font.pixelSize: 12
                color: Tokens.text
            }
        }

        // The player: a heading cone and arrow, dimmed when on another level than the one shown.
        Item {
            objectName: 'mapPlayer'
            x: root.px(ShellState.pose) - width / 2
            y: root.py(ShellState.pose) - height / 2
            width: root.compact ? 18 : 80
            height: width
            rotation: ShellState.heading
            opacity: root.onShownLevel(ShellState.pose) ? 1 : 0.45

            Canvas {
                id: playerGlyph
                anchors.fill: parent
                property bool cone: !root.compact
                Connections { target: Tokens; function onLightChanged() { playerGlyph.requestPaint(); } }
                onPaint: {
                    var c = getContext('2d'), s = width / 2;
                    c.reset();
                    c.translate(s, s);
                    if (cone) {
                        var g = c.createRadialGradient(0, 0, 4, 0, 0, s);
                        g.addColorStop(0, Qt.rgba(Tokens.accent.r, Tokens.accent.g, Tokens.accent.b, 0.42));
                        g.addColorStop(1, Qt.rgba(Tokens.accent.r, Tokens.accent.g, Tokens.accent.b, 0));
                        c.fillStyle = g;
                        c.beginPath(); c.moveTo(0, 0); c.arc(0, 0, s, -Math.PI / 2 - 0.5, -Math.PI / 2 + 0.5); c.closePath(); c.fill();
                    }
                    var k = cone ? 1.5 : 1;
                    c.fillStyle = Tokens.accent;
                    c.strokeStyle = Tokens.ink;
                    c.lineWidth = 2;
                    c.beginPath();
                    c.moveTo(0, -9 * k); c.lineTo(7 * k, 8 * k); c.lineTo(0, 4 * k); c.lineTo(-7 * k, 8 * k);
                    c.closePath();
                    c.stroke();
                    c.fill();
                }
            }

        }
    }

    // Overlay legibility over a zoomed drawing.
    Rectangle {
        visible: root.showingLevel && !root.compact
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: 64
        gradient: Gradient {
            GradientStop { position: 0; color: Qt.rgba(Tokens.ink.r, Tokens.ink.g, Tokens.ink.b, 0.85) }
            GradientStop { position: 1; color: Qt.rgba(Tokens.ink.r, Tokens.ink.g, Tokens.ink.b, 0) }
        }
    }
    Rectangle {
        visible: root.showingLevel && !root.compact
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: 72
        gradient: Gradient {
            GradientStop { position: 0; color: Qt.rgba(Tokens.ink.r, Tokens.ink.g, Tokens.ink.b, 0) }
            GradientStop { position: 1; color: Qt.rgba(Tokens.ink.r, Tokens.ink.g, Tokens.ink.b, 0.85) }
        }
    }

    HudLabel {
        visible: !root.compact
        text: root.showingLevel ? 'N ↑   BLUEPRINT' : root.map ? 'WORLD MAP' : 'N ↑'
        font.family: Tokens.mono
        font.pixelSize: 12
        color: Tokens.accent

        anchors {
            top: parent.top
            right: parent.right
            margins: 18
        }

    }

    // Level switcher (IPC 0.20 blueprint): the levels, top to bottom, and Auto.
    Rectangle {
        id: levelPanel
        objectName: 'mapLevels'
        visible: !root.compact && root.levels.length > 0
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: 46
        anchors.rightMargin: 18
        width: 190
        height: levelColumn.implicitHeight + 20
        radius: 3
        color: Tokens.panel
        border.color: Tokens.line
        opacity: 0.96

        ColumnLayout {
            id: levelColumn
            anchors.fill: parent
            anchors.margins: 10
            spacing: 4

            HudLabel {
                text: 'LEVEL'
                font.family: Tokens.mono
                font.pixelSize: 10
                font.letterSpacing: 2
                color: Tokens.gold
                Layout.bottomMargin: 2
            }

            Repeater {
                model: root.levels.map((l, i) => i).reverse()

                delegate: MapButton {
                    required property int modelData
                    readonly property var entry: root.levels[modelData]
                    objectName: 'mapLevel:' + entry.id
                    Layout.fillWidth: true
                    text: entry.name
                    detail: modelData === root.autoLevel ? 'YOU' : ''
                    active: modelData === root.levelIndex
                    onClicked: root.pickedLevel = entry.id
                }
            }

            MapButton {
                objectName: 'mapLevelAuto'
                Layout.fillWidth: true
                Layout.topMargin: 4
                text: root.pickedLevel === '' ? 'Auto · following you' : 'Auto · follow me'
                active: root.pickedLevel === ''
                activeColor: Tokens.gold
                onClicked: root.pickedLevel = ''
            }
        }
    }

    // Zoom: +, −, fit, centre on me.
    Column {
        objectName: 'mapZoom'
        visible: root.interactive
        spacing: 4
        anchors.right: parent.right
        anchors.rightMargin: 18
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 64

        MapButton { width: 36; text: '+'; onClicked: root.zoomBy(1.5); enabled: root.zoom < 8; objectName: 'mapZoomIn' }
        MapButton { width: 36; text: '−'; onClicked: root.zoomBy(1 / 1.5); enabled: root.zoom > 1; objectName: 'mapZoomOut' }
        MapButton { width: 36; text: '⤢'; onClicked: root.resetView(); enabled: root.zoom !== 1 || root.panX !== 0 || root.panY !== 0; objectName: 'mapZoomReset' }
        MapButton { width: 36; text: '◎'; onClicked: root.centreOn(ShellState.pose, 2); objectName: 'mapCentre' }
    }

    component MapButton: Rectangle {
        id: button
        property string text: ''
        property string detail: ''
        property bool active: false
        property color activeColor: Tokens.accent
        signal clicked()
        implicitHeight: 30
        implicitWidth: 36
        radius: 2
        color: active ? activeColor : buttonMouse.containsMouse && enabled ? Tokens.raised : Tokens.panel
        border.color: active ? activeColor : Tokens.line
        opacity: enabled ? 1 : 0.45
        Accessible.role: Accessible.Button
        Accessible.name: text
        HudLabel {
            anchors.left: parent.left
            anchors.right: detailLabel.left
            anchors.leftMargin: button.width > 60 ? 10 : 0
            anchors.verticalCenter: parent.verticalCenter
            horizontalAlignment: button.width > 60 ? Text.AlignLeft : Text.AlignHCenter
            text: button.text
            font.pixelSize: button.width > 60 ? 12 : 16
            color: button.active ? Tokens.ink : Tokens.text
        }
        HudLabel {
            id: detailLabel
            anchors.right: parent.right
            anchors.rightMargin: 6
            anchors.verticalCenter: parent.verticalCenter
            text: button.detail
            font.pixelSize: 9
            color: button.active ? Tokens.ink : Tokens.accent
        }
        MouseArea {
            id: buttonMouse
            anchors.fill: parent
            hoverEnabled: true
            enabled: button.enabled
            onClicked: button.clicked()
        }
    }

    HudLabel {
        visible: !root.compact
        width: parent.width - 260
        text: root.showingLevel ? 'BLUEPRINT   /   ' + root.level.name.toUpperCase() + (root.pickedLevel ? '' : '   /   AUTO') + (root.zoom > 1.01 ? '   /   ×' + root.zoom.toFixed(1) : '')
            : root.map ? 'PACKAGE BLUEPRINT   /   METERS' : 'LOCAL SCHEMATIC   /   METERS'
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
        width: root.map ? root.scaleBar.pixels : root.unit * 10
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
            text: root.map ? Blueprint.meters(root.scaleBar.meters) : '10 m'
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
