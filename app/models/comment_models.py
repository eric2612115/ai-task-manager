from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from app.models.base_models import MongoBaseModel, PyObjectId

# 創建評論請求體模型
class CommentCreate(BaseModel):
    content: str

# 更新評論請求體模型
class CommentUpdate(BaseModel):
    content: str

# 評論響應模型
class Comment(MongoBaseModel):
    task_id: PyObjectId
    author_id: PyObjectId
    content: str
    attachments: List[PyObjectId] = []
    created_at: datetime
    updated_at: datetime
    content_embedding: Optional[List[float]] = None
