from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.models.base_models import MongoBaseModel, PyObjectId

# 活動日誌模型
class ActivityLogEntry(MongoBaseModel):
    user_id: PyObjectId
    action_type: str
    project_id: Optional[PyObjectId] = None
    target_type: str
    target_id: Optional[PyObjectId] = None
    details: Dict[str, Any] = {}
    timestamp: datetime

# 通知模型
class Notification(MongoBaseModel):
    recipient_id: PyObjectId
    sender_id: Optional[PyObjectId] = None
    type: str
    message: str
    target_type: str
    target_id: PyObjectId
    is_read: bool = False
    created_at: datetime

# 創建關係請求體模型
class RelationshipCreate(BaseModel):
    target_task_id: PyObjectId
    type: str

# 關係響應模型
class Relationship(MongoBaseModel):
    project_id: PyObjectId
    type: str
    source_task_id: PyObjectId
    target_task_id: PyObjectId
    created_by: PyObjectId
    created_at: datetime

# 標籤響應模型
class Tag(MongoBaseModel):
    name: str
    project_id: Optional[PyObjectId] = None
    usage_count: int = 0
    created_at: datetime
    updated_at: datetime

# 搜尋結果模型
class SearchResult(BaseModel):
    type: str
    id: str
    score: float
    highlight: Optional[str] = None
    data: Dict[str, Any] = {}
