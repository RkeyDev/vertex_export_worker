from app.dataTypes.FileType import FileType
from datetime import datetime

class ExportRequest:
    def __init__(self, request_id: str, board_id: str, sender_jwt: str, sender_email: str, file_type: FileType, request_time_stamp: datetime) -> None:
        self.request_id = request_id
        self.board_id = board_id
        self.sender_jwt = sender_jwt
        self.sender_email = sender_email
        self.file_type = file_type
        self.request_time_stamp = request_time_stamp