from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from bson import ObjectId
import json

from app.db.mongodb import mongodb
from app.core.custom_json import CustomJSONEncoder

# 活动日志类型常量
ACTIVITY_TYPES = {
    # 任务相关
    "TASK_CREATED": "task_created",
    "TASK_UPDATED": "task_updated",
    "TASK_DELETED": "task_deleted",
    "TASK_STATUS_CHANGED": "status_changed",
    "TASK_ASSIGNED": "task_assigned",
    "TASK_PRIORITY_CHANGED": "priority_changed",
    "TASK_DUE_DATE_CHANGED": "due_date_changed",
    
    # 评论相关
    "COMMENT_ADDED": "comment_added",
    "COMMENT_UPDATED": "comment_updated",
    "COMMENT_DELETED": "comment_deleted",
    
    # 项目相关
    "PROJECT_CREATED": "project_created",
    "PROJECT_UPDATED": "project_updated",
    "PROJECT_DELETED": "project_deleted",
    
    # 看板相关
    "BOARD_CREATED": "board_created",
    "BOARD_UPDATED": "board_updated",
    "BOARD_COLUMNS_UPDATED": "board_columns_updated",
    "BOARD_DELETED": "board_deleted",
    
    # 附件相关
    "ATTACHMENT_ADDED": "attachment_added",
    "ATTACHMENT_DELETED": "attachment_deleted",
}

# 目标类型常量
TARGET_TYPES = {
    "TASK": "task",
    "COMMENT": "comment",
    "PROJECT": "project",
    "BOARD": "board",
    "ATTACHMENT": "attachment",
    "USER": "user",
}

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
    
    # 处理details中可能的datetime对象
    if details:
        # 先序列化再反序列化，确保所有datetime被正确转换
        details_str = json.dumps(details, cls=CustomJSONEncoder)
        details = json.loads(details_str)
        
        # 结构化变更记录
        if "changed_fields" in details and isinstance(details["changed_fields"], list):
            structured_changes = {}
            for field in details["changed_fields"]:
                if field in details.get("old_values", {}) and field in details.get("new_values", {}):
                    structured_changes[field] = {
                        "old": details["old_values"][field],
                        "new": details["new_values"][field]
                    }
            
            # 替换原始的变更记录
            if structured_changes:
                details["changes"] = structured_changes
    
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

