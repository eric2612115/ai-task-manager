from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from app.models.base_models import MongoBaseModel, PyObjectId

# 創建衝刺請求體模型
class SprintCreate(BaseModel):
    name: str
    project_id: PyObjectId
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    state: str

# 更新衝刺請求體模型
class SprintUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    state: Optional[str] = None

# 衝刺響應模型
class Sprint(MongoBaseModel):
    project_id: PyObjectId
    name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    state: str
    created_at: datetime
    updated_at: datetime
