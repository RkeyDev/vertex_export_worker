from dataTypes.OperationResult import OperationResult
from dataTypes.ExportRequest import ExportRequest
from typing import Union

class ExportService:
    
    def __init__(self):
        self.redisManager = RedisManager
        
    def handlePendingRequest() -> OperationResult:
        pass
    
    def getPendingExportRequest() -> Union[ExportRequest, None]:
        pass