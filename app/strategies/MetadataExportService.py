from dataTypes.ExportRequest import ExportRequest
from dataTypes.OperationResult import OperationResult
from ExportProcessor import ExportProcessor

class MetadataExportService(ExportProcessor):
    
    def requiresScreenshots() -> False:
        return False
     
    def exportBoard(exportRequest: ExportRequest) -> OperationResult:
        pass