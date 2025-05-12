from datetime import datetime
from typing import Dict, Any, Optional, List
from bson import ObjectId
import json

from app.db.mongodb import mongodb
from app.db.redis import redis_manager
from app.core.custom_json import CustomJSONEncoder

# 通知类型常量
NOTIFICATION_TYPES = {
    "TASK_ASSIGNED": "task_assigned_to_me",
    "TASK_STATUS_CHANGED": "status_changed",
    "COMMENT_ADDED": "comment_on_my_task",
    "MENTIONED": "mentioned_me",
    "DUE_DATE_APPROACHING": "due_date_approaching",
    "TASK_OVERDUE": "task_overdue",
}

# 通知模板
NOTIFICATION_TEMPLATES = {
    "zh-CN": {
        NOTIFICATION_TYPES["TASK_ASSIGNED"]: "你被指派了新任務：{task_summary}",
        NOTIFICATION_TYPES["TASK_STATUS_CHANGED"]: "任務 '{task_summary}' 的狀態已從 '{old_status}' 變更為 '{new_status}'",
        NOTIFICATION_TYPES["COMMENT_ADDED"]: "有人在{relation}任務上添加了評論: {task_summary}",
        NOTIFICATION_TYPES["MENTIONED"]: "有人在評論中提及了你 @{username}",
        NOTIFICATION_TYPES["DUE_DATE_APPROACHING"]: "任務 '{task_summary}' 即將到期（還有{days_left}天）",
        NOTIFICATION_TYPES["TASK_OVERDUE"]: "任務 '{task_summary}' 已經逾期",
    },
    "en-US": {
        NOTIFICATION_TYPES["TASK_ASSIGNED"]: "You have been assigned a new task: {task_summary}",
        NOTIFICATION_TYPES["TASK_STATUS_CHANGED"]: "Task '{task_summary}' status changed from '{old_status}' to '{new_status}'",
        NOTIFICATION_TYPES["COMMENT_ADDED"]: "Someone commented on {relation} task: {task_summary}",
        NOTIFICATION_TYPES["MENTIONED"]: "Someone mentioned you @{username} in a comment",
        NOTIFICATION_TYPES["DUE_DATE_APPROACHING"]: "Task '{task_summary}' is due soon ({days_left} days left)",
        NOTIFICATION_TYPES["TASK_OVERDUE"]: "Task '{task_summary}' is overdue",
    }
}

async def create_notification(
    recipient_id: str,
    notification_type: str,
    target_type: str,
    target_id: str,
    sender_id: Optional[str] = None,
    template_vars: Optional[Dict[str, Any]] = None,
    language: str = "zh-CN"
) -> str:
    """
    创建通知并发布实时事件
    
    Args:
        recipient_id: 接收通知的用户ID
        notification_type: 通知类型
        target_type: 目标实体类型 (task, comment, project等)
        target_id: 目标实体ID
        sender_id: 发送通知的用户ID
        template_vars: 模板变量
        language: 语言代码
    
    Returns:
        创建的通知ID
    """
    # 获取通知模板
    templates = NOTIFICATION_TEMPLATES.get(language, NOTIFICATION_TEMPLATES["zh-CN"])
    template = templates.get(notification_type, "")
    
    # 格式化消息
    message = template
    if template_vars:
        try:
            message = template.format(**template_vars)
        except KeyError:
            # 如果格式化失败，使用原始模板
            pass
    
    # 创建通知对象
    notification = {
        "recipient_id": ObjectId(recipient_id),
        "sender_id": ObjectId(sender_id) if sender_id else None,
        "type": notification_type,
        "message": message,
        "target_type": target_type,
        "target_id": ObjectId(target_id),
        "is_read": False,
        "created_at": datetime.utcnow()
    }
    
    # 检查用户通知偏好设置
    user_settings = await mongodb.db.user_settings.find_one({"user_id": ObjectId(recipient_id)})
    if user_settings and "notification_preferences" in user_settings:
        # 如果用户关闭了此类通知，则不创建
        if not user_settings["notification_preferences"].get(notification_type, True):
            return None
    
    # 检查是否需要聚合通知
    # 例如，如果短时间内同一任务有多次状态变更，只保留最新的
    if notification_type == NOTIFICATION_TYPES["TASK_STATUS_CHANGED"]:
        # 查找最近30分钟内同一任务的状态变更通知
        thirty_mins_ago = datetime.utcnow().replace(microsecond=0) - datetime.timedelta(minutes=30)
        existing_notification = await mongodb.db.notifications.find_one({
            "recipient_id": ObjectId(recipient_id),
            "type": notification_type,
            "target_id": ObjectId(target_id),
            "is_read": False,
            "created_at": {"$gt": thirty_mins_ago}
        })
        
        if existing_notification:
            # 更新现有通知而不是创建新的
            result = await mongodb.db.notifications.update_one(
                {"_id": existing_notification["_id"]},
                {
                    "$set": {
                        "message": message,
                        "created_at": datetime.utcnow()
                    }
                }
            )
            notification_id = str(existing_notification["_id"])
        else:
            # 创建新通知
            result = await mongodb.db.notifications.insert_one(notification)
            notification_id = str(result.inserted_id)
    else:
        # 创建新通知
        result = await mongodb.db.notifications.insert_one(notification)
        notification_id = str(result.inserted_id)
    
    # 发布实时通知事件
    await redis_manager.publish_event(
        channel=f"user:{recipient_id}:notifications",
        event_type="notification.created",
        data={
            "notification_id": notification_id,
            "type": notification_type,
            "message": message,
            "target_type": target_type,
            "target_id": target_id,
            "created_at": datetime.utcnow().isoformat()
        }
    )
    
    return notification_id

