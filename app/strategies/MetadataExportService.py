from app.dataTypes.ExportRequest import ExportRequest
from app.dataTypes.OperationResult import OperationResult
from app.strategies.ExportProcessor import ExportProcessor

class MetadataExportService(ExportProcessor):
    
    @staticmethod
    def requiresScreenshots() -> False:
        return False
     
    @staticmethod
    def exportBoard(export_request: ExportRequest) -> OperationResult:
        pass