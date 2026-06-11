from app.dataTypes.OperationResult import OperationResult

class CloudStorageService:
    def __init__(self, localDirectoryPath: str) -> None:
        self.localDirectoryPath = localDirectoryPath
        
    def pushDirectoryToCloud() -> OperationResult:
        pass
    
    def getBucketDirectoryDownloadUrl() -> str:
        pass