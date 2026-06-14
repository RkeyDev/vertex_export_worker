import logging
from app.ExportService import ExportService

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

if __name__ == "__main__":
    export_service = ExportService()
    export_service.handlePendingRequest()