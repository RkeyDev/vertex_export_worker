from app.dataTypes.ExportRequest import ExportRequest
from app.dataTypes.OperationResult import OperationResult
from app.strategies.ExportProcessor import ExportProcessor

class ImageExportService(ExportProcessor):
    
    def requiresScreenshots() -> bool:
        return True
     
    def exportBoard(exportRequest: ExportRequest) -> OperationResult:
        pass