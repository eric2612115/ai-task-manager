from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.models.base_models import MongoBaseModel, PyObjectId, ProjectSettings, ProjectMethodology

# 創建專案請求體模型
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    methodology: ProjectMethodology = "Kanban"  # 默认为Kanban
    settings: Optional[ProjectSettings] = None

# 更新專案請求體模型
class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    methodology: Optional[ProjectMethodology] = None
    settings: Optional[ProjectSettings] = None

# 專案響應模型
class Project(MongoBaseModel):
    name: str
    description: Optional[str] = None
    methodology: ProjectMethodology = "Kanban"  # 默认为Kanban
    created_at: datetime
    updated_at: datetime
    members: List[PyObjectId] = []
    settings: ProjectSettings = Field(default_factory=ProjectSettings)
