import json
import logging
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

from app.dataTypes.OperationResult import OperationResult
from app.dataTypes.ExportRequest import ExportRequest
from app.infrastructure.RedisManager import RedisManager

logger = logging.getLogger(__name__)


@dataclass
class DownloadReadyPayload:
    """
    Lightweight metadata pushed to the download queue after a successful export.
    The backend reads this to locate the file and notify the client.
    """
    request_id: str
    board_id: str
    sender_email: str
    file_type: str
    output_path: str
    created_at: str


class StorageService:
    """
    Responsible for signalling the Spring Boot backend that an exported file is
    ready for download.
    """

    DOWNLOAD_QUEUE_KEY = "download:queue"
    MAX_RETRIES = 3
    RETRY_DELAY_SEC = 2

    def __init__(self) -> None:
        self._redis_manager = RedisManager()

    def pub_download_ready(self, request: ExportRequest, output_path: str) -> OperationResult:
        # Ensure it is relative to the volume root (no leading slash)
        # If output_path is 'output/user/board/file.zip', this keeps it as is.
        clean_path = output_path.lstrip(os.sep)

        payload = DownloadReadyPayload(
            request_id=request.request_id,
            board_id=request.board_id,
            sender_email=request.sender_email,
            file_type=request.file_type.value,
            output_path=clean_path, 
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        try:
            serialised = json.dumps(asdict(payload))
        except (TypeError, ValueError) as exc:
            logger.error(
                "Failed to serialise download-ready payload for request '%s': %s",
                request.request_id, exc, exc_info=True,
            )
            return OperationResult.FAILED

        # Retry loop to handle transient Redis disconnections gracefully
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                result = self._redis_manager.pushToQueue(self.DOWNLOAD_QUEUE_KEY, serialised)
                
                if result == OperationResult.SUCCEED:
                    logger.info(
                        "Download-ready payload queued [requestId=%s, board=%s, path=%s]",
                        payload.request_id, payload.board_id, payload.output_path,
                    )
                    return OperationResult.SUCCEED
                
                logger.warning(
                    "Redis push returned failure for request '%s' (Attempt %d/%d)",
                    request.request_id, attempt, self.MAX_RETRIES
                )

            except Exception as exc:
                logger.warning(
                    "Redis push exception for request '%s' (Attempt %d/%d): %s",
                    request.request_id, attempt, self.MAX_RETRIES, exc
                )

            if attempt < self.MAX_RETRIES:
                time.sleep(self.RETRY_DELAY_SEC)

        logger.error(
            "Exhausted all retries pushing download-ready payload [requestId=%s]",
            request.request_id
        )
        return OperationResult.FAILED