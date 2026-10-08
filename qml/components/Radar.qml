import QtQuick
import ".."
import "../theme"
Item {
    id: root
    property real range: Tokens.hudConcept === 'Instrument' ? 45 : 32
    Canvas {
        id: radar
        anchors.fill: parent
        property string mapSource: ShellState.mapData ? 'data:image/svg+xml,'+encodeURIComponent(ShellState.mapData.svg) : ''
        onMapSourceChanged: { if (mapSource) loadImage(mapSource); requestPaint(); }
        Component.onCompleted: { if (mapSource) loadImage(mapSource); }
        onImageLoaded: requestPaint()
        // Only radar geometry is rasterised; HUD typography stays in the scenegraph.
        onPaint: {
            var c=getContext('2d'), w=canvasSize.width,h=canvasSize.height,r=w/2-4;
            c.reset(); c.clearRect(0,0,w,h); c.save(); c.translate(w/2,h/2);
            c.beginPath(); c.arc(0,0,r,0,Math.PI*2); c.clip();
            c.fillStyle='#70102027'; c.fillRect(-r,-r,2*r,2*r);
            var m=ShellState.mapData, px=ShellState.pose[0],pz=ShellState.pose[2];
            if (m && m.worldToMap && isImageLoaded(mapSource)) {
                var t=m.worldToMap, u=t[0]*px+t[2]*pz+t[4],v=t[1]*px+t[3]*pz+t[5];
                var span=Math.max(.001,Math.abs(t[0])*root.range*2), size=2*r/span;
                c.globalAlpha=.42; c.drawImage(mapSource,-u*size,-v*size,size,size); c.globalAlpha=1;
            }
            c.strokeStyle='#506cb0bc'; c.lineWidth=1.5;
            [r*.5,r-1].forEach(function(rr) { c.beginPath();c.arc(0,0,rr,0,Math.PI*2);c.stroke(); });
            c.beginPath();c.moveTo(-r,0);c.lineTo(r,0);c.moveTo(0,-r);c.lineTo(0,r);c.stroke();
            var yaw=ShellState.heading*Math.PI/180;
            c.fillStyle='#303ee4e0';c.beginPath();c.moveTo(0,0);c.arc(0,0,r,yaw-Math.PI/2-.45,yaw-Math.PI/2+.45);c.closePath();c.fill();
            c.strokeStyle='#a8d8e9e7'; c.lineWidth=2;
            for(var i=0;i<12;i++){var a=i*Math.PI/6;c.beginPath();c.moveTo(Math.cos(a)*(r-8),Math.sin(a)*(r-8));c.lineTo(Math.cos(a)*(r-2),Math.sin(a)*(r-2));c.stroke();}
            ShellState.places.forEach(function(p){var x=(p.position[0]-px)/root.range*r,y=(p.position[2]-pz)/root.range*r;if(x*x+y*y<(r-8)*(r-8)){c.fillStyle='#d7e9e3';c.save();c.translate(x,y);c.rotate(Math.PI/4);c.fillRect(-3,-3,6,6);c.restore();}});
            var wp=ShellState.waypointState; if(wp && wp.position){var pos=wp.position; c.strokeStyle=Tokens.hudAccent;c.lineWidth=3;c.beginPath();c.arc((pos[0]-px)/root.range*r,(pos[2]-pz)/root.range*r,6,0,Math.PI*2);c.stroke();}
            c.rotate(yaw);c.fillStyle='#f5f5e9';c.strokeStyle='#101d29';c.lineWidth=2;c.beginPath();c.moveTo(0,-13);c.lineTo(8,10);c.lineTo(0,6);c.lineTo(-8,10);c.closePath();c.fill();c.stroke();c.restore();
        }
        Connections { target: ShellState; function onPoseChanged(){radar.requestPaint();} function onHeadingChanged(){radar.requestPaint();} function onCorePlacesChanged(){radar.requestPaint();} function onWaypointStateChanged(){radar.requestPaint();} }
    }
    HudText { anchors.top: parent.top; anchors.horizontalCenter: parent.horizontalCenter; text:'N'; font.pixelSize:9 }
}
