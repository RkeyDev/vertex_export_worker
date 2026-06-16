# ==============================================================================
# BROWSER-SIDE JAVASCRIPT PAYLOADS
# All scripts executed via Playwright's page.evaluate().
# Centralised here so they can be imported, versioned, and tested independently.
# ==============================================================================

INJECT_STAGE_INTO_CONTROLLER = """
() => {
    const stage = window.Konva?.stages?.[0];
    if (!stage) return;
    if (!window.boardController) window.boardController = {};
    window.boardController._stage = stage;
}
"""

EXTRACT_NODE_RECTS = """
() => {
    const stage = window.boardController?._stage;
    if (!stage) {
        console.error('[Capture Engine] Extraction aborted: stage instance unavailable.');
        return [];
    }

    const NODE_STROKE_BUFFER = 35;
    const extracted = [];

    stage.getLayers().forEach(layer => {
        layer.getChildren().forEach((node, index) => {
            const className = node.getClassName();
            if (className === 'Transformer' || className === 'Arrow') return;

            const rect = node.getClientRect({ relativeTo: stage });
            if (!rect.width || !rect.height) return;

            extracted.push({
                id: node.id() || `node_${index}`,
                type: className,
                x: Math.round(rect.x) - NODE_STROKE_BUFFER,
                y: Math.round(rect.y) - NODE_STROKE_BUFFER,
                width:  Math.round(rect.width)  + (NODE_STROKE_BUFFER * 2),
                height: Math.round(rect.height) + (NODE_STROKE_BUFFER * 2)
            });
        });
    });

    return extracted;
}
"""

SET_CAMERA = """
({ x, y, zoom }) => {
    const ctrl = window.boardController;
    if (!ctrl || typeof ctrl.setCamera !== 'function') {
        console.error('[Capture Engine] Controller missing setCamera implementation.');
        return;
    }
    ctrl.setCamera({ x, y, zoom });
}
"""


def inject_jwt(jwt_token: str) -> str:
    """Returns a localStorage injection script with the JWT interpolated."""
    return f"window.localStorage.setItem('vertex_access_token', '{jwt_token}');"