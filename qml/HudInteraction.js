function freeCursor(state) {
    return !!state && ((!!state.interaction && state.interaction.mode === 'cursor') ||
                      (!!state.editor && state.editor.mode === 'cursor'));
}
function climbing(state) {
    return !!state && !freeCursor(state) && !!state.movement && state.movement.state === 'climbing';
}
function climbPrompt(state) {
    if (!climbing(state)) return '';
    return (state.movement.prompt || '').trim() || 'W/S climb · Space let go';
}
// Focus (F: a focused workspace or a fullscreen window) and use (E: typing in a window)
// show the window, not the world: no HUD there. The free cursor keeps it.
function focusMode(state) {
    var mode = state && state.interaction ? state.interaction.mode : '';
    return mode === 'workspace' || mode === 'fullscreen' || mode === 'typing';
}
