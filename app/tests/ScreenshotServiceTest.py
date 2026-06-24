import math
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, call

from app.dataTypes.OperationResult import OperationResult
from app.dataTypes.ExportRequest import ExportRequest
from app.dataTypes.FileType import FileType
from app.infrastructure.ScreenshotService import ScreenshotService, _CLUSTER_THRESHOLD


# ==============================================================================
# FIXTURES
# ==============================================================================

def make_export_request(board_id="test-board-123", jwt="mock.jwt.token") -> ExportRequest:
    return ExportRequest(
        request_id="req-001",
        board_id=board_id,
        sender_jwt=jwt,
        sender_email="roei1576@gmail.com",
        file_type=FileType.JPEG_ZIP,
        request_time_stamp=datetime(2025, 1, 1, 12, 0, 0),
    )


def make_node(x: int, y: int, w: int = 100, h: int = 100, node_id: str = "n1") -> dict:
    return {"id": node_id, "type": "Rect", "x": x, "y": y, "width": w, "height": h}


# ==============================================================================
# HELPERS — _calculate_box_distance
# ==============================================================================

class TestCalculateBoxDistance:

    def test_overlapping_nodes_return_zero(self):
        a = make_node(0, 0, 200, 200)
        b = make_node(100, 100, 200, 200)
        assert ScreenshotService._calculate_box_distance(a, b) == 0.0

    def test_touching_nodes_return_zero(self):
        a = make_node(0, 0, 100, 100)
        b = make_node(100, 0, 100, 100)
        assert ScreenshotService._calculate_box_distance(a, b) == 0.0

    def test_horizontal_gap(self):
        a = make_node(0, 0, 100, 100)
        b = make_node(150, 0, 100, 100)
        assert ScreenshotService._calculate_box_distance(a, b) == pytest.approx(50.0)

    def test_vertical_gap(self):
        a = make_node(0, 0, 100, 100)
        b = make_node(0, 200, 100, 100)
        assert ScreenshotService._calculate_box_distance(a, b) == pytest.approx(100.0)

    def test_diagonal_gap(self):
        a = make_node(0, 0, 100, 100)
        b = make_node(200, 200, 100, 100)
        assert ScreenshotService._calculate_box_distance(a, b) == pytest.approx(math.sqrt(100**2 + 100**2))

    def test_node_b_left_of_node_a(self):
        a = make_node(200, 0, 100, 100)
        b = make_node(0, 0, 100, 100)
        assert ScreenshotService._calculate_box_distance(a, b) == pytest.approx(100.0)

    def test_node_b_above_node_a(self):
        a = make_node(0, 200, 100, 100)
        b = make_node(0, 0, 100, 100)
        assert ScreenshotService._calculate_box_distance(a, b) == pytest.approx(100.0)

    def test_identical_nodes_return_zero(self):
        a = make_node(50, 50, 100, 100)
        assert ScreenshotService._calculate_box_distance(a, a) == 0.0


# ==============================================================================
# HELPERS — _group_nodes_into_clusters
# ==============================================================================

class TestGroupNodesIntoClusters:

    def test_single_node_forms_one_cluster(self):
        nodes = [make_node(0, 0)]
        clusters = ScreenshotService._group_nodes_into_clusters(nodes, 100)
        assert len(clusters) == 1
        assert clusters[0] == nodes

    def test_two_close_nodes_merge(self):
        a = make_node(0,   0, 100, 100, "a")
        b = make_node(150, 0, 100, 100, "b")
        clusters = ScreenshotService._group_nodes_into_clusters([a, b], 100)
        assert len(clusters) == 1
        assert set(n["id"] for n in clusters[0]) == {"a", "b"}

    def test_two_far_nodes_stay_separate(self):
        a = make_node(0,    0, 100, 100, "a")
        b = make_node(1000, 0, 100, 100, "b")
        clusters = ScreenshotService._group_nodes_into_clusters([a, b], 100)
        assert len(clusters) == 2

    def test_chain_merge_three_nodes(self):
        a = make_node(0,   0, 100, 100, "a")
        b = make_node(150, 0, 100, 100, "b")
        c = make_node(300, 0, 100, 100, "c")
        clusters = ScreenshotService._group_nodes_into_clusters([a, b, c], 100)
        assert len(clusters) == 1
        assert len(clusters[0]) == 3

    def test_two_separate_groups(self):
        a = make_node(0,    0, 100, 100, "a")
        b = make_node(150,  0, 100, 100, "b")
        c = make_node(2000, 0, 100, 100, "c")
        d = make_node(2150, 0, 100, 100, "d")
        clusters = ScreenshotService._group_nodes_into_clusters([a, b, c, d], 100)
        assert len(clusters) == 2
        ids = [set(n["id"] for n in cl) for cl in clusters]
        assert {"a", "b"} in ids
        assert {"c", "d"} in ids

    def test_empty_nodes_returns_empty(self):
        assert ScreenshotService._group_nodes_into_clusters([], 100) == []

    def test_threshold_zero_only_overlapping_merge(self):
        a = make_node(0,   0, 100, 100, "a")
        b = make_node(100, 0, 100, 100, "b")
        c = make_node(201, 0, 100, 100, "c")
        clusters = ScreenshotService._group_nodes_into_clusters([a, b, c], 0)
        assert len(clusters) == 2


# ==============================================================================
# takeScreenshots — Playwright integration (fully mocked)
#
# The new ScreenshotService receives an already-launched Browser object via DI
# (no sync_playwright context manager involved). Each takeScreenshots() call
# opens its own context/page on that shared browser, then closes the context.
# ==============================================================================

