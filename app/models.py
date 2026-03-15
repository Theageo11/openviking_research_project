from pydantic import BaseModel, Field
from typing import Optional, List

'''定义功能接口'''

class RegisterResourceRequest(BaseModel):
    folder_path: str = Field(..., description="Absolute local folder path")


class RegisterResourceResponse(BaseModel):
    status: str
    folder_path: str
    resource_uri: Optional[str] = None
    message: str


class CreateSessionResponse(BaseModel):
    session_id: str


class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    folder_path: Optional[str] = None
    top_k: int = 5
    commit_after_response: bool = False


class QueryResponse(BaseModel):
    session_id: str
    snippet: str
    committed: bool


class CommitResponse(BaseModel):
    session_id: str
    status: str


class AgentUploadResponse(BaseModel):
    filename: str
    status: str
    message: str


class ListResourcesResponse(BaseModel):
    uploaded_folders: List[str]
