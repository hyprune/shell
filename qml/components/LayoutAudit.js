// Development-only scene geometry inspection. Clipped scroll content is valid;
// text painting outside its own box, negative sizes and unconstrained headings
// are not. Called only by preview IPC inside the isolated test harness.
function inspect(root) {
    var failures = [], labels = 0, elided = 0, apps = 0;
    function visit(item) {
        if (!item || !item.visible) return;
        if (item.objectName === 'workspaceApp') {
            apps++;
            var card = item.parent;
            while (card && card.objectName !== 'surfaceCard') card = card.parent;
            if (!card) failures.push({app:'missing containing card'});
            else {
                var p = item.mapToItem(card, 0, 0);
                if (p.x < 0 || p.y < 0 || p.x + item.width > card.width + 1 || p.y + item.height > card.height + 1)
                    failures.push({app:'outside card',x:p.x,y:p.y,width:item.width,height:item.height});
            }
        }
        if (typeof item.text === 'string' && item.paintedWidth !== undefined && item.text.length) {
            labels++;
            if (item.truncated) elided++;
            if (item.width < 0 || item.paintedWidth > item.width + 2 || (item.text.trim().length === 1 && item.truncated))
                failures.push({text:item.text.slice(0,100),width:item.width,painted:item.paintedWidth});
        }
        if (item.children) for (var i=0;i<item.children.length;i++) visit(item.children[i]);
    }
    visit(root);
    return {labels:labels,elided:elided,apps:apps,failures:failures};
}

// Reach overflow content for visual evidence without changing production input.
function scroll(root, fraction) {
    if (!root || !root.visible) return false;
    if (root.contentY !== undefined && root.contentHeight > root.height) {
        root.contentY = Math.max(0, root.contentHeight - root.height) * Math.max(0, Math.min(1, fraction));
        return true;
    }
    if (root.children) for (var i=0;i<root.children.length;i++)
        if (scroll(root.children[i], fraction)) return true;
    return false;
}

function find(root, name) {
    if (!root || !root.visible) return null;
    if (root.objectName === name) return root;
    if (root.children) for (var i=0;i<root.children.length;i++) {
        var found = find(root.children[i], name);
        if (found) return found;
    }
    return null;
}

function findAll(root, prefix, out) {
    out = out || [];
    if (!root || !root.visible) return out;
    if (typeof root.objectName === 'string' && root.objectName.indexOf(prefix) === 0) out.push(root.objectName.slice(prefix.length));
    if (root.children) for (var i = 0; i < root.children.length; i++) findAll(root.children[i], prefix, out);
    return out;
}
