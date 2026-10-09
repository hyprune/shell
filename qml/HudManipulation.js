// Presentation adapter. New core fields are mapped here, never inferred from
// desktop inventory: a visible app is not necessarily an unplaced app.
function binding(state, action, fallback) {
    var modes=state && state.keymap && state.keymap.config && state.keymap.config.modes;
    var value=modes && modes.world && modes.world[action];
    return Array.isArray(value) ? (value.length ? value.join(' / ') : 'Unbound') : (fallback || '');
}
function empty() {
    return {placement:{available:false,active:false,count:0,index:-1,app:null,size:null,ghost:false},
            carry:{active:false,label:'',toggle:''},content:null,hints:{context:'',actions:[]}};
}
function presentation(state) {
    var result=empty(), editor=state && state.editor;
    result.hints=slotHints(state);
    if (!editor) return result;
    var queue=editor.unplaced;
    if (queue && Array.isArray(queue.windows)) {
        var index=queue.windows.findIndex(w=>w.surfaceId===queue.selectedId);
        var selected=index>=0 ? queue.windows[index] : null;
        var metadata=selected && (state.apps || []).find(a=>a.surfaceId===selected.surfaceId);
        var surface=selected && (state.surfaces || []).find(a=>a.id===selected.surfaceId);
        result.placement={available:true,active:editor.tool===5,count:queue.count,index:index,
            app:selected ? Object.assign({},metadata || {},selected) : null,
            size:selected && selected.logicalSize ? selected.logicalSize : surface ? surface.logicalSize : null,
            ghost:queue.preview===true};
    }
    if (typeof editor.carryFacing==='boolean') {
        result.carry={active:true,label:editor.carryFacing ? 'FACING YOU' : 'KEEP ANGLE',
            toggle:binding(state,'carry.facing','R')+' · TOGGLE'};
    }
    var content=editor.contentScale;
    if (content) result.content={surfaceId:content.surfaceId,scale:content.scale,
        clientSize:content.logicalSize,serial:content.sequence,reset:content.reset};
    return result;
}
function changedContent(previous, next) {
    if (!previous || !next || !previous.world || !next.world || previous.world.id!==next.world.id) return null;
    var before=presentation(previous).content, after=presentation(next).content;
    return after && (!before || after.serial!==before.serial) ? after : null;
}

function slotHints(state) {
    var editor=state && state.editor;
    if (!editor || !editor.toolSlots) return {context:'',actions:[]};
    var input=editor.toolInput, gestures=input ? input.gestures.map(gesture=>({
        slot:gesture.action,label:gesture.label,bindings:gesture.bindings})) : [];
    // Core owns modifier state, precedence and eligibility, including remapped
    // chords. The passive HUD never grabs keys or guesses which gesture wins.
    if (input && input.override) return {context:'GLOBAL GESTURES',actions:gestures};
    return {context:'',actions:['primary','secondary','alternate','cycle'].filter(slot=>editor.toolSlots[slot]).map(slot=>({
        slot:slot,label:editor.toolSlots[slot].label,
        bindings:bindingList(state,slot)})).concat(gestures)};
}
function bindingList(state, action) {
    var config=state && state.keymap && state.keymap.config;
    return config && config.modes.world[action] || [];
}
function toolHelp(state) {
    var editor=state && state.editor;
    return editor && editor.toolDefinitions ? editor.toolDefinitions.map(tool=>[
        tool.slot+' · '+tool.name.toUpperCase(),
        ['primary','secondary','alternate','cycle'].filter(slot=>tool.slots[slot]).map(slot=>
            binding(state,slot,'Unbound')+' · '+tool.slots[slot].label).join('  /  ')
    ]) : [];
}
