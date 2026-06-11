from abc import ABC, abstractmethod
from app.dataTypes.OperationResult import OperationResult
from app.dataTypes.ExportRequest import ExportRequest

class ExportProcessor(ABC):
    
    @abstractmethod
    def requiresScreenshots() -> bool:
        pass
     
    @abstractmethod
    def exportBoard(exportRequest: ExportRequest) -> OperationResult:
        pass