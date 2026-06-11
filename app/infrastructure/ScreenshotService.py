from dataTypes.OperationResult import OperationResult
from dataTypes.ExportRequest import ExportRequest

class ScreenshotService:
    
    def __init__(self, exportRequest: ExportRequest) -> None:
        self.exportRequest = exportRequest
        
    def saveScreenshotLocally() -> OperationResult:
        pass