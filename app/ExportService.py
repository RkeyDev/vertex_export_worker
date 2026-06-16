import logging
import json
import datetime
from typing import Optional

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

logger = logging.getLogger(__name__)

_BLPOP_TIMEOUT = 5


class ExportService:

    def __init__(self):
        self.redis_manager = RedisManager()
        
        # Maps file type specs to concrete strategy handler implementations
        self.export_type_routes = {
            FileType.JPEG: ImageExportService,
            FileType.PDF: PdfExportService,
            FileType.VERTEX: MetadataExportService
        }

        # Lifecycle management initialization for headless rendering
        self._playwright: Playwright = sync_playwright().start()
        self._browser: Browser = self._playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--allow-running-insecure-content"
            ]
        )
        logger.info("Playwright browser initialized successfully.")

    def shutdown(self) -> None:
        """
        Clean up Playwright cluster resources. 
        Ensures execution processes free socket and browser layers gracefully upon shutdown signals.
        """
        try:
            self._browser.close()
            self._playwright.stop()
            logger.info("Playwright browser shut down cleanly.")
        except Exception as e:
            logger.warning("Error during Playwright shutdown orchestration: %s", e)

    def handlePendingRequest(self) -> OperationResult:
        """
        Pulls pending queue signals from Redis and executes matching strategy processors.
        """
        request = self._waitForExportRequest()

        if request is None:
            return OperationResult.SUCCEED

        # Fetch the strategy class handler matching the file specification
        processor_class = self.export_type_routes.get(request.file_type)

        if processor_class is None:
            logger.error("Invalid file type strategy route mapping missing for: %s", request.file_type)
            return OperationResult.FAILED

        # Instantiate strategy engine context dynamically
        export_processor: ExportProcessor = processor_class()

        # Phase 1: Determine if visual rasterization via Playwright chromium layers is required
        if export_processor.requiresScreenshots():
            screenshot_service = ScreenshotService(request, self._browser)
            result = screenshot_service.takeScreenshots()

            if result != OperationResult.SUCCEED:
                logger.error("Taking board screenshots failed for board configuration id: '%s'", request.board_id)
                return OperationResult.FAILED

        # Phase 2: Execute domain-specific aggregation (e.g., PDF generation or Zip file compilation)
        result = export_processor.exportBoard(request)

        if result == OperationResult.SUCCEED:
            logger.info("Successfully exported board tracking identifier: '%s'", request.board_id)
        else:
            logger.error("Failed to export board tracking identifier: '%s'", request.board_id)

        return result

    def _waitForExportRequest(self) -> Optional[ExportRequest]:
        """
        Blocks till a job is popped from the underlying Redis message layer.
        Defensively maps schemas via factory constructor to mitigate corrupted payload crashes.
        """
        try:
            raw = self.redis_manager.blockingGetFirstFromQueue(timeout=_BLPOP_TIMEOUT)
            if raw is None:
                return None
            
            # Map structural text streams to intermediate raw dictionary structures
            data = json.loads(raw)
            
            # Use factory parsing method to build domain request models, resolving timestamp conflicts
            return ExportRequest.from_dict(data)
            
        except (KeyError, json.JSONDecodeError, ValueError) as e:
            logger.error(
                "Export worker pipeline dropped a corrupted queue message artifact. "
                "Parsing failed with structural violation exception: %s", 
                e, 
                exc_info=True
            )
            return None