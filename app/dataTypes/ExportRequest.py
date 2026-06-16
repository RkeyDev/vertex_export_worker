import os
from app.dataTypes.FileType import FileType
from datetime import datetime

class ExportRequest:
    def __init__(self, request_id: str, board_id: str, sender_jwt: str, sender_email: str, file_type: FileType, request_time_stamp: datetime, board_metadata:str = None, canvas_data:str =  None) -> None:
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
        """Canonical output directory for this export request."""
        timestamp_str = self.request_time_stamp.strftime("%Y-%m-%dT%H-%M-%S")
        return os.path.join(".", "output", self.sender_email, self.board_id, timestamp_str)