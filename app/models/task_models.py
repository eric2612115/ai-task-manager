from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.models.base_models import MongoBaseModel, PyObjectId

# 創建任務請求體模型
class TaskCreate(BaseModel):
    summary: str
    project_id: PyObjectId
    description: Optional[str] = None
    status: str
    priority: Optional[str] = None
    task_type: Optional[str] = None
    assignee_id: Optional[PyObjectId] = None
    due_date: Optional[datetime] = None
    sprint_id: Optional[PyObjectId] = None
    board_column_id: Optional[PyObjectId] = None
    order_in_column: Optional[float] = None
    mermaid_syntax: Optional[str] = None
    tags: List[str] = []

# 更新任務請求體模型
class TaskUpdate(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    task_type: Optional[str] = None
    assignee_id: Optional[PyObjectId] = None
    due_date: Optional[datetime] = None
    sprint_id: Optional[PyObjectId] = None
    mermaid_syntax: Optional[str] = None
    tags: Optional[List[str]] = None
    __v: Optional[int] = None

# 任務移動請求體模型
class TaskMove(BaseModel):
    target_column_id: PyObjectId
    position: float
    __v: Optional[int] = None

# 任務響應模型
class Task(MongoBaseModel):
    project_id: PyObjectId
    summary: str
    description: Optional[str] = None
    status: str
    priority: Optional[str] = None
    task_type: Optional[str] = None
    assignee_id: Optional[PyObjectId] = None
    reporter_id: PyObjectId
    due_date: Optional[datetime] = None
    sprint_id: Optional[PyObjectId] = None
    board_column_id: Optional[PyObjectId] = None
    order_in_column: Optional[float] = None
    mermaid_syntax: Optional[str] = None
    tags: List[str] = []
    attachments: List[PyObjectId] = []
    created_at: datetime
    updated_at: datetime
    __v: int = 0
    description_embedding: Optional[List[float]] = None
    summary_embedding: Optional[List[float]] = None
