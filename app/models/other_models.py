from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.models.base_models import MongoBaseModel, PyObjectId

# 活動日誌模型
class ActivityLogEntry(MongoBaseModel):
    user_id: PyObjectId = Field(..., description="執行操作的用戶ID")
    action_type: str = Field(..., description="活動類型，例如 'task_created', 'status_changed'")
    project_id: Optional[PyObjectId] = Field(None, description="關聯的專案ID")
    target_type: str = Field(..., description="活動目標實體類型，例如 'task', 'comment', 'project'")
    target_id: Optional[PyObjectId] = Field(None, description="活動目標實體的ID")
    details: Dict[str, Any] = Field(default={}, description="活動詳細信息，記錄變更內容或關鍵參數")
    timestamp: datetime = Field(..., description="活動發生的時間")

# 通知模型
class Notification(MongoBaseModel):
    recipient_id: PyObjectId = Field(..., description="接收通知的用戶ID")
    sender_id: Optional[PyObjectId] = Field(None, description="發送通知的用戶ID")
    type: str = Field(..., description="通知類型，例如 'task_assigned_to_me', 'mentioned_me'")
    message: str = Field(..., description="通知消息內容")
    target_type: str = Field(..., description="通知相關的實體類型，例如 'task', 'comment'")
    target_id: PyObjectId = Field(..., description="通知相關的實體ID")
    is_read: bool = Field(default=False, description="通知是否已讀")
    created_at: datetime = Field(..., description="通知創建時間")

# 用户通知偏好设置模型
class NotificationPreference(BaseModel):
    task_assigned_to_me: bool = Field(default=True, description="当任务分配给我时通知我")
    status_changed: bool = Field(default=True, description="当任务状态变更时通知我")
    comment_on_my_task: bool = Field(default=True, description="当有人在我的任务上评论时通知我")
    mentioned_me: bool = Field(default=True, description="当有人在评论中@我时通知我")
    due_date_approaching: bool = Field(default=True, description="当任务即将到期时通知我")
    task_overdue: bool = Field(default=True, description="当任务已逾期时通知我")

# 用户设置模型
class UserSettings(MongoBaseModel):
    user_id: PyObjectId = Field(..., description="用户ID")
    language: str = Field(default="zh-CN", description="用户界面语言")
    notification_preferences: NotificationPreference = Field(default_factory=NotificationPreference, description="通知偏好设置")
    theme: str = Field(default="light", description="界面主题")
    timezone: str = Field(default="Asia/Shanghai", description="用户时区")

# 活动摘要模型
class ActivitySummary(BaseModel):
    total_activities: int = Field(..., description="活动总数")
    by_target_type: Dict[str, Dict[str, Any]] = Field(..., description="按目标类型分组的活动统计")

# 变更历史记录模型
class ChangeHistoryItem(BaseModel):
    timestamp: datetime = Field(..., description="变更时间")
    user_id: Optional[str] = Field(None, description="执行变更的用户ID")
    action_type: str = Field(..., description="活动类型")
    changes: Dict[str, Dict[str, Any]] = Field(..., description="变更内容，格式为 {field: {old: value, new: value}}")

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
    navigation: Dict[str, str] = {}  # 包含所有可能的导航路径
    metadata: Dict[str, Any] = {}  # 额外的元数据，如创建时间、更新时间等
