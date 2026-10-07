import "../theme"
import QtQuick

Item {
    id: root

    property bool shown: true
    property real travel: 18

    opacity: shown ? 1 : 0
    visible: opacity > 0

    transform: Translate {
        y: root.shown ? 0 : (Tokens.reducedMotion ? 0 : root.travel)

        Behavior on y {
            NumberAnimation {
                duration: Tokens.motion * 2
                easing.type: Easing.OutCubic
            }

        }

    }

    Behavior on opacity {
        NumberAnimation {
            duration: Tokens.motion * 2
            easing.type: Easing.OutCubic
        }

    }

}
