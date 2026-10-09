import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "PerformanceText.js" as PerformanceText
ColumnLayout {
    id:root
    property var graphics
    signal graphicsPatch(var patch)
    readonly property bool supported: !!graphics && graphics.config.outline !== undefined
    readonly property var ink: supported && ShellState.outline && ShellState.state && ShellState.outline.worldId === ShellState.state.world.id ? ShellState.outline.style : null
    readonly property bool persistent: supported && graphics.config.outline_quality !== undefined
    readonly property string quality: persistent ? graphics.effective.outline_quality : ''
    readonly property bool editable: !!ink && ShellState.available(persistent ? 'graphics.set' : 'atmosphere.set')
    readonly property real strokeWidth: persistent && graphics.effective.outline_width_px !== null ? graphics.effective.outline_width_px : ink ? ink.widthPx : 2
    readonly property var strokeColour: persistent && graphics.effective.outline_colour ? graphics.effective.outline_colour : ink ? ink.colour : null
    function setInk(patch) {
        if (!persistent) { ShellState.patchOutline(patch); return; }
        var keys={widthPx:'outline_width_px',colour:'outline_colour'}, out={};
        Object.keys(patch).forEach(k=>out[keys[k]]=patch[k]);
        graphicsPatch(out);
    }
    function resetInk() {
        widthCommit.stop();
        graphicsPatch({outline:null,outline_quality:null,outline_width_px:null,outline_colour:null});
        colour.focus=false;
    }
    readonly property var visibilityStats: graphics && graphics.timings.visibility
    function hex(rgb) { return rgb ? '#'+rgb.map(v=>Math.round(v*255).toString(16).padStart(2,'0')).join('') : ''; }
    function applyColour() {
        if (!/^#[0-9a-fA-F]{6}$/.test(colour.text)) return;
        setInk({colour:[1,3,5].map(i=>parseInt(colour.text.slice(i,i+2),16)/255)});
    }
    spacing:12
    Rectangle { Layout.fillWidth:true; height:1; color:Tokens.line }
    HudLabel { text:'INK & VISIBILITY'; Layout.fillWidth:true; color:Tokens.gold; font.pixelSize:Tokens.caption; font.letterSpacing:1.5 }
    HudLabel { visible:!root.supported; Layout.fillWidth:true; text:'Ink controls require core IPC 0.13.'; color:Tokens.muted; wrapMode:Text.Wrap }
    ColumnLayout {
        visible:root.supported; Layout.fillWidth:true; spacing:12
        RowLayout {
            Layout.fillWidth:true
            HudLabel { Layout.fillWidth:true; text:'Ink outlines'; wrapMode:Text.Wrap }
            HudLabel { objectName:'inkCost'; Layout.preferredWidth:180; text:PerformanceText.effectCost(root.graphics && root.graphics.performance,root.graphics ? root.graphics.timings : {},'outline') || 'Timing unavailable'; font.family:Tokens.mono; font.pixelSize:12; color:Tokens.accent }
            Choice { objectName:'graphics-outline'; Layout.preferredWidth:220; model:['Preset','Off','On']; currentIndex:root.supported ? [null,false,true].indexOf(root.graphics.config.outline) : 0; enabled:root.supported && ShellState.available('graphics.set'); onActivated:root.graphicsPatch({outline:[null,false,true][currentIndex]}) }
        }
        HudLabel { Layout.fillWidth:true; text:root.persistent ? 'One shared ink cost for detection and compositing at either quality. On permits the world’s authored style.' : 'Cost includes normal/depth geometry and edge ink. On permits the world’s authored style.'; color:Tokens.muted; font.pixelSize:12; wrapMode:Text.Wrap }
        RowLayout {
            Layout.fillWidth:true
            HudLabel { Layout.fillWidth:true; text:'Ink quality' }
            Choice { objectName:'graphics-outline_quality'; Layout.preferredWidth:220; model:root.persistent ? ['Preset','Fast · 1 px','Smooth · authored width'] : ['Native · geometry edges']; currentIndex:root.persistent ? [null,'fast','smooth'].indexOf(root.graphics.config.outline_quality) : 0; enabled:root.persistent && ShellState.available('graphics.set'); onActivated:{widthCommit.stop();root.graphicsPatch({outline_quality:[null,'fast','smooth'][currentIndex]});} }
        }
        HudLabel { Layout.fillWidth:true; text:root.persistent ? 'Active: '+(root.quality==='fast' ? 'Fast · fixed 1 px. Select Smooth to adjust width.' : 'Smooth · world width or your saved override.') : 'Core 0.13 has one fixed ink quality; no quality override is available.'; color:Tokens.muted; font.pixelSize:12; wrapMode:Text.Wrap }
        RowLayout {
            Layout.fillWidth:true
            HudLabel { Layout.preferredWidth:150; text:'Width'; wrapMode:Text.Wrap }
            SettingSlider { objectName:'graphics-outline_width'; Layout.fillWidth:true; from:1; to:4; stepSize:.25; value:root.strokeWidth; enabled:root.editable && (!root.persistent || root.quality==='smooth'); onMoved:{widthCommit.widthValue=value;widthCommit.worldId=ShellState.state.world.id;widthCommit.restart();} }
            HudLabel { Layout.preferredWidth:110; text:root.ink ? root.strokeWidth.toFixed(2)+' px' : 'No world ink'; font.pixelSize:12 }
        }
        RowLayout {
            Layout.fillWidth:true
            HudLabel { Layout.fillWidth:true; text:'Colour override'; wrapMode:Text.Wrap }
            Rectangle { width:22;height:22; color:root.ink ? root.hex(root.strokeColour) : 'transparent'; border.color:Tokens.line }
            TextField { id:colour; objectName:'graphics-outline_colour'; Layout.preferredWidth:120; enabled:root.editable; placeholderText:'#RRGGBB'; maximumLength:7; color:Tokens.text; placeholderTextColor:Tokens.muted; selectionColor:Tokens.accent; selectedTextColor:Tokens.ink; font.family:Tokens.mono; validator:RegularExpressionValidator { regularExpression:/#[0-9a-fA-F]{6}/ }
                background:Rectangle { color:Tokens.panel; radius:3; border.color:colour.activeFocus ? Tokens.gold : Tokens.line }
                onAccepted:root.applyColour() }
            ActionButton { objectName:'graphics-outline_apply'; text:'Apply'; Layout.preferredWidth:90; implicitWidth:90; enabled:root.editable && colour.acceptableInput; onClicked:root.applyColour() }
            ActionButton { objectName:'graphics-outline_reset'; visible:!root.persistent; text:'Reset colour'; Layout.preferredWidth:120; enabled:root.editable; onClicked:root.setInk({colour:null}) }
        }
        HudLabel { Layout.fillWidth:true; text:root.persistent ? 'Overrides are saved across worlds and restarts. Reset restores world width/colour and preset quality. Worlds must author enabled ink.' : root.ink ? 'Width and colour apply live until world reload. Reset restores the colour first loaded here.' : 'This world has no authored ink style. Width and colour are unavailable.'; wrapMode:Text.Wrap; font.pixelSize:12; color:Tokens.muted }
        ActionButton { objectName:'graphics-outline_defaults'; visible:root.persistent; text:'Reset to world default'; Layout.fillWidth:true; enabled:root.persistent && ShellState.available('graphics.set'); onClicked:root.resetInk() }
        RowLayout {
            Layout.fillWidth:true
            HudLabel { Layout.fillWidth:true; text:'Authored visibility culling'; wrapMode:Text.Wrap }
            Choice { objectName:'graphics-visibility_culling'; Layout.preferredWidth:220; model:['Off','On']; currentIndex:root.supported && root.graphics.config.visibility_culling ? 1 : 0; enabled:root.supported && ShellState.available('graphics.set'); onActivated:root.graphicsPatch({visibility_culling:currentIndex===1}) }
        }
        HudLabel { Layout.fillWidth:true; text:root.visibilityStats ? root.visibilityStats.submitted+' submitted / '+root.visibilityStats.culled+' culled / '+root.visibilityStats.total+' world batches' : 'Visibility counters unavailable'; wrapMode:Text.Wrap; font.pixelSize:12; color:Tokens.muted }
    }
    Binding { target:colour; property:'text'; value:root.hex(root.strokeColour); when:!colour.activeFocus; restoreMode:Binding.RestoreNone }
    Timer { id:widthCommit; property real widthValue:2; property string worldId:''; interval:120; onTriggered:{if(ShellState.state && ShellState.state.world && ShellState.state.world.id===worldId) root.setInk({widthPx:widthValue});} }
}
