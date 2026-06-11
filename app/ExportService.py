from app.dataTypes.OperationResult import OperationResult
from app.dataTypes.ExportRequest import ExportRequest
from app.infrastructure.RedisManager import RedisManager
from app.strategies.ExportProcessor import ExportProcessor
from app.strategies.ImageExportService import ImageExportService
from app.strategies.MetadataExportService import MetadataExportService
from app.strategies.PdfExportService import PdfExportService
from app.dataTypes.FileType import FileType
from app.infrastructure.ScreenshotService import ScreenshotService

from typing import Union

class ExportService:
    
    
    
    def __init__(self):
        self.redisManager = RedisManager()
        
        self.exportTypeRoutes = {
            FileType.JPEG: ImageExportService,
            FileType.PDF: PdfExportService,
            FileType.VERTEX: MetadataExportService
        }
        
    def handlePendingRequest(self) -> OperationResult:
        request = self.getPendingExportRequest() #Get the ExportRequest object with the data from redis
        
        if(request == None):
            return OperationResult.FAILED
        
        #Get the correct export processor class according to the file type specified in the request
        exportProcessor: ExportProcessor = self.exportTypeRoutes.get(request.fileType)
        
        if exportProcessor.requiresScreenshots():
            screenshotSerivce = ScreenshotService(request)
            result = screenshotSerivce.takeScreenshots()
            
            if result != OperationResult.SUCCEED:
                return OperationResult.FAILED
        
        result = exportProcessor.exportBoard(request) #Start exporting board to the correct type
        
        return result
            
        
    
    def getPendingExportRequest(self) -> Union[ExportRequest, None]:
        pass