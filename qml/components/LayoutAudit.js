// Development-only scene geometry inspection. Clipped scroll content is valid;
// text painting outside its own box, negative sizes and unconstrained headings
// are not. Called only by preview IPC inside the isolated test harness.
function inspect(root) {
    var failures = [], labels = 0, elided = 0;
    function visit(item) {
        if (!item || !item.visible) return;
        if (typeof item.text === 'string' && item.paintedWidth !== undefined && item.text.length) {
            labels++;
            if (item.truncated) elided++;
            if (item.width < 0 || item.paintedWidth > item.width + 2 || (item.text.trim().length === 1 && item.truncated))
                failures.push({text:item.text.slice(0,100),width:item.width,painted:item.paintedWidth});
        }
        if (item.children) for (var i=0;i<item.children.length;i++) visit(item.children[i]);
    }
    visit(root);
    return {labels:labels,elided:elided,failures:failures};
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
