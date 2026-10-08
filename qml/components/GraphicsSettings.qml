import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"

ColumnLayout {
    id: root
    property var graphics: ShellState.graphics
    readonly property var labels: ({quality:'Quality preset',sky:'Sky',msaa:'Anti-aliasing',bloom:'Bloom',fog:'Fog',reflections:'Environment reflections',normal_maps:'Normal maps',specular:'Specular highlights',ambient_occlusion:'Ambient occlusion',alpha_haze:'Glass and atmospheric haze',anisotropy:'Texture filtering',dynamic_resolution:'Dynamic resolution'})
    readonly property var inherited: ['msaa','bloom','fog','sky','reflections','normal_maps','specular','ambient_occlusion','alpha_haze','anisotropy']
    spacing: 12
    function label(value) { return value === null ? 'Preset' : value === true ? 'On' : value === false ? 'Off' : String(value).replace(/_/g,' ').replace(/^./,c => c.toUpperCase()); }
    property var pendingPatch: ({})
    function setValue(key,value) {
        var patch = Object.assign({}, pendingPatch); patch[key] = value;
        pendingPatch = patch; commit.restart();
    }
    Timer {
        id: commit
        interval: 120
        onTriggered: { ShellState.action('graphics.set',{patch:root.pendingPatch}); root.pendingPatch = ({}); }
    }
    HudLabel { Layout.fillWidth: true; text: 'WORLD GRAPHICS'; color: Tokens.gold; font.pixelSize: Tokens.caption }
    HudLabel { Layout.fillWidth: true; text: 'Changes apply immediately and are saved for future sessions.'; color: Tokens.muted; wrapMode: Text.Wrap; font.pixelSize: 12 }
    Repeater {
        model: root.graphics ? ['quality'].concat(Object.keys(root.graphics.options).filter(k => k !== 'quality')) : []
        delegate: RowLayout {
            id: optionRow
            required property string modelData
            readonly property var values: (root.inherited.indexOf(modelData) >= 0 ? [null] : []).concat(root.graphics.options[modelData])
            Layout.fillWidth: true
            spacing: 16
            HudLabel { Layout.fillWidth: true; Layout.minimumWidth: 0; text: root.labels[optionRow.modelData] || optionRow.modelData; wrapMode: Text.Wrap }
            HudLabel { Layout.preferredWidth: 110; text: 'Active: ' + root.label(root.graphics.effective[optionRow.modelData]); font.pixelSize: 11; color: Tokens.muted }
            Choice {
                objectName: 'graphics-' + optionRow.modelData
                Layout.preferredWidth: 210
                model: optionRow.values.map(root.label)
                currentIndex: optionRow.values.indexOf(root.graphics.config[optionRow.modelData])
                enabled: ShellState.available('graphics.set')
                onActivated: root.setValue(optionRow.modelData, optionRow.values[currentIndex])
            }
        }
    }
    RowLayout {
        Layout.fillWidth: true
        HudLabel { Layout.fillWidth: true; text: 'Render scale'; wrapMode: Text.Wrap }
        Choice {
            readonly property var values: ['auto',.375,.5,.625,.75,.875,1]
            Layout.preferredWidth: 210
            model: values.map(v => v === 'auto' ? 'Automatic' : Math.round(v * 100) + '%')
            currentIndex: root.graphics ? values.indexOf(root.graphics.config.render_scale) : 0
            displayText: currentIndex >= 0 ? currentText : (root.graphics ? Math.round(root.graphics.config.render_scale * 100) + '%' : '')
            enabled: ShellState.available('graphics.set')
            onActivated: root.setValue('render_scale',values[currentIndex])
        }
    }
    Repeater {
        model: [{key:'sharpen',label:'Reconstruction sharpening',min:0,max:1,step:.05},{key:'target_fps',label:'Target frame rate',min:30,max:240,step:1},{key:'fov',label:'Field of view',min:30,max:110,step:1},{key:'exposure',label:'Exposure',min:.01,max:16,step:.01},{key:'bloom_strength',label:'Bloom strength',min:0,max:4,step:.05}]
        delegate: RowLayout {
            required property var modelData
            Layout.fillWidth: true
            HudLabel { Layout.preferredWidth: 170; text: modelData.label; wrapMode: Text.Wrap }
            SettingSlider { Layout.fillWidth: true; from:modelData.min; to:modelData.max; stepSize:modelData.step; value:root.graphics ? root.graphics.config[modelData.key] : from; enabled:ShellState.available('graphics.set'); onMoved: root.setValue(modelData.key, modelData.step === 1 ? Math.round(value) : value) }
            HudLabel { Layout.preferredWidth: 64; horizontalAlignment: Text.AlignRight; text: root.graphics ? Number(root.graphics.config[modelData.key]).toFixed(modelData.step === 1 ? 0 : 2) : ''; font.family: Tokens.mono }
        }
    }
    ActionButton { Layout.fillWidth: true; text: 'World transitions · ' + (root.graphics && root.graphics.config.reduced_motion ? 'Reduced motion' : 'Animated'); onClicked: root.setValue('reduced_motion',!root.graphics.config.reduced_motion) }
    HudLabel { Layout.fillWidth: true; text: 'Screen-space reflections and runtime/contact shadows are not supported. Baked shadows remain part of the world.'; color: Tokens.muted; wrapMode: Text.Wrap; font.pixelSize: 12 }
    HudLabel {
        Layout.fillWidth: true; wrapMode: Text.Wrap; color: Tokens.muted; font.pixelSize: 11
        text: root.graphics && root.graphics.timings ? 'World render: ' + root.graphics.timings.internalSize.join(' × ') + ' / Output: ' + root.graphics.timings.nativeSize.join(' × ') : ''
    }
    HudLabel { Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.graphics ? root.graphics.error : ''; visible: text !== ''; color: Tokens.gold; font.pixelSize: 12 }
}
