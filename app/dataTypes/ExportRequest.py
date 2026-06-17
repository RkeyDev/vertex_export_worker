import os
import re
from datetime import datetime
from app.dataTypes.FileType import FileType

class ExportRequest:
    def __init__(
        self, 
        request_id: str, 
        board_id: str, 
        sender_jwt: str, 
        sender_email: str, 
        file_type: FileType, 
        request_time_stamp: datetime, 
        board_metadata: str = None, 
        canvas_data: str = None
    ) -> None:
        self.request_id = request_id
        self.board_id = board_id
        self.sender_jwt = sender_jwt
        self.sender_email = sender_email
        self.file_type = file_type
        self.board_metadata = board_metadata
        self.canvas_data = canvas_data
        self.request_time_stamp = request_time_stamp

    @property
    def output_dir(self) -> str:
        """
        Canonical output directory for this export request.
        Uses dash-delimiters for time components to maintain strict file-system compatibility 
        across varying host OS storage kernels (Windows/UNIX filesystem safety).
        """
        timestamp_str = self.request_time_stamp.strftime("%Y-%m-%dT%H-%M-%S")
        base_dir = os.getenv("OUTPUT_BASE_DIR", "./output")
        return os.path.join(base_dir, self.sender_email, self.board_id, timestamp_str)

    @classmethod
    def from_dict(cls, data: dict) -> "ExportRequest":
        """
        Factory constructor to safely map incoming JSON message brokers into instances.
        Defensively normalizes non-standard timestamp representations on the fly.
        """
        raw_timestamp = data.get("request_time_stamp")
        parsed_timestamp = cls._parse_timestamp_defensively(raw_timestamp)

        # Map string mapping representation to standard enum safely if provided as string
        raw_file_type = data.get("file_type")
        file_type_enum = (
            FileType[raw_file_type] if isinstance(raw_file_type, str) else FileType(raw_file_type)
        )

        return cls(
            request_id=data["request_id"],
            board_id=data["board_id"],
            sender_jwt=data["sender_jwt"],
            sender_email=data["sender_email"],
            file_type=file_type_enum,
            request_time_stamp=parsed_timestamp,
            board_metadata=data.get("board_metadata"),
            canvas_data=data.get("canvas_data")
        )

    @staticmethod
    def _parse_timestamp_defensively(timestamp_str: str) -> datetime:
        """
        Internal normalization engine. Resolves conflicts between standard ISO strings 
        and filesystem-safe dash-delimited timestamps.
        """
        if not timestamp_str:
            raise ValueError("The provided request_time_stamp artifact is missing or null.")

        try:
            # Optimal path for native standard compliant ISO format inputs
            return datetime.fromisoformat(timestamp_str)
        except ValueError:
            # Fallback for dash-delimited file path representations (e.g., '2026-06-16T12-24-49')
            if 'T' in timestamp_str:
                date_part, time_part = timestamp_str.split('T', 1)
                normalized_time = time_part.replace('-', ':')
                return datetime.fromisoformat(f"{date_part}T{normalized_time}")
            
            raise