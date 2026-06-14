from app.ExportService import ExportService

if __name__ == "__main__":
    export_service = ExportService()
    export_service.handlePendingRequest()