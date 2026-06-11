from dataTypes.ExportRequest import ExportRequest
from dataTypes.OperationResult import OperationResult
from app.strategies.ExportProcessor import ExportProcessor

class PdfExportService(ExportProcessor):
    
    @staticmethod
    def requiresScreenshots() -> bool:
        return True
     
    @staticmethod
    def exportBoard(exportRequest: ExportRequest) -> OperationResult:
        pass