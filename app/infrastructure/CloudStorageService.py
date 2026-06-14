from app.dataTypes.OperationResult import OperationResult

class CloudStorageService:
    def __init__(self, local_directory_path: str) -> None:
        self.local_directory_path = local_directory_path
        
    def pushDirectoryToCloud() -> OperationResult:
        pass
    
    def getBucketDirectoryDownloadUrl() -> str:
        pass