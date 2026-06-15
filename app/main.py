import logging
import signal
import sys
from app.ExportService import ExportService

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger(__name__)

_running = True


def _handle_shutdown(sig, frame):
    global _running
    logger.info("Shutdown signal received (%s), draining current job then exiting...", signal.Signals(sig).name)
    _running = False


if __name__ == "__main__":
    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)

    logger.info("Vertex export worker started. Initializing browser...")
    export_service = ExportService()

    try:
        while _running:
            export_service.handlePendingRequest()
    finally:
        export_service.shutdown()

    logger.info("Worker shut down cleanly.")
    sys.exit(0)