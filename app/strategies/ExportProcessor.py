from abc import ABC, abstractmethod
from app.dataTypes.OperationResult import OperationResult
from app.dataTypes.ExportRequest import ExportRequest

class ExportProcessor(ABC):
    
    @staticmethod
    @abstractmethod
    def requiresScreenshots() -> bool:
        """Indicates whether this strategy requires a Playwright headless browser instance."""
        pass
     
    @staticmethod
    @abstractmethod
    def exportBoard(export_request: ExportRequest) -> OperationResult:
        pass