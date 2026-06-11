from app.dataTypes.FileType import FileType
from datetime import datetime

class ExportRequest:
    def __init__(self, requestId: str, boardId: str, senderJwt: str, senderEmail: str, fileType: FileType, requestTimeStamp: datetime) -> None:
        self.requestId = requestId
        self.boardId = boardId
        self.senderJwt = senderJwt
        self.senderEmail = senderEmail
        self.fileType = fileType
        self.requestTimeStamp = requestTimeStamp