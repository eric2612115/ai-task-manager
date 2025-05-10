from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.models.base_models import MongoBaseModel, PyObjectId, BoardColumn

# 看板列創建模型
class BoardColumnCreate(BaseModel):
    name: str
    order: int
    status_mapping: List[str] = []

# 看板列更新模型
class BoardColumnUpdate(BaseModel):
    id: Optional[PyObjectId] = None
    name: Optional[str] = None
    order: Optional[int] = None
    status_mapping: Optional[List[str]] = None

# 創建看板請求體模型
class BoardCreate(BaseModel):
    name: str
    project_id: PyObjectId
    type: str
    columns: List[BoardColumnCreate] = []

# 更新看板請求體模型
class BoardUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    columns: Optional[List[BoardColumnUpdate]] = None

# 看板響應模型
class Board(MongoBaseModel):
    project_id: PyObjectId
    name: str
    type: str
    columns: List[BoardColumn] = []
    created_at: datetime
    updated_at: datetime
