import math
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock, call

from app.dataTypes.OperationResult import OperationResult
from app.dataTypes.ExportRequest import ExportRequest
from app.dataTypes.FileType import FileType
from app.infrastructure.ScreenshotService import ScreenshotService, _CLUSTER_THRESHOLD


# ==============================================================================
# FIXTURES
# ==============================================================================

def make_export_request(board_id="test-board-123", jwt="mock.jwt.token") -> ExportRequest:
    return ExportRequest(
        requestId="req-001",
        boardId=board_id,
        senderJwt=jwt,
        senderEmail="roei1576@gmail.com",
        fileType=FileType.JPEG,
        requestTimeStamp=datetime(2025, 1, 1, 12, 0, 0),
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
        # b starts exactly where a ends
        a = make_node(0, 0, 100, 100)
        b = make_node(100, 0, 100, 100)
        assert ScreenshotService._calculate_box_distance(a, b) == 0.0

    def test_horizontal_gap(self):
        a = make_node(0, 0, 100, 100)
        b = make_node(150, 0, 100, 100)  # 50px gap
        assert ScreenshotService._calculate_box_distance(a, b) == pytest.approx(50.0)

    def test_vertical_gap(self):
        a = make_node(0, 0, 100, 100)
        b = make_node(0, 200, 100, 100)  # 100px gap
        assert ScreenshotService._calculate_box_distance(a, b) == pytest.approx(100.0)

    def test_diagonal_gap(self):
        a = make_node(0, 0, 100, 100)
        b = make_node(200, 200, 100, 100)  # 100px gap in both axes
        assert ScreenshotService._calculate_box_distance(a, b) == pytest.approx(math.sqrt(100**2 + 100**2))

    def test_node_b_left_of_node_a(self):
        a = make_node(200, 0, 100, 100)
        b = make_node(0, 0, 100, 100)   # 100px gap to the left
        assert ScreenshotService._calculate_box_distance(a, b) == pytest.approx(100.0)

    def test_node_b_above_node_a(self):
        a = make_node(0, 200, 100, 100)
        b = make_node(0, 0, 100, 100)   # 100px gap above
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
        b = make_node(150, 0, 100, 100, "b")   # 50px gap — within threshold of 100
        clusters = ScreenshotService._group_nodes_into_clusters([a, b], 100)
        assert len(clusters) == 1
        assert set(n["id"] for n in clusters[0]) == {"a", "b"}

    def test_two_far_nodes_stay_separate(self):
        a = make_node(0,    0, 100, 100, "a")
        b = make_node(1000, 0, 100, 100, "b")  # 900px gap — beyond threshold of 100
        clusters = ScreenshotService._group_nodes_into_clusters([a, b], 100)
        assert len(clusters) == 2

    def test_chain_merge_three_nodes(self):
        # a–b are close, b–c are close, so all three should merge even if a–c are far
        a = make_node(0,   0, 100, 100, "a")
        b = make_node(150, 0, 100, 100, "b")   # 50px from a
        c = make_node(300, 0, 100, 100, "c")   # 50px from b, 200px from a
        clusters = ScreenshotService._group_nodes_into_clusters([a, b, c], 100)
        assert len(clusters) == 1
        assert len(clusters[0]) == 3

    def test_two_separate_groups(self):
        a = make_node(0,    0, 100, 100, "a")
        b = make_node(150,  0, 100, 100, "b")  # close to a
        c = make_node(2000, 0, 100, 100, "c")
        d = make_node(2150, 0, 100, 100, "d")  # close to c
        clusters = ScreenshotService._group_nodes_into_clusters([a, b, c, d], 100)
        assert len(clusters) == 2
        ids = [set(n["id"] for n in cl) for cl in clusters]
        assert {"a", "b"} in ids
        assert {"c", "d"} in ids

    def test_empty_nodes_returns_empty(self):
        assert ScreenshotService._group_nodes_into_clusters([], 100) == []

    def test_threshold_zero_only_overlapping_merge(self):
        # With threshold=0, only touching/overlapping nodes merge
        a = make_node(0, 0, 100, 100, "a")
        b = make_node(100, 0, 100, 100, "b")   # touching — distance == 0
        c = make_node(201, 0, 100, 100, "c")   # 1px gap
        clusters = ScreenshotService._group_nodes_into_clusters([a, b, c], 0)
        assert len(clusters) == 2


# ==============================================================================
# saveScreenshotLocally — Playwright integration (fully mocked)
# ==============================================================================

def _build_playwright_mocks(raw_nodes: list[dict]):
    """
    Constructs the layered mock tree that sync_playwright().__enter__ returns,
    wired so page.evaluate() returns raw_nodes on the extraction call and None
    on all setup calls.
    """
    mock_page = MagicMock()
    mock_canvas = MagicMock()
    mock_browser = MagicMock()
    mock_context = MagicMock()
    mock_playwright = MagicMock()

    # Wire browser/context/page creation chain
    mock_playwright.__enter__ = MagicMock(return_value=mock_playwright)
    mock_playwright.__exit__ = MagicMock(return_value=False)
    mock_playwright.chromium.launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    # Canvas locator
    mock_page.locator.return_value = mock_canvas

    # page.evaluate(): return raw_nodes only on the extraction call (the one that
    # returns a list); all other calls (setup JS) return None.
    def evaluate_side_effect(script, *args, **kwargs):
        if isinstance(script, str) and "extracted.push" in script:
            return raw_nodes
        return None

    mock_page.evaluate.side_effect = evaluate_side_effect

    return mock_playwright, mock_page, mock_canvas, mock_browser


class TestSaveScreenshotLocally:

    def test_returns_succeed_on_happy_path(self):
        nodes = [make_node(0, 0, 200, 200, "n1")]
        mock_pw, mock_page, mock_canvas, mock_browser = _build_playwright_mocks(nodes)

        with patch("app.infrastructure.ScreenshotService.sync_playwright", return_value=mock_pw):
            service = ScreenshotService(make_export_request())
            result = service.saveScreenshotLocally()

        assert result == OperationResult.SUCCEED

    def test_returns_failed_when_no_nodes_detected(self):
        mock_pw, mock_page, mock_canvas, mock_browser = _build_playwright_mocks([])

        with patch("app.infrastructure.ScreenshotService.sync_playwright", return_value=mock_pw):
            service = ScreenshotService(make_export_request())
            result = service.saveScreenshotLocally()

        assert result == OperationResult.FAILED

    def test_returns_failed_on_playwright_exception(self):
        mock_pw = MagicMock()
        mock_pw.__enter__ = MagicMock(return_value=mock_pw)
        mock_pw.__exit__ = MagicMock(return_value=False)
        mock_pw.chromium.launch.side_effect = RuntimeError("Browser failed to launch")

        with patch("app.infrastructure.ScreenshotService.sync_playwright", return_value=mock_pw):
            service = ScreenshotService(make_export_request())
            result = service.saveScreenshotLocally()

        assert result == OperationResult.FAILED

    def test_jwt_injected_into_localstorage(self):
        nodes = [make_node(0, 0, 200, 200, "n1")]
        mock_pw, mock_page, mock_canvas, mock_browser = _build_playwright_mocks(nodes)

        jwt = "my.test.jwt"
        with patch("app.infrastructure.ScreenshotService.sync_playwright", return_value=mock_pw):
            ScreenshotService(make_export_request(jwt=jwt)).saveScreenshotLocally()

        injected_calls = [
            str(c) for c in mock_page.evaluate.call_args_list
            if jwt in str(c)
        ]
        assert len(injected_calls) >= 1, "JWT was never injected into localStorage"

    def test_navigates_to_correct_board_url(self):
        nodes = [make_node(0, 0, 200, 200, "n1")]
        mock_pw, mock_page, mock_canvas, mock_browser = _build_playwright_mocks(nodes)

        board_id = "board-abc-999"
        with patch("app.infrastructure.ScreenshotService.sync_playwright", return_value=mock_pw):
            ScreenshotService(make_export_request(board_id=board_id)).saveScreenshotLocally()

        goto_urls = [c.args[0] for c in mock_page.goto.call_args_list if c.args]
        assert any(board_id in url for url in goto_urls), (
            f"Expected board ID '{board_id}' in one of the goto calls: {goto_urls}"
        )

    def test_screenshot_taken_once_per_cluster(self):
        # Two nodes far apart → two clusters → two screenshots
        nodes = [
            make_node(0,    0, 100, 100, "a"),
            make_node(5000, 0, 100, 100, "b"),
        ]
        mock_pw, mock_page, mock_canvas, mock_browser = _build_playwright_mocks(nodes)

        with patch("app.infrastructure.ScreenshotService.sync_playwright", return_value=mock_pw):
            ScreenshotService(make_export_request()).saveScreenshotLocally()

        assert mock_canvas.screenshot.call_count == 2

    def test_single_cluster_produces_one_screenshot(self):
        nodes = [
            make_node(0,   0, 100, 100, "a"),
            make_node(150, 0, 100, 100, "b"),  # close — merges into one cluster
        ]
        mock_pw, mock_page, mock_canvas, mock_browser = _build_playwright_mocks(nodes)

        with patch("app.infrastructure.ScreenshotService.sync_playwright", return_value=mock_pw):
            ScreenshotService(make_export_request()).saveScreenshotLocally()

        assert mock_canvas.screenshot.call_count == 1

    def test_browser_closed_on_success(self):
        nodes = [make_node(0, 0, 200, 200, "n1")]
        mock_pw, mock_page, mock_canvas, mock_browser = _build_playwright_mocks(nodes)

        with patch("app.infrastructure.ScreenshotService.sync_playwright", return_value=mock_pw):
            ScreenshotService(make_export_request()).saveScreenshotLocally()

        mock_browser.close.assert_called_once()

    def test_browser_closed_when_no_nodes(self):
        mock_pw, mock_page, mock_canvas, mock_browser = _build_playwright_mocks([])

        with patch("app.infrastructure.ScreenshotService.sync_playwright", return_value=mock_pw):
            ScreenshotService(make_export_request()).saveScreenshotLocally()

        mock_browser.close.assert_called_once()

    def test_setcamera_called_for_each_cluster(self):
        # Three nodes: two nearby (one cluster) + one far (second cluster) → 2 setCamera calls
        nodes = [
            make_node(0,    0, 100, 100, "a"),
            make_node(150,  0, 100, 100, "b"),
            make_node(9000, 0, 100, 100, "c"),
        ]
        mock_pw, mock_page, mock_canvas, mock_browser = _build_playwright_mocks(nodes)

        set_camera_calls = []

        def evaluate_side_effect(script, *args, **kwargs):
            if isinstance(script, str) and "extracted.push" in script:
                return nodes
            if isinstance(script, str) and "setCamera" in script:
                set_camera_calls.append(args[0] if args else kwargs)
            return None

        mock_page.evaluate.side_effect = evaluate_side_effect

        with patch("app.infrastructure.ScreenshotService.sync_playwright", return_value=mock_pw):
            ScreenshotService(make_export_request()).saveScreenshotLocally()

        assert len(set_camera_calls) == 2