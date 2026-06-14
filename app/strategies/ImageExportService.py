from app.dataTypes.ExportRequest import ExportRequest
from app.dataTypes.OperationResult import OperationResult
from app.strategies.ExportProcessor import ExportProcessor

class ImageExportService(ExportProcessor):
    
    @staticmethod
    def requiresScreenshots() -> bool:
        return True
     
    @staticmethod
    def exportBoard(export_request: ExportRequest) -> OperationResult:
        pass