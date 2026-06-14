import os
import zipfile
from typing import Union

from app.dataTypes.ExportRequest import ExportRequest


class CompressFileService:

    @staticmethod
    def compressFiles(export_request: ExportRequest) -> Union[str, None]:
        """
        Compresses the entire board output directory into a ZIP archive.
        Saved inside the export request's output directory.

        :return: Path to the created ZIP file, or None if compression failed.
        """
        source_dir = export_request.output_dir
        output_zip = os.path.join(source_dir, f"{export_request.board_id}.zip")

        if not os.path.isdir(source_dir):
            print(f"[CompressFileService] Source directory not found: {source_dir}")
            return None

        try:
            with zipfile.ZipFile(output_zip, mode='w', compression=zipfile.ZIP_DEFLATED) as archive:
                for root, _, files in os.walk(source_dir):
                    for file in files:
                        # Skip the zip file itself if it already exists
                        if file.endswith(".zip"):
                            continue

                        full_path = os.path.join(root, file)
                        relative_path = os.path.relpath(full_path, start=source_dir)
                        archive.write(full_path, arcname=relative_path)

            print(f"[CompressFileService] Archive created: {output_zip}")
            return output_zip

        except Exception as e:
            print(f"[CompressFileService] Compression failed for board '{export_request.board_id}': {e}")
            return None