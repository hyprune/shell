import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
Item {
    ColumnLayout {
        anchors.fill:parent; spacing:16
        RowLayout {
            Layout.fillWidth:true
            HudLabel { text:'Performance'; font.pixelSize:Tokens.title; Layout.fillWidth:true }
            HudLabel { Layout.maximumWidth:450; text:HudData.stats; font.family:Tokens.mono; color:Tokens.accent; font.pixelSize:13 }
        }
        ScrollView {
            id:scroll; Layout.fillWidth:true; Layout.fillHeight:true; contentWidth:availableWidth; clip:true
            GraphicsSettings { width:Math.min(scroll.availableWidth-20,1800) }
        }
    }
}
