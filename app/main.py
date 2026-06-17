import logging
import os
import signal
import sys
import time

from app.ExportService import ExportService
from app.dataTypes.OperationResult import OperationResult
from app.infrastructure.StorageService import StorageService

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

_running = True


def _handle_shutdown(sig, _frame):
    global _running
    logger.info(
        "Shutdown signal received (%s), draining current job then exiting...",
        signal.Signals(sig).name,
    )
    _running = False


if __name__ == "__main__":
    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)

    logger.info("Vertex export worker started. Initialising browser...")
    export_service = ExportService()
    storage_service = StorageService()

    try:
        while _running:
            result, completed_request, output_path = export_service.handlePendingRequest()

            if result == OperationResult.SUCCEED and completed_request is not None and output_path:
                notify_result = storage_service.pub_download_ready(completed_request, output_path)
                
                if notify_result != OperationResult.SUCCEED:
                    logger.error(
                        "Export succeeded but download notification failed "
                        "[requestId=%s]. The client will not receive the file automatically.",
                        completed_request.request_id,
                    )
            elif result != OperationResult.SUCCEED:
                # Optional: Prevent tight CPU spinning if handlePendingRequest 
                # returns non-blocking failures (e.g. transient DB issues).
                time.sleep(1)

    finally:
        export_service.shutdown()

    logger.info("Worker shut down cleanly.")
    sys.exit(0)