async def mark_notification_as_read(notification_id: str) -> bool:
    """
    将通知标记为已读
    
    Args:
        notification_id: 通知ID
    
    Returns:
        是否成功标记
    """
    notification = await mongodb.db.notifications.find_one({"_id": ObjectId(notification_id)})
    if not notification:
        return False
    
    # 如果通知已经是已读状态，直接返回成功
    if notification.get("is_read", False):
        return True
    
    # 更新通知为已读
    result = await mongodb.db.notifications.update_one(
        {"_id": ObjectId(notification_id)},
        {"$set": {"is_read": True}}
    )
    
    # 发布通知更新事件
    if result.modified_count > 0:
        await redis_manager.publish_event(
            channel=f"user:{str(notification['recipient_id'])}:notifications",
            event_type="notification.updated",
            data={
                "notification_id": notification_id,
                "is_read": True
            }
        )
        return True
    
    return False

async def mark_all_notifications_as_read(user_id: str) -> int:
    """
    将用户的所有通知标记为已读
    
    Args:
        user_id: 用户ID
    
    Returns:
        标记为已读的通知数量
    """
    result = await mongodb.db.notifications.update_many(
        {
            "recipient_id": ObjectId(user_id),
            "is_read": False
        },
        {"$set": {"is_read": True}}
    )
    
    # 发布通知批量更新事件
    if result.modified_count > 0:
        await redis_manager.publish_event(
            channel=f"user:{user_id}:notifications",
            event_type="notification.bulk_updated",
            data={
                "all_marked_read": True,
                "count": result.modified_count
            }
        )
    
    return result.modified_count

async def get_user_notifications(
    user_id: str,
    is_read: Optional[bool] = None,
    notification_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    获取用户的通知列表
    
    Args:
        user_id: 用户ID
        is_read: 是否已读
        notification_type: 通知类型
        skip: 分页跳过数量
        limit: 分页限制数量
    
    Returns:
        通知列表
    """
    # 构建查询条件
    query = {"recipient_id": ObjectId(user_id)}
    
    if is_read is not None:
        query["is_read"] = is_read
        
    if notification_type:
        query["type"] = notification_type
    
    # 查询通知
    notifications_cursor = mongodb.db.notifications.find(query).sort([("created_at", -1)]).skip(skip).limit(limit)
    notifications = await notifications_cursor.to_list(length=limit)
    
    return notifications

async def get_unread_notification_count(user_id: str) -> int:
    """
    获取用户未读通知数量
    
    Args:
        user_id: 用户ID
    
    Returns:
        未读通知数量
    """
    count = await mongodb.db.notifications.count_documents({
        "recipient_id": ObjectId(user_id),
        "is_read": False
    })
    
    return count

async def update_user_notification_preferences(user_id: str, preferences: Dict[str, bool]) -> bool:
    """
    更新用户的通知偏好设置
    
    Args:
        user_id: 用户ID
        preferences: 通知偏好设置 {notification_type: enabled}
    
    Returns:
        是否成功更新
    """
    result = await mongodb.db.user_settings.update_one(
        {"user_id": ObjectId(user_id)},
        {"$set": {"notification_preferences": preferences}},
        upsert=True
    )
    
    return result.acknowledged 