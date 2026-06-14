import os
import zipfile
from typing import Union

from app.dataTypes.ExportRequest import ExportRequest
from app.dataTypes.OperationResult import OperationResult
from app.strategies.ExportProcessor import ExportProcessor
from app.infrastructure.CompressFileService import CompressFileService


class ImageExportService(ExportProcessor):

    @staticmethod
    def requiresScreenshots() -> bool:
        return True

    @staticmethod
    def exportBoard(export_request: ExportRequest) -> OperationResult:
        board_id     = export_request.board_id
        sender_email = export_request.sender_email

        zip_path = CompressFileService.compressFiles(
            sender_email=sender_email,
            board_id=board_id,
        )

        if zip_path is None:
            return OperationResult.FAILED

        return OperationResult.SUCCEED