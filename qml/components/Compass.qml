import QtQuick
import ".."
import "../theme"
Item {
    id: root
    clip: true
    implicitHeight: 70
    Repeater {
        model: 23
        Item {
            required property int index
            property real degrees: (Math.floor(ShellState.heading/15)*15+(index-11)*15+720)%360
            x: root.width/2+(index-11)*42-(ShellState.heading%15)*42/15
            width: 1; height: 33; visible:x>16 && x<root.width-16
            Rectangle { y: 24; x: -1; width: 3; height: parent.degrees%90 === 0 ? 11 : 6; color: '#c0081118' }
            Rectangle { y: 24; width: 1; height: parent.degrees%90 === 0 ? 10 : 5; color: Tokens.hudWhite }
            HudText { anchors.horizontalCenter: parent.horizontalCenter; y: 1; text: parent.degrees%90 === 0 ? ['N','E','S','W'][parent.degrees/90] : parent.degrees%30 === 0 ? parent.degrees : ''; font.pixelSize: 11; font.letterSpacing: 1 }
        }
    }
    Repeater {
        model: [43,48]
        Rectangle { required property int modelData; x: 12; y: modelData; width: root.width-24; height: 1; color: '#d5dce9e7'; Rectangle { y: 1; width: parent.width; height: 1; color: '#a0081118' } }
    }
    Rectangle { x: 12; y: 43; width: 1; height: 9; color: Tokens.hudWhite }
    Rectangle { x: parent.width-13; y: 43; width: 1; height: 9; color: Tokens.hudWhite }
    Rectangle { anchors.horizontalCenter: parent.horizontalCenter; y: 36; width: 3; height: 15; color: Tokens.hudAccent }
    Repeater {
        model: ShellState.places.concat(ShellState.waypointState && ShellState.waypointState.position ? [{name:ShellState.waypointState.label,position:ShellState.waypointState.position,waypoint:true}] : [])
        Item {
            required property var modelData
            property real bearing: Math.atan2(modelData.position[0]-ShellState.pose[0],-(modelData.position[2]-ShellState.pose[2]))*180/Math.PI
            property real delta: (bearing-ShellState.heading+540)%360-180
            x: root.width/2+delta*42/15; y: 43
            visible: Math.abs(delta) < root.width/2*15/42-3
            Rectangle { x:-3; y:-1; width: 6; height:6; rotation:45; color: modelData.waypoint ? Tokens.hudAccent : '#c0e2ebe7'; border.color:'#c0081118' }
        }
    }
}
