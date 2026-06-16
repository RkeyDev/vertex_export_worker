import math
import os
from playwright.sync_api import Browser

from app.dataTypes.OperationResult import OperationResult
from app.dataTypes.ExportRequest import ExportRequest
from app.infrastructure.js_scripts import (
    INJECT_STAGE_INTO_CONTROLLER,
    EXTRACT_NODE_RECTS,
    SET_CAMERA,
    inject_jwt,
)

# ==============================================================================
# CONFIGURATION CONSTANTS
# ==============================================================================
_VIEWPORT_WIDTH    = 1920
_VIEWPORT_HEIGHT   = 1080
_PADDING_FACTOR    = 1.50
_MIN_ZOOM_LEVEL    = 0.5
_MAX_ZOOM_LEVEL    = 5.0
_CLUSTER_THRESHOLD = 650.0

_BASE_URL = os.getenv("BASE_URL", "http://localhost:5174")


class ScreenshotService:

    def __init__(self, export_request: ExportRequest, browser: Browser) -> None:
        self.export_request = export_request
        self._browser = browser

    # ==========================================================================
    # SPATIAL ALGORITHMS & CLUSTERING MECHANISMS
    # ==========================================================================

    @staticmethod
    def _calculate_box_distance(node1: dict, node2: dict) -> float:
        """
        Computes the shortest distance between two discrete bounding boxes.
        Returns 0 if the nodes overlap on both dimensions.
        """
        l1, r1 = node1["x"], node1["x"] + node1["width"]
        t1, b1 = node1["y"], node1["y"] + node1["height"]

        l2, r2 = node2["x"], node2["x"] + node2["width"]
        t2, b2 = node2["y"], node2["y"] + node2["height"]

        dx = max(0, l2 - r1) if r1 < l2 else max(0, l1 - r2) if r2 < l1 else 0
        dy = max(0, t2 - b1) if b1 < t2 else max(0, t1 - b2) if b2 < t1 else 0

        return math.sqrt(dx**2 + dy**2)

    @staticmethod
    def _group_nodes_into_clusters(nodes: list[dict], threshold: float) -> list[list[dict]]:
        """
        Agglomerative clustering algorithm that merges component records into unified
        clusters whenever an element drops within the defined proximity threshold of
        an existing member.
        """
        clusters = [[node] for node in nodes]

        changed = True
        while changed:
            changed = False
            for i in range(len(clusters)):
                for j in range(i + 1, len(clusters)):
                    should_merge = any(
                        ScreenshotService._calculate_box_distance(n1, n2) <= threshold
                        for n1 in clusters[i]
                        for n2 in clusters[j]
                    )
                    if should_merge:
                        clusters[i].extend(clusters[j])
                        clusters.pop(j)
                        changed = True
                        break
                if changed:
                    break

        return clusters

    # ==========================================================================
    # MAIN CAPTURE PIPELINE
    # ==========================================================================

    def takeScreenshots(self) -> OperationResult:
        board_id   = self.export_request.board_id
        jwt_token  = self.export_request.sender_jwt
        target_url = f"{_BASE_URL}/board?id={board_id}"

        try:
            # Each job gets its own isolated context (cookies, localStorage, etc.)
            # but shares the already-running browser process — no cold-start.
            context = self._browser.new_context(
                viewport={"width": _VIEWPORT_WIDTH, "height": _VIEWPORT_HEIGHT}
            )
            page = context.new_page()

            # ------------------------------------------------------------------
            # DIAGNOSTIC ENGINE INTERCEPTORS
            # ------------------------------------------------------------------
            page.on("console",       lambda msg: print(f"  [Browser Console] {msg.type.upper()}: {msg.text}"))
            page.on("response",      lambda res: print(f"  [Browser Network] {res.status} -> {res.url}") if res.status >= 400 else None)
            page.on("requestfailed", lambda req: print(f"  [Browser Network Error] Failed: {req.url}"))
            page.on("pageerror",     lambda exc: print(f"  [Browser Runtime Crash] CRITICAL EXCEPTION: {exc}"))

            # ------------------------------------------------------------------
            # PLAYWRIGHT INITIALIZATION & WORKSPACE INJECTION
            # ------------------------------------------------------------------
            page.goto(_BASE_URL)
            page.evaluate(inject_jwt(jwt_token))
            page.goto(target_url, wait_until="networkidle")

            canvas_locator = page.locator("canvas")
            canvas_locator.wait_for(state="visible")

            page.wait_for_timeout(2000)

            page.evaluate(INJECT_STAGE_INTO_CONTROLLER)

            # ------------------------------------------------------------------
            # IN-BROWSER METRIC EXTRACTION ENGINE
            # ------------------------------------------------------------------
            raw_nodes = page.evaluate(EXTRACT_NODE_RECTS)

            if not raw_nodes:
                context.close()
                return OperationResult.FAILED

            # ------------------------------------------------------------------
            # CLUSTER LOGIC & TRANSFORMS
            # ------------------------------------------------------------------
            clusters = self._group_nodes_into_clusters(raw_nodes, _CLUSTER_THRESHOLD)
            print(f"[INFO] Grouped {len(raw_nodes)} components into {len(clusters)} visual clusters.")

            # ------------------------------------------------------------------
            # CAMERA VIEWPORT TRANSITIONS & RENDERED CAPTURE
            # ------------------------------------------------------------------
            output_dir = self.export_request.output_dir
            os.makedirs(output_dir, exist_ok=True)
            print(f"[INFO] Saving screenshots to: {output_dir}")

            saved_paths: list[str] = []

            for idx, cluster in enumerate(clusters):
                c_min_x = min(n["x"] for n in cluster)
                c_max_x = max(n["x"] + n["width"] for n in cluster)
                c_min_y = min(n["y"] for n in cluster)
                c_max_y = max(n["y"] + n["height"] for n in cluster)

                cluster_w = c_max_x - c_min_x
                cluster_h = c_max_y - c_min_y

                center_x = c_min_x + (cluster_w / 2)
                center_y = c_min_y + (cluster_h / 2)

                scale_x = _VIEWPORT_WIDTH  / (cluster_w * _PADDING_FACTOR)
                scale_y = _VIEWPORT_HEIGHT / (cluster_h * _PADDING_FACTOR)
                final_zoom = max(min(min(scale_x, scale_y), _MAX_ZOOM_LEVEL), _MIN_ZOOM_LEVEL)

                offset_x = (_VIEWPORT_WIDTH  / 2) - (center_x * final_zoom)
                offset_y = (_VIEWPORT_HEIGHT / 2) - (center_y * final_zoom)

                print(
                    f"[Capture] Cluster {idx + 1}/{len(clusters)} | "
                    f"Elements: {len(cluster)} | Zoom: {final_zoom:.2f}"
                )

                page.evaluate(SET_CAMERA, {"x": offset_x, "y": offset_y, "zoom": final_zoom})

                page.wait_for_timeout(800)

                out_path = os.path.join(output_dir, f"cluster_output_{idx + 1:02d}.jpeg")
                canvas_locator.screenshot(path=out_path, type="jpeg", quality=95)
                saved_paths.append(out_path)
                print(f"  └ Saved snapshot: {out_path}")

            # Always close the context when done — frees memory and
            # ensures the next job gets a clean session (no stale localStorage, cookies, etc.)
            context.close()
            return OperationResult.SUCCEED

        except Exception as e:
            print(f"[ERROR] Executing snapshot process failed: {str(e)}")
            try:
                context.close()
            except Exception:
                pass
            return OperationResult.FAILED