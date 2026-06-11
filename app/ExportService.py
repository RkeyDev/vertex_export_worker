from app.dataTypes.OperationResult import OperationResult
from app.dataTypes.ExportRequest import ExportRequest
from app.infrastructure.RedisManager import RedisManager

from typing import Union

class ExportService:
    
    def __init__(self):
        self.redisManager = RedisManager
        
    def handlePendingRequest() -> OperationResult:
        pass
    
    def getPendingExportRequest() -> Union[ExportRequest, None]:
        pass