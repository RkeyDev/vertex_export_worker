from dataTypes.ExportRequest import ExportRequest
from dataTypes.OperationResult import OperationResult
from ExportProcessor import ExportProcessor

class PdfExportService(ExportProcessor):
    
    def requiresScreenshots() -> bool:
        return True
     
    def exportBoard(exportRequest: ExportRequest) -> OperationResult:
        pass