def _build_browser_mock(raw_nodes: list[dict]):
    """
    Builds a mock Browser whose new_context() chain behaves like a real
    Playwright browser context. Returns (mock_browser, mock_page, mock_canvas).
    """
    mock_browser  = MagicMock()
    mock_context  = MagicMock()
    mock_page     = MagicMock()
    mock_canvas   = MagicMock()

    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value    = mock_page
    mock_page.locator.return_value        = mock_canvas

    def evaluate_side_effect(script, *args, **kwargs):
        if isinstance(script, str) and "extracted.push" in script:
            return raw_nodes
        return None

    mock_page.evaluate.side_effect = evaluate_side_effect

    return mock_browser, mock_context, mock_page, mock_canvas


class TestTakeScreenshots:

    def test_returns_succeed_on_happy_path(self):
        nodes = [make_node(0, 0, 200, 200, "n1")]
        mock_browser, mock_context, mock_page, mock_canvas = _build_browser_mock(nodes)

        service = ScreenshotService(make_export_request(), mock_browser)
        result = service.takeScreenshots()

        assert result == OperationResult.SUCCEED

    def test_returns_failed_when_no_nodes_detected(self):
        mock_browser, mock_context, mock_page, mock_canvas = _build_browser_mock([])

        service = ScreenshotService(make_export_request(), mock_browser)
        result = service.takeScreenshots()

        assert result == OperationResult.FAILED

    def test_returns_failed_on_playwright_exception(self):
        mock_browser = MagicMock()
        mock_browser.new_context.side_effect = RuntimeError("Browser failed to launch")

        service = ScreenshotService(make_export_request(), mock_browser)
        result = service.takeScreenshots()

        assert result == OperationResult.FAILED

    def test_jwt_injected_into_localstorage(self):
        nodes = [make_node(0, 0, 200, 200, "n1")]
        mock_browser, mock_context, mock_page, mock_canvas = _build_browser_mock(nodes)

        jwt = "my.test.jwt"
        service = ScreenshotService(make_export_request(jwt=jwt), mock_browser)
        service.takeScreenshots()

        # JWT is now injected via context.add_init_script (not page.evaluate)
        injected_calls = [
            str(c) for c in mock_context.add_init_script.call_args_list
            if jwt in str(c)
        ]
        assert len(injected_calls) >= 1, "JWT was never injected via add_init_script"

    def test_navigates_to_correct_board_url(self):
        nodes = [make_node(0, 0, 200, 200, "n1")]
        mock_browser, mock_context, mock_page, mock_canvas = _build_browser_mock(nodes)

        board_id = "board-abc-999"
        service = ScreenshotService(make_export_request(board_id=board_id), mock_browser)
        service.takeScreenshots()

        goto_urls = [c.args[0] for c in mock_page.goto.call_args_list if c.args]
        assert any(board_id in url for url in goto_urls), (
            f"Expected board ID '{board_id}' in one of the goto calls: {goto_urls}"
        )

    def test_screenshot_taken_once_per_cluster(self):
        nodes = [
            make_node(0,    0, 100, 100, "a"),
            make_node(5000, 0, 100, 100, "b"),
        ]
        mock_browser, mock_context, mock_page, mock_canvas = _build_browser_mock(nodes)

        service = ScreenshotService(make_export_request(), mock_browser)
        service.takeScreenshots()

        assert mock_canvas.screenshot.call_count == 2

    def test_single_cluster_produces_one_screenshot(self):
        nodes = [
            make_node(0,   0, 100, 100, "a"),
            make_node(150, 0, 100, 100, "b"),
        ]
        mock_browser, mock_context, mock_page, mock_canvas = _build_browser_mock(nodes)

        service = ScreenshotService(make_export_request(), mock_browser)
        service.takeScreenshots()

        assert mock_canvas.screenshot.call_count == 1

    def test_context_closed_on_success(self):
        nodes = [make_node(0, 0, 200, 200, "n1")]
        mock_browser, mock_context, mock_page, mock_canvas = _build_browser_mock(nodes)

        service = ScreenshotService(make_export_request(), mock_browser)
        service.takeScreenshots()

        mock_context.close.assert_called_once()

    def test_context_closed_when_no_nodes(self):
        mock_browser, mock_context, mock_page, mock_canvas = _build_browser_mock([])

        service = ScreenshotService(make_export_request(), mock_browser)
        service.takeScreenshots()

        mock_context.close.assert_called_once()

    def test_context_closed_on_exception(self):
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.side_effect = RuntimeError("page creation failed")

        service = ScreenshotService(make_export_request(), mock_browser)
        result = service.takeScreenshots()

        assert result == OperationResult.FAILED
        mock_context.close.assert_called_once()

    def test_setcamera_called_for_each_cluster(self):
        nodes = [
            make_node(0,    0, 100, 100, "a"),
            make_node(150,  0, 100, 100, "b"),
            make_node(9000, 0, 100, 100, "c"),
        ]
        mock_browser, mock_context, mock_page, mock_canvas = _build_browser_mock(nodes)

        set_camera_calls = []

        def evaluate_side_effect(script, *args, **kwargs):
            if isinstance(script, str) and "extracted.push" in script:
                return nodes
            if isinstance(script, str) and "setCamera" in script:
                set_camera_calls.append(args[0] if args else kwargs)
            return None

        mock_page.evaluate.side_effect = evaluate_side_effect

        service = ScreenshotService(make_export_request(), mock_browser)
        service.takeScreenshots()

        assert len(set_camera_calls) == 2