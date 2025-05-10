from datetime import datetime
from typing import List, Optional, Dict, Any, Union, Annotated, Type, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict, BeforeValidator
from bson import ObjectId

# 自定義 ObjectId 驗證器函數
def validate_object_id(value) -> str:
    if value is None:
        return None
    if isinstance(value, str) and ObjectId.is_valid(value):
        return value
    if isinstance(value, ObjectId):
        return str(value)
    raise ValueError("Invalid ObjectId")

# 定義 PyObjectId 類型
PyObjectId = Annotated[str, BeforeValidator(validate_object_id)]

# 定義專案方法論
ProjectMethodology = Literal["Kanban", "Scrum"]

# 為所有MongoDB文檔模型提供基礎類
class MongoBaseModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={"example": {"id": "507f1f77bcf86cd799439011"}},
        arbitrary_types_allowed=True
    )

# 用戶模型 (簡化)
class User(MongoBaseModel):
    username: str
    full_name: Optional[str] = None
    email: Optional[str] = None

# 任務狀態轉換模型
class StatusTransition(BaseModel):
    from_status: str
    to_status: str
    type: Optional[str] = None  # e.g., 'manual', 'automatic'
    condition: Optional[Dict[str, Any]] = None

# 任務狀態模型
class TaskStatus(BaseModel):
    value: str
    label: str
    color: Optional[str] = None  # 添加颜色字段，默认为None

# 專案設置模型
class ProjectSettings(BaseModel):
    task_status_workflow: List[StatusTransition] = []
    task_statuses: List[TaskStatus] = []
    methodology: Optional[ProjectMethodology] = "Kanban"  # 默认为看板方法论

# 看板列模型 (嵌入)
class BoardColumn(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: str
    order: int
    status_mapping: List[str] = []

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

# 附件模型
class Attachment(MongoBaseModel):
    file_name: str
    file_size: int
    content_type: str
    storage_path: str
    url: str
    uploaded_by: PyObjectId
    uploaded_at: datetime
    attached_to_task: Optional[PyObjectId] = None
    attached_to_comment: Optional[PyObjectId] = None

# SSE 消息模型
class SseMessage(BaseModel):
    event: str
    data: Dict[str, Any]
    id: Optional[str] = None
    retry: int = 5000
