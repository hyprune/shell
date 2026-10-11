pragma Singleton
import QtQuick
import "theme"
import "HudInteraction.js" as Interaction
import "HudManipulation.js" as Manipulation
import "components/PerformanceText.js" as PerformanceText
QtObject {
    readonly property var manipulation: ShellState.dev && ShellState.manipulationPreview ? ShellState.manipulationPreview : Manipulation.presentation(ShellState.state)
    readonly property var placement: manipulation.placement
    readonly property var hints: manipulation.hints || ({context:'',actions:[]})
    readonly property var carry: manipulation.carry
    readonly property var content: manipulation.content
    readonly property bool placing: placement.available && tool === 5
    readonly property bool freeCursor: Interaction.freeCursor(ShellState.state)
    readonly property bool focusMode: Interaction.focusMode(ShellState.state)
    readonly property bool climbing: Interaction.climbing(ShellState.state)
    readonly property string climbPrompt: Interaction.climbPrompt(ShellState.state)
    readonly property bool worldPrompts: !freeCursor
    readonly property var editor: ShellState.state ? ShellState.state.editor : null
    readonly property int tool: manipulation.placement.active ? 5 : ShellState.hudTool ? ShellState.hudTool.slot : editor && editor.tool <= 5 ? editor.tool : 1
    readonly property string subtype: ShellState.hudTool ? ShellState.hudTool.subtype : editor && editor.submode !== 'reserved' ? editor.submode : 'normal'
    readonly property var subtypes: tool === 2 ? ['place','lock'] : tool === 3 ? ['open line','open curve','open arc','closed line','closed curve','closed arc'] : tool === 4 ? ['move','rotate','scale'] : ['normal']
    readonly property string toolName: ['Navigate','Window','Path','Position','Placement'][tool-1]
    readonly property var timings: ShellState.graphics ? ShellState.graphics.timings : null
    readonly property real fps: ShellState.hudFrame ? (typeof ShellState.hudFrame.fps === 'number' ? ShellState.hudFrame.fps : -1) : timings && typeof timings.deliveredFPS === 'number' ? timings.deliveredFPS : -1
    readonly property real frameMs: ShellState.hudFrame ? (typeof ShellState.hudFrame.frameMs === 'number' ? ShellState.hudFrame.frameMs : -1) : timings && typeof timings.frameMs === 'number' ? timings.frameMs : -1
    readonly property real renderScale: ShellState.hudFrame ? (typeof ShellState.hudFrame.renderScale === 'number' ? ShellState.hudFrame.renderScale : -1) : timings && typeof timings.renderScale === 'number' ? timings.renderScale : -1
    readonly property real budget: 1000 / (ShellState.graphics ? ShellState.graphics.config.target_fps : 60)
    readonly property real gpuMs: ShellState.hudFrame ? (typeof ShellState.hudFrame.gpuMs === 'number' ? ShellState.hudFrame.gpuMs : -1) : timings && timings.gpuPassMs && timings.gpuPassMs.every(v => typeof v === 'number') ? timings.gpuPassMs.reduce((a,b) => a+b,0) : -1
    readonly property real cpuMs: ShellState.hudFrame ? (typeof ShellState.hudFrame.cpuMs === 'number' ? ShellState.hudFrame.cpuMs : -1) : timings && typeof timings.cpuRenderMs === 'number' ? timings.cpuRenderMs : -1
    readonly property string activeWindow: {
        if (!ShellState.state || !ShellState.state.apps) return '';
        var selected = editor ? editor.selectedId : null;
        var focused = ShellState.surfaces.find(s => s.kind === 'window' && s.focused);
        var app = ShellState.state.apps.find(a => a.surfaceId === selected || (focused && a.surfaceId === focused.id));
        return app ? app.title : '';
    }
    readonly property int pathPoints: editor ? editor.paths.reduce((n,p) => n+p.points.length,0) : 0
    readonly property int locked: editor ? editor.locked.length : 0
    readonly property real resourceValue: Tokens.hudResource === 'tool' ? (tool === 3 ? pathPoints/2048 : tool === 2 ? locked/Math.max(1,ShellState.surfaces.filter(s => s.kind === 'window').length) : -1) : Tokens.hudResource === 'cpu' ? cpuMs/budget : gpuMs/budget
    readonly property bool resourceAvailable: resourceValue >= 0
    readonly property string resourceLabel: Tokens.hudResource === 'tool' ? (tool === 3 ? 'PATH POINT CAPACITY' : tool === 2 ? 'WINDOWS LOCKED' : 'NO TOOL CAPACITY') : Tokens.hudResource === 'cpu' ? 'CPU RENDER / FRAME BUDGET' : 'GPU / FRAME BUDGET'
    readonly property string resourceText: Tokens.hudResource === 'tool' ? (tool === 3 ? pathPoints+' / 2048' : tool === 2 ? locked+' LOCKED' : '—') : (Tokens.hudResource === 'cpu' ? cpuMs : gpuMs) >= 0 ? (Tokens.hudResource === 'cpu' ? cpuMs : gpuMs).toFixed(1)+' / '+budget.toFixed(1)+' ms' : 'UNAVAILABLE'
    readonly property bool idle: PerformanceText.idle(ShellState.previousTimings, timings)
    readonly property string stats: PerformanceText.stats(fps, frameMs, renderScale, idle)
}
