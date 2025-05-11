from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.base_models import MongoBaseModel, PyObjectId

class ProjectDocumentation(MongoBaseModel):
    project_id: PyObjectId
    title: str
    content: str  # Markdown格式内容
    path: Optional[str] = None  # 文档的路径
    tags: List[str] = []
    author_id: Optional[PyObjectId] = None
    last_modified_by: Optional[PyObjectId] = None
    is_deleted: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class DocumentationVersion(MongoBaseModel):
    doc_id: PyObjectId
    title: str
    content: str
    edited_by: Optional[PyObjectId] = None
    version_number: int
    change_summary: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class DocCreate(BaseModel):
    project_id: PyObjectId
    title: str
    content: str
    path: Optional[str] = None
    tags: Optional[List[str]] = None

class DocUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    path: Optional[str] = None
    tags: Optional[List[str]] = None
    change_summary: Optional[str] = None

class DocGenerateRequest(BaseModel):
    source_files: List[str]  # 文件路径列表
    target_format: str = "markdown"
    include_code: bool = True
    doc_type: str = "technical"  # technical, api, user, etc. 