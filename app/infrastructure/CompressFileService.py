import os
import zipfile
from typing import Union


class CompressFileService:

    @staticmethod
    def compressFiles(sender_email: str, board_id: str) -> Union[str, None]:
        """
        Compresses the entire board output directory into a ZIP archive.
        Saved alongside the PDF at ./output/{sender_email}/{board_id}/

        :return: Path to the created ZIP file, or None if compression failed.
        """
        source_dir = os.path.join(".", "output", sender_email, board_id)
        output_zip = os.path.join(".", "output", sender_email, board_id, f"{board_id}.zip")

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
            print(f"[CompressFileService] Compression failed for board '{board_id}': {e}")
            return None