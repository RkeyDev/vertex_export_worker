import logging
import json
import os
from typing import Optional, Tuple

from playwright.sync_api import sync_playwright, Playwright, Browser

from app.dataTypes.OperationResult import OperationResult
from app.dataTypes.ExportRequest import ExportRequest
from app.dataTypes.FileType import FileType
from app.infrastructure.RedisManager import RedisManager
from app.infrastructure.ScreenshotService import ScreenshotService
from app.strategies.ExportProcessor import ExportProcessor
from app.strategies.ImageExportService import ImageExportService
from app.strategies.MetadataExportService import MetadataExportService
from app.strategies.PdfExportService import PdfExportService
from app.strategies.ThumbnailExportService import ThumbnailExportService

logger = logging.getLogger(__name__)

_BLPOP_TIMEOUT = 5


class ExportService:

    def __init__(self):
        self.redis_manager = RedisManager()

        # Maps file type specs to concrete strategy handler implementations
        self.export_type_routes = {
            FileType.JPEG_ZIP: ImageExportService,
            FileType.PDF: PdfExportService,
            FileType.VERTEX: MetadataExportService,
            FileType.JPEG_THUMBNAIL: ThumbnailExportService,
        }

        # Lifecycle management initialisation for headless rendering
        self._playwright: Playwright = sync_playwright().start()
        self._browser: Browser = self._playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--allow-running-insecure-content",
            ],
        )
        logger.info("Playwright browser initialised successfully.")

    def shutdown(self) -> None:
        """
        Clean up Playwright cluster resources.
        Ensures execution processes free socket and browser layers gracefully
        upon shutdown signals.
        """
        try:
            self._browser.close()
            self._playwright.stop()
            logger.info("Playwright browser shut down cleanly.")
        except Exception as exc:
            logger.warning("Error during Playwright shutdown orchestration: %s", exc)

    def handlePendingRequest(
        self,
    ) -> Tuple[OperationResult, Optional[ExportRequest], Optional[str]]:
        """
        Pulls pending queue signals from Redis and executes matching strategy
        processors.

        Returns:
            A 3-tuple of ``(OperationResult, ExportRequest | None, output_path | None)``.
            ``output_path`` is populated only on ``SUCCEED``; callers use it to
            enqueue the download-ready notification.
        """
        request = self._waitForExportRequest()

        if request is None:
            # Queue was empty — not an error, just nothing to do this cycle.
            return OperationResult.SUCCEED, None, None

        processor_class = self.export_type_routes.get(request.file_type)

        if processor_class is None:
            logger.error(
                "Invalid file type: no strategy route found for: %s", request.file_type
            )
            return OperationResult.FAILED, request, None

        export_processor: ExportProcessor = processor_class()

        # Phase 1: Visual rasterisation via Playwright (only for image-bearing formats)
        if export_processor.requiresScreenshots():
            screenshot_service = ScreenshotService(request, self._browser, export_processor.screenshotsNumber())
            screenshot_result = screenshot_service.takeScreenshots()

            if screenshot_result != OperationResult.SUCCEED:
                logger.error(
                    "Screenshot capture failed for board '%s'", request.board_id
                )
                return OperationResult.FAILED, request, None

        # Phase 2: Domain-specific aggregation (PDF compilation, ZIP packing, etc.)
        result = export_processor.exportBoard(request)

        if result != OperationResult.SUCCEED:
            logger.error(
                "Export strategy failed for board '%s'", request.board_id
            )
            return OperationResult.FAILED, request, None

        output_path = self._resolve_output_path(request)
        logger.info(
            "Board exported successfully [board=%s, path=%s]",
            request.board_id, output_path,
        )
        return OperationResult.SUCCEED, request, output_path

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _waitForExportRequest(self) -> Optional[ExportRequest]:
        """
        Blocks until a job is popped from the Redis export queue.
        Defensively maps schemas via factory constructor to guard against
        corrupted payload crashes.
        """
        try:
            raw = self.redis_manager.blockingGetFirstFromQueue(timeout=_BLPOP_TIMEOUT)
            if raw is None:
                return None

            data = json.loads(raw)
            return ExportRequest.from_dict(data)

        except (KeyError, json.JSONDecodeError, ValueError) as exc:
            logger.error(
                "Export worker dropped a corrupted queue message. "
                "Parsing failed with: %s",
                exc,
                exc_info=True,
            )
            return None

    def _resolve_output_path(self, request: ExportRequest) -> str:
            # The worker writes to /app/exports/output/email/boardId/timestamp/...
            # The backend expects the path relative to /app/exports/
            # Therefore, we return 'output/email/boardId/timestamp/...'
            
            timestamp_str = request.request_time_stamp.strftime("%Y-%m-%dT%H-%M-%S")
            relative_dir = os.path.join("output", request.sender_email, request.board_id, timestamp_str)
            
            filename_map = {
                FileType.JPEG_ZIP:   f"{request.board_id}.zip",
                FileType.PDF:    f"{request.board_id}.pdf",
                FileType.VERTEX: f"{request.board_id}.vertex",
                FileType.JPEG_THUMBNAIL: f"{request.board_id}_thumbnail.jpeg",
            }

            filename = filename_map.get(request.file_type, request.board_id)
            return os.path.join(relative_dir, filename)