from abc import ABC, abstractmethod
from dataTypes.OperationResult import OperationResult
from dataTypes.ExportRequest import ExportRequest

class ExportProcessor(ABC):
    
    @abstractmethod
    def requiresScreenshots() -> bool:
        pass
     
    @abstractmethod
    def exportBoard(exportRequest: ExportRequest) -> OperationResult:
        pass