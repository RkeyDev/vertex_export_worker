from app.dataTypes.ExportRequest import ExportRequest
from app.dataTypes.OperationResult import OperationResult
from app.strategies.ExportProcessor import ExportProcessor
from pathlib import Path
import zipfile
import json
import logging

# Adhering to the established module-level logging practice
logger = logging.getLogger(__name__)


class MetadataExportService(ExportProcessor):
    
    @staticmethod
    def requiresScreenshots() -> bool:
        return False
     
    @staticmethod
    def exportBoard(export_request: ExportRequest) -> OperationResult:
        """
        Compiles structural metadata and canvas JSON payloads into a compressed .vertex archive.
        Ensures target file system directory allocations exist dynamically prior to streaming.
        """
        # Defensive check against missing critical payload data
        if export_request.board_metadata is None or export_request.canvas_data is None:
            logger.warning(
                f"Aborting export for board '{export_request.board_id}'. "
                f"Payload structural violation: board_metadata or canvas_data are null."
            )
            return OperationResult.FAILED
        
        metadata = export_request.board_metadata
        canvas = export_request.canvas_data

        try:
            # Cast the string target path into a structural Path object
            target_zip_path = Path(export_request.output_dir + f"/{export_request.board_id}.vertex")
            
            # Isolate the deep directory tree to support dynamic clean builds inside Docker
            parent_directory = target_zip_path.parent
            
            # Create structural directories concurrently without throwing race condition exceptions
            parent_directory.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Target distribution path verified: '{parent_directory}'")

            # Open the target file stream with ZIP deflation compression enabled
            with zipfile.ZipFile(target_zip_path, 'w', zipfile.ZIP_DEFLATED) as vertex_file:
                # Direct structural payload streaming eliminates local container disk IO waste
                vertex_file.writestr("metadata.json", json.dumps(metadata, indent=2))
                vertex_file.writestr("canvas.json", json.dumps(canvas, indent=2))

            logger.info(f"Successfully serialized and archived board '{export_request.board_id}' to location: {target_zip_path}")
            return OperationResult.SUCCESS

        except PermissionError as pe:
            logger.error(
                f"OS Write Violation. Worker lacks execution authorization to mutate file structure "
                f"at path '{export_request.output_dir}': {str(pe)}", 
                exc_info=True
            )
            return OperationResult.FAILED

        except (ValueError, TypeError) as json_err:
            logger.error(
                f"Failed to serialize engine components for board '{export_request.board_id}'. "
                f"Data structures contain non-serializable objects: {str(json_err)}", 
                exc_info=True
            )
            return OperationResult.FAILED

        except zipfile.BadZipFile as zip_err:
            logger.error(
                f"Compression layer system breakdown writing archive for board '{export_request.board_id}': "
                f"{str(zip_err)}", 
                exc_info=True
            )
            return OperationResult.FAILED

        except Exception as ex:
            logger.critical(
                f"Unexpected platform anomaly occurred during asset execution processing for board "
                f"'{export_request.board_id}': {str(ex)}", 
                exc_info=True
            )
            return OperationResult.FAILED