from abc import ABC, abstractmethod
from app.dataTypes.OperationResult import OperationResult
from app.dataTypes.ExportRequest import ExportRequest

class ExportProcessor(ABC):
    
    @staticmethod
    @abstractmethod
    def requiresScreenshots() -> bool:
        pass
     
    @staticmethod
    @abstractmethod
    def exportBoard(export_request: ExportRequest) -> OperationResult:
        pass