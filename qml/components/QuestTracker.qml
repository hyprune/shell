import QtQuick
import ".."
import "../theme"
import "../Quests.js" as Quests

// HUD quest tracker (RFC-0012): the tracked quest, its current step and progress, from
// quests.active[0] while a quest is tracked. Calm mode collapses it to one line.
Item {
    id: root
    objectName: 'hudQuestTracker'
    readonly property var quests: ShellState.questsState
    readonly property var quest: quests && quests.tracked && quests.active && quests.active.length && Quests.sameRef(quests.tracked, {source: quests.active[0].source, id: quests.active[0].id}) ? quests.active[0] : null
    readonly property bool calm: ShellState.focusCalm
    readonly property bool technical: Tokens.hudConcept === 'Instrument'
    readonly property bool minimal: Tokens.hudConcept === 'Minimal'
    readonly property var step: quest ? quest.step : null
    readonly property real share: quest && quest.progress[1] > 0 ? quest.progress[0] / quest.progress[1] : 0
    visible: !!quest
    implicitHeight: calm ? 34 : column.implicitHeight + 20

    HudTile {
        anchors.fill: parent
        color: root.minimal ? '#b013242d' : Qt.rgba(Tokens.hudScrim.r, Tokens.hudScrim.g, Tokens.hudScrim.b, .78)
        borderColor: root.technical ? Tokens.hudQuest : 'transparent'
        borderWidth: root.technical ? 1 : 0
    }
    Rectangle { anchors.right: parent.right; width: root.minimal ? 2 : 4; height: parent.height; color: Tokens.hudQuest }
    // Calm: one line, title and step.
    HudText {
        objectName: 'hudQuestTrackerLine'
        visible: root.calm
        x: 12; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 26
        text: root.quest ? '◆ ' + root.quest.title + (root.step ? '  ·  ' + root.step.title : '') : ''
        font.pixelSize: 12
        color: Tokens.hudMuted
    }
    Column {
        id: column
        visible: !root.calm
        x: 12; y: 10; width: parent.width - 26
        spacing: 5
        HudText {
            width: parent.width
            text: 'TRACKED QUEST'
            font.pixelSize: 10; font.letterSpacing: 1.6
            font.family: root.technical ? Tokens.mono : Tokens.hudFont
            color: Tokens.hudQuest
        }
        HudText {
            objectName: 'hudQuestTitle'
            width: parent.width
            text: root.quest ? root.quest.title : ''
            font.pixelSize: 15
            smallText: false
        }
        HudText {
            objectName: 'hudQuestStep'
            width: parent.width
            visible: !!root.step
            text: root.step ? '▸ ' + root.step.title + (root.step.progress && root.step.progress[1] > 1 ? '   ' + Quests.progressText(root.step.progress) : '') : ''
            font.pixelSize: 12
            color: Tokens.hudMuted
        }
        Item {
            width: parent.width; height: 14
            Rectangle { y: 6; width: parent.width - stepsText.width - 10; height: 3; color: '#5a8a9aa0'
                Rectangle { width: parent.width * root.share; height: parent.height; color: Tokens.hudQuest
                    Behavior on width { NumberAnimation { duration: Tokens.reducedMotion ? 0 : 300 } } }
            }
            HudText {
                id: stepsText
                anchors.right: parent.right
                text: root.quest ? Quests.progressText(root.quest.progress) + ' steps' : ''
                font.pixelSize: 10; font.family: Tokens.mono
                color: Tokens.hudMuted
            }
        }
    }
}
