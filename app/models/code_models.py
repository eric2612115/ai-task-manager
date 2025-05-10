from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.base_models import MongoBaseModel, PyObjectId

class CodeFile(MongoBaseModel):
    repository_id: PyObjectId
    file_path: str  # 相对于仓库根目录
    file_name: str
    content: str  # 直接存储源码
    code_language: Optional[str] = None  # 程序语言
    size_bytes: int
    line_count: int
    commit_sha: str
    branch: str
    last_modified: datetime
    author: Optional[str] = None
    is_deleted: bool = False  # 软删除标记
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class CodeFileVersion(MongoBaseModel):
    file_id: PyObjectId
    commit_sha: str
    content: str
    diff: Optional[str] = None  # 与上一版本的差异
    author: Optional[str] = None
    commit_message: Optional[str] = None
    committed_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CodeSearchQuery(BaseModel):
    repository_id: PyObjectId
    query: str
    file_extensions: Optional[List[str]] = None
    branch: Optional[str] = None
    limit: int = 50
    skip: int = 0 