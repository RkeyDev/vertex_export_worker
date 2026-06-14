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

logger = logging.getLogger(__name__)

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
            logger.error("Request was corrupted or empty")
            return OperationResult.FAILED
        
        #Get the correct export processor class according to the file type specified in the request
        export_processor: ExportProcessor = self.export_type_routes.get(request.file_type)
        
        if export_processor is None:
            logger.error("Invalid file type in request")
            return OperationResult.FAILED
        
        if export_processor.requiresScreenshots():
            screenshot_service = ScreenshotService(request)
            result = screenshot_service.takeScreenshots()
            
            if result != OperationResult.SUCCEED:
                logger.error("Taking board screenshots failed")
                return OperationResult.FAILED
        
        result = export_processor.exportBoard(request) #Start exporting board to the correct type
        
        if result == OperationResult.SUCCEED:
            logger.info("Successfully export board!")
        else:
            logger.error("Failed to export board")
        
        return result
            
        
    def getPendingExportRequest(self) -> Union[ExportRequest, None]:
        try:
            raw = self.redis_manager.getFirstFromQueue()
            if raw is None:
                logger.error("Redis queue is empty")
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
            logger.error(f"getPendingExportRequest failed: {e}")
            return None