async def get_activity_logs_by_project(
    project_id: str,
    action_type: Optional[str] = None,
    target_type: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    获取项目的活动日志
    
    Args:
        project_id: 项目ID
        action_type: 活动类型
        target_type: 目标实体类型
        user_id: 用户ID
        start_date: 开始日期
        end_date: 结束日期
        skip: 分页跳过数量
        limit: 分页限制数量
    
    Returns:
        活动日志列表
    """
    # 构建查询条件
    query = {"project_id": ObjectId(project_id)}
    
    if action_type:
        query["action_type"] = action_type
        
    if target_type:
        query["target_type"] = target_type
        
    if user_id:
        query["user_id"] = ObjectId(user_id)
    
    # 添加日期范围筛选
    if start_date or end_date:
        date_query = {}
        if start_date:
            date_query["$gte"] = start_date
        if end_date:
            date_query["$lte"] = end_date
        
        if date_query:
            query["timestamp"] = date_query
    
    # 查询活动日志
    logs_cursor = mongodb.db.activity_logs.find(query).sort([("timestamp", -1)]).skip(skip).limit(limit)
    logs = await logs_cursor.to_list(length=limit)
    
    return logs

async def get_activity_logs_by_user(
    user_id: str,
    action_type: Optional[str] = None,
    target_type: Optional[str] = None,
    project_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    获取用户的活动日志
    
    Args:
        user_id: 用户ID
        action_type: 活动类型
        target_type: 目标实体类型
        project_id: 项目ID
        start_date: 开始日期
        end_date: 结束日期
        skip: 分页跳过数量
        limit: 分页限制数量
    
    Returns:
        活动日志列表
    """
    # 构建查询条件
    query = {"user_id": ObjectId(user_id)}
    
    if action_type:
        query["action_type"] = action_type
        
    if target_type:
        query["target_type"] = target_type
        
    if project_id:
        query["project_id"] = ObjectId(project_id)
    
    # 添加日期范围筛选
    if start_date or end_date:
        date_query = {}
        if start_date:
            date_query["$gte"] = start_date
        if end_date:
            date_query["$lte"] = end_date
        
        if date_query:
            query["timestamp"] = date_query
    
    # 查询活动日志
    logs_cursor = mongodb.db.activity_logs.find(query).sort([("timestamp", -1)]).skip(skip).limit(limit)
    logs = await logs_cursor.to_list(length=limit)
    
    return logs

async def get_activity_logs_by_target(
    target_type: str,
    target_id: str,
    action_type: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    获取特定目标实体的活动日志
    
    Args:
        target_type: 目标实体类型
        target_id: 目标实体ID
        action_type: 活动类型
        user_id: 用户ID
        start_date: 开始日期
        end_date: 结束日期
        skip: 分页跳过数量
        limit: 分页限制数量
    
    Returns:
        活动日志列表
    """
    # 构建查询条件
    query = {
        "target_type": target_type,
        "target_id": ObjectId(target_id)
    }
    
    if action_type:
        query["action_type"] = action_type
        
    if user_id:
        query["user_id"] = ObjectId(user_id)
    
    # 添加日期范围筛选
    if start_date or end_date:
        date_query = {}
        if start_date:
            date_query["$gte"] = start_date
        if end_date:
            date_query["$lte"] = end_date
        
        if date_query:
            query["timestamp"] = date_query
    
    # 查询活动日志
    logs_cursor = mongodb.db.activity_logs.find(query).sort([("timestamp", -1)]).skip(skip).limit(limit)
    logs = await logs_cursor.to_list(length=limit)
    
    return logs

async def get_entity_change_history(
    target_type: str,
    target_id: str,
    field: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    获取实体特定字段的变更历史
    
    Args:
        target_type: 目标实体类型
        target_id: 目标实体ID
        field: 要查询的字段名称
    
    Returns:
        变更历史记录
    """
    # 构建查询条件
    query = {
        "target_type": target_type,
        "target_id": ObjectId(target_id)
    }
    
    # 如果指定了字段，查找包含该字段变更的记录
    if field:
        query["$or"] = [
            {f"details.{field}": {"$exists": True}},
            {f"details.changes.{field}": {"$exists": True}}
        ]
    
    # 查询活动日志
    logs_cursor = mongodb.db.activity_logs.find(query).sort([("timestamp", 1)])
    logs = await logs_cursor.to_list(length=None)
    
    # 提取变更历史
    history = []
    for log in logs:
        changes = {}
        
        # 处理不同格式的变更记录
        if "changes" in log.get("details", {}):
            # 新格式的结构化变更
            changes = log["details"]["changes"]
        else:
            # 旧格式或单字段变更
            for key, value in log.get("details", {}).items():
                if key != "changes" and key != "changed_fields":
                    if isinstance(value, dict) and "old" in value and "new" in value:
                        changes[key] = value
                    else:
                        changes[key] = {"new": value}
        
        # 如果指定了字段且该字段有变更，或者未指定字段
        if not field or field in changes:
            history_item = {
                "timestamp": log["timestamp"],
                "user_id": str(log["user_id"]) if log.get("user_id") else None,
                "action_type": log["action_type"],
                "changes": changes if not field else {field: changes.get(field)}
            }
            history.append(history_item)
    
    return history

async def get_activity_summary(
    project_id: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    获取活动统计摘要
    
    Args:
        project_id: 项目ID
        user_id: 用户ID
        start_date: 开始日期
        end_date: 结束日期
    
    Returns:
        活动统计摘要
    """
    # 构建查询条件
    query = {}
    
    if project_id:
        query["project_id"] = ObjectId(project_id)
    
    if user_id:
        query["user_id"] = ObjectId(user_id)
    
    # 添加日期范围筛选
    if start_date or end_date:
        date_query = {}
        if start_date:
            date_query["$gte"] = start_date
        if end_date:
            date_query["$lte"] = end_date
        
        if date_query:
            query["timestamp"] = date_query
    
    # 聚合查询
    pipeline = [
        {"$match": query},
        {"$group": {
            "_id": {
                "action_type": "$action_type",
                "target_type": "$target_type"
            },
            "count": {"$sum": 1}
        }},
        {"$group": {
            "_id": "$_id.target_type",
            "actions": {
                "$push": {
                    "action_type": "$_id.action_type",
                    "count": "$count"
                }
            },
            "total": {"$sum": "$count"}
        }}
    ]
    
    result = await mongodb.db.activity_logs.aggregate(pipeline).to_list(length=None)
    
    # 格式化结果
    summary = {
        "total_activities": 0,
        "by_target_type": {}
    }
    
    for item in result:
        target_type = item["_id"]
        summary["by_target_type"][target_type] = {
            "total": item["total"],
            "by_action": {action["action_type"]: action["count"] for action in item["actions"]}
        }
        summary["total_activities"] += item["total"]
    
    return summary
