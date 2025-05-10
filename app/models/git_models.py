from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from app.models.base_models import MongoBaseModel, PyObjectId

class GitCredential(MongoBaseModel):
    name: str  # 用户自定义名称
    platform: Literal["github", "gitlab"]
    auth_type: Literal["token", "oauth"] = "token"
    token: str  # 需要加密存储
    base_url: Optional[str] = None  # 企业版GitLab URL
    status: Literal["active", "invalid", "expired"] = "active"
    last_validated: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class GitCredentialCreate(BaseModel):
    name: str
    platform: Literal["github", "gitlab"]
    auth_type: Literal["token", "oauth"] = "token"
    token: str
    base_url: Optional[str] = None

class GitCredentialTest(BaseModel):
    platform: Literal["github", "gitlab"]
    token: str
    base_url: Optional[str] = None

class GitCredentialUpdate(BaseModel):
    name: Optional[str] = None
    token: Optional[str] = None
    base_url: Optional[str] = None
    status: Optional[Literal["active", "invalid", "expired"]] = None

class Repository(MongoBaseModel):
    credential_id: PyObjectId
    platform: Literal["github", "gitlab"]
    owner: str  # 组织或用户名
    name: str   # 仓库名
    full_name: str  # owner/name
    default_branch: str = "main"
    description: Optional[str] = None
    is_private: bool = False
    sync_enabled: bool = True
    sync_branches: List[str] = Field(default_factory=lambda: ["main", "master", "develop"])
    last_synced_at: Optional[datetime] = None
    last_commit_sha: Optional[str] = None
    sync_status: Literal["pending", "syncing", "completed", "failed"] = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class RepositoryCreate(BaseModel):
    credential_id: PyObjectId
    platform: Literal["github", "gitlab"]
    owner: str
    name: str
    full_name: str
    default_branch: str = "main"
    description: Optional[str] = None
    is_private: bool = False
    sync_branches: List[str] = Field(default_factory=lambda: ["main", "master", "develop"])

class RepositoryUpdate(BaseModel):
    default_branch: Optional[str] = None
    sync_enabled: Optional[bool] = None
    sync_branches: Optional[List[str]] = None
    description: Optional[str] = None

class SyncHistory(MongoBaseModel):
    repository_id: PyObjectId
    sync_type: Literal["full", "incremental"]
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: Literal["running", "completed", "failed"] = "running"
    from_commit: Optional[str] = None
    to_commit: Optional[str] = None
    files_processed: int = 0
    files_added: int = 0
    files_updated: int = 0
    files_deleted: int = 0
    error_message: Optional[str] = None 