from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class IndexFolderRequest(BaseModel):
    folder_path: Optional[str] = None

class IndexProgressStatus(BaseModel):
    is_indexing: bool = False
    current_stage: str = "idle" # Reading -> Extracting -> Understanding -> Indexing -> Complete
    total_files: int = 0
    processed_files: int = 0
    documents_count: int = 0
    images_count: int = 0
    other_count: int = 0
    current_file: Optional[str] = None
    last_indexed_at: Optional[datetime] = None
    error_message: Optional[str] = None

class IndexResponse(BaseModel):
    status: str
    message: str
    files_found: int
