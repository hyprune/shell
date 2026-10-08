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
