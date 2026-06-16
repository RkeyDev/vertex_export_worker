from app.dataTypes.OperationResult import OperationResult
from app.dataTypes.ExportRequest import ExportRequest
from app.infrastructure.RedisManager import RedisManager
from app.strategies.ExportProcessor import ExportProcessor
from app.strategies.ImageExportService import ImageExportService
from app.strategies.MetadataExportService import MetadataExportService
from app.strategies.PdfExportService import PdfExportService
from app.dataTypes.FileType import FileType
from app.infrastructure.ScreenshotService import ScreenshotService

from playwright.sync_api import sync_playwright, Playwright, Browser

import datetime
import json
import logging

from typing import Union

logger = logging.getLogger(__name__)

_BLPOP_TIMEOUT = 5


class ExportService:

    def __init__(self):
        self.redis_manager = RedisManager()
        self.export_type_routes = {
            FileType.JPEG: ImageExportService,
            FileType.PDF: PdfExportService,
            FileType.VERTEX: MetadataExportService
        }

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
        logger.info("Playwright browser initialized.")

    def shutdown(self):
        """Clean up Playwright resources. Call this before the process exits."""
        try:
            self._browser.close()
            self._playwright.stop()
            logger.info("Playwright browser shut down cleanly.")
        except Exception as e:
            logger.warning("Error during Playwright shutdown: %s", e)

    def handlePendingRequest(self) -> OperationResult:
        request = self._waitForExportRequest()

        if request is None:
            return OperationResult.SUCCEED

        export_processor: ExportProcessor = self.export_type_routes.get(request.file_type)

        if export_processor is None:
            logger.error("Invalid file type in request: %s", request.file_type)
            return OperationResult.FAILED

        if export_processor.requiresScreenshots():
            screenshot_service = ScreenshotService(request, self._browser)
            result = screenshot_service.takeScreenshots()

            if result != OperationResult.SUCCEED:
                logger.error("Taking board screenshots failed for board '%s'", request.board_id)
                return OperationResult.FAILED

        result = export_processor.exportBoard(request)

        if result == OperationResult.SUCCEED:
            logger.info("Successfully exported board '%s'", request.board_id)
        else:
            logger.error("Failed to export board '%s'", request.board_id)

        return result

    def _waitForExportRequest(self) -> Union[ExportRequest, None]:
        try:
            raw = self.redis_manager.blockingGetFirstFromQueue(timeout=_BLPOP_TIMEOUT)
            if raw is None:
                return None
            data = json.loads(raw)
            return ExportRequest(
                request_id=data["request_id"],
                board_id=data["board_id"],
                sender_jwt=data["sender_jwt"],
                sender_email=data["sender_email"],
                file_type=FileType[data["file_type"]],
                board_metadata=data.get("board_metadata"),
                canvas_data=data.get("canvas_data"),
                request_time_stamp=datetime.datetime.fromisoformat(data["request_time_stamp"]),
            )
        except (KeyError, json.JSONDecodeError) as e:
            logger.error("_waitForExportRequest failed to parse job: %s", e)
            return None