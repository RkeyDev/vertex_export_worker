from app.dataTypes.ExportRequest import ExportRequest
from app.dataTypes.OperationResult import OperationResult
from app.strategies.ExportProcessor import ExportProcessor
from app.infrastructure.CompressFileService import CompressFileService


class ImageExportService(ExportProcessor):

    @staticmethod
    def screenshotsNumber() -> int:
        return -1 # -1 means to take all possible screenshots

    @staticmethod
    def requiresScreenshots() -> bool:
        return True

    @staticmethod
    def exportBoard(export_request: ExportRequest) -> OperationResult:
        zip_path = CompressFileService.compressFiles(export_request)

        if zip_path is None:
            return OperationResult.FAILED

        return OperationResult.SUCCEED