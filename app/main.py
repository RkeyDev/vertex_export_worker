from app.infrastructure.ScreenshotService import ScreenshotService
from app.dataTypes.ExportRequest import ExportRequest
from app.dataTypes.FileType import FileType

if __name__ == "__main__":
    s = ScreenshotService(ExportRequest(
        requestId="1",
        boardId= "889b8ba1-6451-4d41-b5c8-fb3f133868af",
        senderJwt="eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJyb2VpMTU3NkBnbWFpbC5jb20iLCJpYXQiOjE3ODExNzM0MDEsImV4cCI6MTc4MTI1OTgwMX0.1i80pSfTy2vnpRvn_biFkowh4mncIUp0d7zumx_Nrcs",
        senderEmail="roei1576@gmail.com",
        fileType=FileType.JPEG,
        requestTimeStamp=None
    ))
    
    s.saveScreenshotLocally()