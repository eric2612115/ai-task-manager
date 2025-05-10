from datetime import datetime
from typing import Dict, Any, Optional
from bson import ObjectId

from app.db.mongodb import mongodb

async def create_activity_log(
    user_id: str,
    action_type: str,
    target_type: str,
    target_id: Optional[str] = None,
    project_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> str:
    """
    創建活動日誌記錄
    
    Args:
        user_id: 執行操作的用戶ID
        action_type: 活動類型 (如 'task_created', 'status_changed', 'user_assigned')
        target_type: 活動目標實體類型 (如 'task', 'comment', 'project')
        target_id: 活動目標實體的ID
        project_id: 關聯的專案ID
        details: 活動詳細信息，記錄變更內容或關鍵參數
    
    Returns:
        創建的活動日誌ID
    """
    now = datetime.utcnow()
    
    activity_log = {
        "user_id": ObjectId(user_id) if user_id else None,
        "action_type": action_type,
        "target_type": target_type,
        "target_id": ObjectId(target_id) if target_id else None,
        "project_id": ObjectId(project_id) if project_id else None,
        "details": details or {},
        "timestamp": now
    }
    
    result = await mongodb.db.activity_logs.insert_one(activity_log)
    return str(result.inserted_id)
