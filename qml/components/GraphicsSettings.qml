import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../theme"
import "PerformanceText.js" as PerformanceText
ColumnLayout {
    id:root
    property var graphics:ShellState.graphics
    readonly property var config:graphics ? graphics.config : ({})
    readonly property var effective:graphics ? graphics.effective : ({})
    readonly property var performance: graphics && graphics.performance ? graphics.performance : null
    readonly property var timings:graphics && graphics.timings ? graphics.timings : ({})
    // IPC 0.18: null cap = automatic (profile ceiling, or a share of the GPU's limit) and an
    // offload_device; older cores keep the 20-100 W slider.
    readonly property bool deviceAware: config.offload_device !== undefined
    readonly property var offloadDevice: performance && performance.device ? performance.device : null
    readonly property real capMax: deviceAware ? Math.max(100, Math.min(1000, (offloadDevice && offloadDevice.enforcedLimitW) || 350)) : 100
    // IPC 0.16: FSR 1 / bilinear reconstruction below output size.
    readonly property bool upscalerSupported:ShellState.supportsProtocol(16) && !!(graphics && graphics.options && graphics.options.upscaler)
    readonly property var inherited:['msaa','bloom','fog','sky','reflections','normal_maps','specular','ambient_occlusion','alpha_haze','anisotropy'].concat(config.outline !== undefined ? ['outline'] : []).concat(config.outline_quality !== undefined ? ['outline_quality','outline_width_px','outline_colour'] : []).concat(upscalerSupported ? ['upscaler'] : [])
    readonly property var labels:({quality:'Preset',sky:'Sky',msaa:'MSAA',bloom:'Bloom',fog:'Fog',reflections:'Reflections',normal_maps:'Normal maps',specular:'Specular highlights',ambient_occlusion:'Ambient occlusion',alpha_haze:'Glass / haze',anisotropy:'Anisotropy',dynamic_resolution:'Dynamic resolution'})
    property var pendingPatch:({})
    spacing:12
    function label(v){return v === null ? 'Preset' : v === true ? 'On' : v === false ? 'Off' : String(v).replace(/_/g,' ').replace(/^./,c=>c.toUpperCase());}
    function values(key){return graphics && graphics.options[key] ? (inherited.indexOf(key)>=0 ? [null] : []).concat(graphics.options[key]) : [];}
    function setValue(key,value){var p=Object.assign({},pendingPatch);p[key]=value;pendingPatch=p;commit.restart();}
    function cost(key){return PerformanceText.effectCost(performance,timings,key);}
    Timer {id:commit;interval:120;onTriggered:{ShellState.action('graphics.set',{patch:root.pendingPatch});root.pendingPatch=({});}}
    HudLabel {Layout.fillWidth:true;text:'Live changes · saved automatically';color:Tokens.muted;font.pixelSize:12}
    RowLayout {
        Layout.fillWidth:true
        HudLabel {text:'Preset';Layout.fillWidth:true;font.pixelSize:20}
        HudLabel {Layout.preferredWidth:230;wrapMode:Text.Wrap;color:Tokens.gold;text:!root.graphics ? 'Waiting for core' : root.performance && root.performance.preset === 'custom' ? 'Custom · '+root.label(root.config.quality)+' base' : root.inherited.some(k=>root.config[k]!==null && root.config[k]!==undefined) ? 'Custom · '+root.label(root.config.quality)+' base' : root.config.quality==='auto' ? 'Auto · '+root.label(root.effective.quality) : root.label(root.config.quality)}
        Choice {objectName:'graphics-quality';Layout.preferredWidth:220;model:root.values('quality').map(root.label);currentIndex:root.values('quality').indexOf(root.config.quality);enabled:ShellState.available('graphics.set');onActivated:{root.setValue('quality',root.values('quality')[currentIndex]);root.inherited.forEach(k=>root.setValue(k,null));}}
    }
    GridLayout {
        Layout.fillWidth:true
        columns:root.width>=1400 ? 2 : 1
        columnSpacing:32;rowSpacing:24;uniformCellWidths:true
        ColumnLayout {
            Layout.fillWidth:true;Layout.minimumWidth:0;Layout.alignment:Qt.AlignTop;spacing:12
    Rectangle {Layout.fillWidth:true;height:1;color:Tokens.line}
    HudLabel {text:'RENDERER';color:Tokens.gold;font.pixelSize:Tokens.caption;Layout.fillWidth:true;font.letterSpacing:1.5}
    RowLayout {
        Layout.fillWidth:true
        ColumnLayout {
            Layout.fillWidth:true
            HudLabel {Layout.fillWidth:true;text:root.performance && root.performance.activeRenderer === 'offload' ? ((root.performance.workerTimings || {}).renderer || 'NVIDIA · Offload') : root.timings.renderer || 'Renderer unavailable';wrapMode:Text.Wrap}
            HudLabel {Layout.fillWidth:true;text:'Power draw '+(root.performance && typeof root.performance.powerW === 'number' ? root.performance.powerW.toFixed(1)+' W' : '—')+'   /   Profile '+(root.performance ? ({'usb-c':'USB-C','full-ac':'AC power','limited-ac':'Limited AC','battery':'Battery','unknown':'Unknown'})[root.performance.profile] : 'unavailable')+(root.performance && root.performance.targetFPS>0 ? '   /   Offload ceiling '+root.performance.targetFPS+' FPS' : '');color:Tokens.muted;font.pixelSize:12;wrapMode:Text.Wrap}
        }
        Choice {objectName:'graphics-offload';Layout.preferredWidth:220;model:['Offload · Off','Offload · Auto','Offload · On'];enabled:root.values('offload').length>0 && ShellState.available('graphics.set');currentIndex:Math.max(0,['off','auto','on'].indexOf(root.config.offload));onActivated:root.setValue('offload',['off','auto','on'][currentIndex])}
    }
    HudLabel {Layout.fillWidth:true;text:PerformanceText.policy(root.performance);wrapMode:Text.Wrap;color:Tokens.muted;font.pixelSize:12}
    Rectangle {Layout.fillWidth:true;height:1;color:Tokens.line}
    RowLayout {
        Layout.fillWidth:true;visible:root.config.offload_power_cap_w!==undefined
        HudLabel {Layout.preferredWidth:190;text:'Power cap';wrapMode:Text.Wrap}
        Choice {objectName:'graphics-offload_power_cap_mode';Layout.preferredWidth:180;visible:root.deviceAware;model:['Cap · Automatic','Cap · Custom'];enabled:ShellState.available('graphics.set');currentIndex:root.config.offload_power_cap_w===null ? 0 : 1;onActivated:root.setValue('offload_power_cap_w',currentIndex===0 ? null : Math.round(Math.max(20,Math.min(root.capMax,(root.performance && root.performance.capW) || 80))))}
        SettingSlider {objectName:'graphics-offload_power_cap_w';Layout.fillWidth:true;visible:!root.deviceAware || root.config.offload_power_cap_w!==null;from:20;to:root.capMax;stepSize:root.capMax>100 ? 5 : 1;value:root.config.offload_power_cap_w || 80;enabled:ShellState.available('graphics.set');onMoved:root.setValue('offload_power_cap_w',Math.round(value))}
        Item {Layout.fillWidth:true;visible:root.deviceAware && root.config.offload_power_cap_w===null}
        HudLabel {Layout.preferredWidth:180;text:(root.config.offload_power_cap_w===null ? 'Automatic' : (root.config.offload_power_cap_w || 80)+' W requested')+(root.performance ? ' / '+root.performance.capW+' W policy' : '');font.pixelSize:12;wrapMode:Text.Wrap}
    }
    RowLayout {
        Layout.fillWidth:true;visible:root.deviceAware && root.offloadDevice!==null
        HudLabel {Layout.preferredWidth:190;text:'Offload GPU';wrapMode:Text.Wrap}
        HudLabel {Layout.fillWidth:true;wrapMode:Text.Wrap;font.pixelSize:12;color:Tokens.muted;text:root.offloadDevice ? (root.offloadDevice.name || 'GPU')+' · '+root.offloadDevice.pci+(root.offloadDevice.drivesCompositor ? ' · also drives the display' : '')+(typeof root.offloadDevice.enforcedLimitW==='number' ? ' · '+Math.round(root.offloadDevice.enforcedLimitW)+' W limit' : '') : ''}
        Choice {objectName:'graphics-offload_device';Layout.preferredWidth:180;model:['GPU · Automatic','GPU · Pin this one'];enabled:ShellState.available('graphics.set');currentIndex:root.config.offload_device==='auto' ? 0 : 1;onActivated:root.setValue('offload_device',currentIndex===0 || !root.offloadDevice ? 'auto' : root.offloadDevice.pci)}
    }
    HudLabel {text:'FRAME RATE & RESOLUTION';color:Tokens.gold;font.pixelSize:Tokens.caption;Layout.fillWidth:true;font.letterSpacing:1.5}
    Repeater {
        model:[{key:'target_fps',name:'Target FPS',min:30,max:240,step:1},{key:'sharpen',name:'Sharpening',min:0,max:1,step:.05}]
        RowLayout {
            required property var modelData
            Layout.fillWidth:true
            HudLabel {Layout.preferredWidth:190;text:modelData.name;wrapMode:Text.Wrap}
            SettingSlider {objectName:'graphics-'+modelData.key;Layout.fillWidth:true;from:modelData.min;to:modelData.max;stepSize:modelData.step;value:root.config[modelData.key] || from;enabled:ShellState.available('graphics.set');onMoved:root.setValue(modelData.key,modelData.step===1 ? Math.round(value) : value)}
            HudLabel {Layout.preferredWidth:180;text:(root.config[modelData.key] === undefined ? '—' : Number(root.config[modelData.key]).toFixed(modelData.step===1 ? 0 : 2))+(modelData.key==='sharpen' ? (root.cost('sharpen') ? ' / '+root.cost('sharpen') : '') : ' FPS');horizontalAlignment:Text.AlignRight;font.pixelSize:12}
        }
    }
    RowLayout {
        Layout.fillWidth:true;visible:root.upscalerSupported
        HudLabel {Layout.fillWidth:true;text:'Upscaler';wrapMode:Text.Wrap}
        HudLabel {Layout.preferredWidth:180;text:PerformanceText.upscaler(root.timings.upscaler);color:Tokens.muted;font.pixelSize:12;wrapMode:Text.Wrap}
        Choice {objectName:'graphics-upscaler';Layout.preferredWidth:220;model:root.values('upscaler').map(v=>PerformanceText.upscalerName(v));currentIndex:root.values('upscaler').indexOf(root.config.upscaler === undefined ? null : root.config.upscaler);enabled:ShellState.available('graphics.set');onActivated:root.setValue('upscaler',root.values('upscaler')[currentIndex])}
    }
    Repeater {
        model:['dynamic_resolution','msaa']
        RowLayout {
            required property string modelData
            Layout.fillWidth:true
            HudLabel {Layout.fillWidth:true;text:root.labels[modelData];wrapMode:Text.Wrap}
            HudLabel {Layout.preferredWidth:180;text:modelData==='msaa' ? root.cost('msaa') : 'Active: '+root.label(root.effective[modelData]);color:Tokens.muted;font.pixelSize:12}
            Choice {objectName:'graphics-'+modelData;Layout.preferredWidth:220;model:root.values(modelData).map(root.label);currentIndex:root.values(modelData).indexOf(root.config[modelData]);enabled:ShellState.available('graphics.set');onActivated:root.setValue(modelData,root.values(modelData)[currentIndex])}
        }
    }
    RowLayout {
        Layout.fillWidth:true
        HudLabel {Layout.fillWidth:true;text:root.config.dynamic_resolution ? 'Scale ceiling' : 'Fixed render scale';wrapMode:Text.Wrap}
        HudLabel {Layout.preferredWidth:180;text:HudData.renderScale>=0 ? 'Live: '+Math.round(HudData.renderScale*100)+'%' : 'Live: —';color:Tokens.muted;font.pixelSize:12}
        Choice {objectName:'graphics-render_scale';property var values:['auto',.375,.5,.625,.75,.875,1];Layout.preferredWidth:220;model:values.map(v=>v==='auto' ? 'Automatic' : Math.round(v*100)+'%');currentIndex:values.indexOf(root.config.render_scale);enabled:ShellState.available('graphics.set');onActivated:root.setValue('render_scale',values[currentIndex])}
    }
    Repeater {
        model:root.config.dynamic_resolution===true && root.config.scale_min!==undefined ? ['scale_min','scale_max'] : []
        RowLayout {
            required property string modelData;Layout.fillWidth:true
            HudLabel {Layout.preferredWidth:190;text:modelData==='scale_min' ? 'Minimum scale' : 'Maximum scale'}
            SettingSlider {objectName:'graphics-'+modelData;Layout.fillWidth:true;from:modelData==='scale_max' ? root.config.scale_min : .375;to:modelData==='scale_min' ? root.config.scale_max : 1;stepSize:.025;value:root.config[modelData];enabled:ShellState.available('graphics.set');onMoved:root.setValue(modelData,value)}
            HudLabel {Layout.preferredWidth:180;text:Math.round(root.config[modelData]*100)+'%';horizontalAlignment:Text.AlignRight;font.pixelSize:12}
        }
    }
    HudLabel {Layout.fillWidth:true;visible:root.config.dynamic_resolution===true && root.config.scale_min===undefined;text:'Dynamic scale limits are managed by core.';wrapMode:Text.Wrap;color:Tokens.muted;font.pixelSize:12}
    Rectangle {Layout.fillWidth:true;height:1;color:Tokens.line}
        }
        ColumnLayout {
            Layout.fillWidth:true;Layout.minimumWidth:0;Layout.alignment:Qt.AlignTop;spacing:12
            Rectangle {Layout.fillWidth:true;height:1;color:Tokens.line}
    HudLabel {text:'EFFECTS';color:Tokens.gold;font.pixelSize:Tokens.caption;Layout.fillWidth:true;font.letterSpacing:1.5}
    HudLabel {Layout.fillWidth:true;text:PerformanceText.worldShading(root.performance,root.timings,root.labels);wrapMode:Text.Wrap;color:Tokens.muted;font.pixelSize:12}
    Repeater {
        model:['anisotropy','bloom','fog','alpha_haze','ambient_occlusion','normal_maps','reflections','sky','specular']
        RowLayout {
            required property string modelData
            Layout.fillWidth:true
            HudLabel {Layout.fillWidth:true;text:root.labels[modelData];wrapMode:Text.Wrap}
            HudLabel {Layout.preferredWidth:180;text:root.cost(modelData);color:Tokens.accent;font.pixelSize:12;font.family:Tokens.mono}
            HudLabel {Layout.preferredWidth:110;text:'Active: '+root.label(root.effective[modelData]);color:Tokens.muted;font.pixelSize:11}
            Choice {objectName:'graphics-'+modelData;Layout.preferredWidth:220;model:root.values(modelData).map(root.label);currentIndex:root.values(modelData).indexOf(root.config[modelData]);enabled:ShellState.available('graphics.set');onActivated:root.setValue(modelData,root.values(modelData)[currentIndex])}
        }
    }
    InkSettings { Layout.fillWidth:true; graphics:root.graphics; onGraphicsPatch:patch => { Object.keys(patch).forEach(k=>root.setValue(k,patch[k])); } }
    HudLabel {Layout.fillWidth:true;text:'Per-effect costs appear only for separately measured effects. World shading is one shared pass; its cost is not additive.';wrapMode:Text.Wrap;color:Tokens.muted;font.pixelSize:12}
        }
    }
    HudLabel {Layout.fillWidth:true;text:root.graphics ? root.graphics.error || '' : 'Waiting for graphics settings from core.';visible:text!=='';wrapMode:Text.Wrap;color:Tokens.gold;font.pixelSize:12}
}
