from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from app.models.base_models import MongoBaseModel, PyObjectId

class EmbeddingRequest(BaseModel):
    repo_id: str
    force_regenerate: bool = False

class EmbeddingStatus(MongoBaseModel):
    repository_id: PyObjectId
    code_progress: float = 0.0  # 0.0 to 1.0
    docs_progress: float = 0.0  # 0.0 to 1.0
    status: str = "pending"  # pending, processing, completed, failed
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    total_code_files: int = 0
    processed_code_files: int = 0
    total_docs: int = 0
    processed_docs: int = 0
    error_message: Optional[str] = None

class SearchRequest(BaseModel):
    query: str
    collection: Optional[str] = None  # code, docs, or both
    limit: int = 5
    repo_id: str
    file_types: Optional[List[str]] = None  # 文件类型过滤，例如 ["python", "javascript"]

class SearchResult(BaseModel):
    file_id: str
    file_path: str
    file_name: str
    content: str
    language: Optional[str] = None
    score: float
    type: str  # code 或 doc
    metadata: Dict[str, Any] = {}

class RAGQueryRequest(BaseModel):
    query: str
    repo_id: str
    context_limit: int = 5
    llm_model: Optional[str] = None  # 可以指定使用哪个LLM模型
    llm_provider: Optional[str] = None  # openai, anthropic, google
    include_code: bool = True
    include_docs: bool = True
    temperature: float = 0.7
    max_tokens: int = 1000
    file_types: Optional[List[str]] = None  # 文件类型过滤

class RAGQueryResponse(BaseModel):
    query: str
    answer: str
    sources: List[SearchResult]
    execution_time: float  # 执行时间（秒）
    token_usage: Optional[Dict[str, int]] = None  # 使用的token数 

class UnifiedSearchRequest(BaseModel):
    query: str
    repo_id: Optional[str] = None
    project_id: Optional[str] = None
    include_code: bool = True
    include_docs: bool = True
    include_tasks: bool = True
    include_comments: bool = True
    include_external_docs: bool = True
    limit: int = 10

class UserInteraction(MongoBaseModel):
    user_id: PyObjectId
    document_id: str
    document_type: str  # code, doc, task, comment, external_doc
    interaction_type: str  # click, helpful, not_helpful, bookmark
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    project_id: Optional[PyObjectId] = None
    interaction_count: int = 1
    metadata: Dict[str, Any] = {} 