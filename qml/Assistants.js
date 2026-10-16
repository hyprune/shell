// RFC-0016 (IPC 0.33): assistants that pair with Hyprune (`hyprune mcp`). Core keeps the
// connections (state.connections, shell.control peers only); the shell asks the user (Allow
// once, Always allow, Deny), shows the Assistant chip and lists Connected assistants with
// Pause, Disconnect and Revoke. Pure helpers: tested with node in tests/test_assistants.py.

var DECISIONS = [{id: 'once', label: 'Allow once'}, {id: 'always', label: 'Always allow'}, {id: 'deny', label: 'Deny'}];

function connectionsOf(state) {
    var c = state && state.connections;
    return {pending: c && c.pending ? c.pending : [], live: c && c.live ? c.live : [], approvals: c && c.approvals ? c.approvals : []};
}
function agentLabel(agent) {
    if (!agent) return 'An assistant';
    var name = String(agent.name || 'An assistant');
    return agent.version ? name + ' ' + agent.version : name;
}
// The prompt's sentences (RFC-0016 Pairing): what it may do, what it can't, and that the name is the client's own claim.
function promptTitle(request) { return request ? agentLabel(request.agent) + ' wants to build in Hyprune' : ''; }
function promptText(request) {
    if (!request) return '';
    return 'It can change world folders, objects, behaviours, companions and quests. It can\'t see or use your windows, and it can\'t publish anything. '
         + 'Changes stay unsaved until you or it saves, and can be undone. The name is what the assistant says it is.';
}
function secondsLeft(request) { return request ? Math.max(0, Math.ceil((request.expiresInMs || 0) / 1000)) : 0; }
function answerParams(request, decision) { return {requestId: request.requestId, decision: decision}; }
// The HUD banner while a request waits (the Director answers it).
function bannerText(pending) {
    if (!pending || !pending.length) return '';
    return (agentLabel(pending[0].agent) + ' wants to build · open the Director to answer').toUpperCase();
}
// The Assistant chip: who, how many changes, the last action, paused.
function chipText(live) {
    if (!live || !live.length) return '';
    var a = live[0], changes = a.changes || 0;
    var text = 'ASSISTANT · ' + agentLabel(a.agent).toUpperCase() + ' · ' + changes + (changes === 1 ? ' CHANGE' : ' CHANGES');
    if (a.paused) text += ' · PAUSED';
    if (live.length > 1) text += ' · +' + (live.length - 1);
    return text;
}
function chipDetail(live) { return live && live.length && live[0].action ? String(live[0].action) : ''; }
function liveRow(a) {
    var minutes = Math.floor((a.connectedMs || 0) / 60000);
    return {actor: a.actor, title: agentLabel(a.agent), line: (a.changes || 0) + ' changes · connected ' + (minutes ? minutes + ' min' : 'just now') + (a.remembered ? ' · always allowed' : '') + (a.paused ? ' · paused' : ''),
            action: a.action || '', paused: !!a.paused};
}
function approvalRow(a) { return {clientId: a.clientId, agent: a.agent, title: a.agent, line: 'Always allowed since ' + String(a.approvedAt || '').slice(0, 10)}; }
