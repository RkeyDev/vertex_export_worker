import os

from app.dataTypes.ExportRequest import ExportRequest
from app.dataTypes.OperationResult import OperationResult
from app.strategies.ExportProcessor import ExportProcessor


class ThumbnailExportService(ExportProcessor):

    @staticmethod
    def screenshotsNumber() -> int:
        return 1

    @staticmethod
    def requiresScreenshots() -> bool:
        return True

    @staticmethod
    def exportBoard(export_request: ExportRequest) -> OperationResult:
        source_path = os.path.join(export_request.output_dir, "cluster_output_01.jpeg")
        target_path = os.path.join(export_request.output_dir, f"{export_request.board_id}_thumbnail.jpeg")

        if not os.path.isfile(source_path):
            return OperationResult.FAILED

        try:
            os.replace(source_path, target_path)
        except OSError:
            return OperationResult.FAILED

        return OperationResult.SUCCEED
