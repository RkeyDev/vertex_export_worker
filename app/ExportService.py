from app.dataTypes.OperationResult import OperationResult
from app.dataTypes.ExportRequest import ExportRequest
from app.infrastructure.RedisManager import RedisManager
from app.strategies.ExportProcessor import ExportProcessor
from app.strategies.ImageExportService import ImageExportService
from app.strategies.MetadataExportService import MetadataExportService
from app.strategies.PdfExportService import PdfExportService
from app.dataTypes.FileType import FileType
from app.infrastructure.ScreenshotService import ScreenshotService
import datetime
import redis
import json
import logging

from typing import Union

class ExportService:
    
    
    
    def __init__(self):
        self.redis_manager = RedisManager()
        
        self.export_type_routes = {
            FileType.JPEG: ImageExportService,
            FileType.PDF: PdfExportService,
            FileType.VERTEX: MetadataExportService
        }
        
    def handlePendingRequest(self) -> OperationResult:
        request = self.getPendingExportRequest() #Get the ExportRequest object with the data from redis
        
        if request is None:
            return OperationResult.FAILED
        
        #Get the correct export processor class according to the file type specified in the request
        export_processor: ExportProcessor = self.export_type_routes.get(request.file_type)
        
        if export_processor is None:
            return OperationResult.FAILED
        
        if export_processor.requiresScreenshots():
            screenshot_service = ScreenshotService(request)
            result = screenshot_service.takeScreenshots()
            
            if result != OperationResult.SUCCEED:
                return OperationResult.FAILED
        
        result = export_processor.exportBoard(request) #Start exporting board to the correct type
        
        return result
            
        
    def getPendingExportRequest(self) -> Union[ExportRequest, None]:
        try:
            raw = self.redis_manager.getFirstFromQueue()
            if raw is None:
                return None
            data = json.loads(raw)
            return ExportRequest(
                request_id=data["request_id"],
                board_id=data["board_id"],
                sender_jwt=data["sender_jwt"],
                sender_email=data["sender_email"],
                file_type=FileType[data["file_type"]],
                request_time_stamp=datetime.datetime.fromisoformat(data["request_time_stamp"]),
            )
        except (KeyError, json.JSONDecodeError) as e:
            print(f"getPendingExportRequest failed: {e}")
            return None