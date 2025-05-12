from datetime import datetime
from typing import List, Optional, Dict
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from pymongo.errors import DuplicateKeyError
from starlette.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT, HTTP_500_INTERNAL_SERVER_ERROR, HTTP_400_BAD_REQUEST
from bson import ObjectId

from app.db.mongodb import mongodb
from app.db.redis import redis_manager
from app.models.other_models import Relationship, RelationshipCreate
from app.services.activity_log_service import create_activity_log

router = APIRouter()

# 反向關係類型對應表
INVERSE_RELATIONSHIP_TYPES = {
    "blocks": "is_blocked_by",
    "is_blocked_by": "blocks",
    "relates_to": "relates_to",  # 自反關係
    "parent": "child",
    "child": "parent",
    "duplicate": "is_duplicate_of",
    "is_duplicate_of": "duplicate"
}

# 获取依赖关系完成状态
COMPLETED_STATUSES = ["Resolved", "Closed", "已解决", "已关闭", "完成"]

# 定义工作状态
WORKING_STATUSES = ["In Progress", "进行中", "处理中"]

# 工具函数：验证任务依赖关系
async def validate_task_relationships(task_id: str, target_status: str) -> Dict:
    """
    验证任务是否满足依赖关系约束，可以变更为目标状态
    
    Args:
        task_id: 要验证的任务ID
        target_status: 目标状态
        
    Returns:
        Dict包含验证结果: {
            "valid": True/False,
            "blocking_tasks": [阻塞任务列表]
        }
    """
    result = {
        "valid": True,
        "blocking_tasks": []
    }
    
    # 只检查变更为工作中状态的情况
    if target_status not in WORKING_STATUSES:
        return result
        
    # 查找阻塞此任务的关系
    try:
        blocking_relationships = await mongodb.db.relationships.find({
            "target_task_id": ObjectId(task_id),
            "type": "is_blocked_by"
        }).to_list(100)
        
        if blocking_relationships:
            # 检查所有阻塞任务的状态
            blocking_task_ids = [ObjectId(rel["source_task_id"]) for rel in blocking_relationships]
            blocking_tasks = await mongodb.db.tasks.find({
                "_id": {"$in": blocking_task_ids},
                # 检查这些任务是否处于未完成状态
                "status": {"$nin": COMPLETED_STATUSES}
            }).to_list(100)
            
            if blocking_tasks:
                # 有阻塞任务还未完成
                result["valid"] = False
                result["blocking_tasks"] = [
                    {
                        "id": str(task["_id"]),
                        "summary": task.get("summary", "未知任务"),
                        "status": task.get("status")
                    }
                    for task in blocking_tasks
                ]
    except Exception as e:
        print(f"Error validating task relationships: {e}")
        # 出错时默认为有效，避免阻止正常操作
        pass
        
    return result

# 獲取當前用戶ID (暫時固定返回一個測試用戶ID)
async def get_current_user_id():
    # 實際應用中，應該從JWT令牌或session中獲取經過認證的用戶ID
    # 這里為了測試，返回一個固定的測試用戶ID
    return "507f1f77bcf86cd799439011"  # 模擬用戶ID

@router.post("/tasks/{source_task_id}/relationships/", response_model=Relationship, status_code=HTTP_201_CREATED)
async def create_relationship(
    source_task_id: str = Path(...),
    relationship_data: RelationshipCreate = Body(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    為任務創建一個關係到另一個任務。
    自動創建反向關係，並維護雙向關係的一致性。
    """
    try:
        # 驗證源任務存在
        source_task = await mongodb.db.tasks.find_one({"_id": ObjectId(source_task_id)})
        if not source_task:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Source task not found")
        
        # 驗證目標任務存在
        target_task = await mongodb.db.tasks.find_one({"_id": ObjectId(relationship_data.target_task_id)})
        if not target_task:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Target task not found")
        
        # 驗證源任務和目標任務不是同一個
        if source_task_id == relationship_data.target_task_id:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Cannot create a relationship between a task and itself"
            )
        
        # 驗證關係類型有效
        if relationship_data.type not in INVERSE_RELATIONSHIP_TYPES:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Invalid relationship type. Valid types are: {', '.join(INVERSE_RELATIONSHIP_TYPES.keys())}"
            )
        
        # 確認兩個任務屬於同一個專案
        if source_task["project_id"] != target_task["project_id"]:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Tasks must belong to the same project to create a relationship"
            )
        
        # 檢查是否已存在相同類型的關係
        existing_relationship = await mongodb.db.relationships.find_one({
            "source_task_id": ObjectId(source_task_id),
            "target_task_id": ObjectId(relationship_data.target_task_id),
            "type": relationship_data.type
        })
        
        if existing_relationship:
            raise HTTPException(
                status_code=HTTP_409_CONFLICT,
                detail=f"Relationship of type '{relationship_data.type}' already exists between these tasks"
            )
        
        now = datetime.utcnow()
        
        # 移除事务，直接创建双向关系
        # 创建正向关系
        relationship = {
            "project_id": source_task["project_id"],
            "type": relationship_data.type,
            "source_task_id": ObjectId(source_task_id),
            "target_task_id": ObjectId(relationship_data.target_task_id),
            "created_by": ObjectId(current_user_id),
            "created_at": now
        }
        
        result = await mongodb.db.relationships.insert_one(relationship)
        relationship["_id"] = result.inserted_id
        
        # 创建反向关系
        inverse_type = INVERSE_RELATIONSHIP_TYPES[relationship_data.type]
        
        inverse_relationship = {
            "project_id": source_task["project_id"],
            "type": inverse_type,
            "source_task_id": ObjectId(relationship_data.target_task_id),
            "target_task_id": ObjectId(source_task_id),
            "created_by": ObjectId(current_user_id),
            "created_at": now
        }
        
        inverse_result = await mongodb.db.relationships.insert_one(inverse_relationship)
        
        # 記錄活動日誌
        await create_activity_log(
            user_id=current_user_id,
            action_type="relationship_created",
            target_type="relationship",
            target_id=str(relationship["_id"]),
            project_id=str(source_task["project_id"]),
            details={
                "source_task_id": source_task_id,
                "target_task_id": str(relationship_data.target_task_id),
                "type": relationship_data.type
            }
        )
        
        # 發布關係創建事件
        await redis_manager.publish_event(
            channel=f"project:{str(source_task['project_id'])}:events",
            event_type="relationship.created",
            data={
                "relationship_id": str(relationship["_id"]),
                "source_task_id": source_task_id,
                "target_task_id": str(relationship_data.target_task_id),
                "type": relationship_data.type
            }
        )
        
        await redis_manager.publish_event(
            channel=f"task:{source_task_id}:updates",
            event_type="task.relationship_added",
            data={
                "task_id": source_task_id,
                "related_task_id": str(relationship_data.target_task_id),
                "relationship_type": relationship_data.type
            }
        )
        
        return relationship
        
    except DuplicateKeyError:
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="A relationship with the same properties already exists"
        )
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating relationship: {str(e)}"
        )

@router.get("/tasks/{task_id}/relationships/", response_model=List[Relationship])
async def get_task_relationships(
    task_id: str = Path(...),
    type: Optional[str] = None,
    direction: Optional[str] = "outgoing",  # "outgoing", "incoming", or "both"
    current_user_id: str = Depends(get_current_user_id)
):
    """
    獲取任務的關係列表，可以按關係類型和方向過濾。
    """
    try:
        # 驗證任務存在
        task = await mongodb.db.tasks.find_one({"_id": ObjectId(task_id)})
        if not task:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Task not found")
        
        # 構建查詢條件
        query = {}
        
        if direction == "outgoing" or direction == "both":
            query["source_task_id"] = ObjectId(task_id)
        elif direction == "incoming":
            query["target_task_id"] = ObjectId(task_id)
        else:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Invalid direction parameter. Valid values are: outgoing, incoming, both"
            )
        
        # 如果是 "both"，需要使用 $or 查詢
        if direction == "both":
            query = {
                "$or": [
                    {"source_task_id": ObjectId(task_id)},
                    {"target_task_id": ObjectId(task_id)}
                ]
            }
        
        if type:
            query["type"] = type
        
        # 執行查詢
        relationships_cursor = mongodb.db.relationships.find(query)
        relationships = await relationships_cursor.to_list(length=None)
        
        return relationships
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching task relationships: {str(e)}"
        )

@router.delete("/{relationship_id}")
async def delete_relationship(
    relationship_id: str = Path(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    刪除關係，同時刪除反向關係，維護雙向關係的一致性。
    """
    try:
        # 查找關係
        relationship = await mongodb.db.relationships.find_one({"_id": ObjectId(relationship_id)})
        if not relationship:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Relationship not found")
        
        # 移除事务，直接删除双向关系
        # 删除正向关系
        await mongodb.db.relationships.delete_one({"_id": ObjectId(relationship_id)})
        
        # 查找并删除反向关系
        inverse_type = INVERSE_RELATIONSHIP_TYPES.get(relationship["type"])
        
        await mongodb.db.relationships.delete_one({
            "source_task_id": relationship["target_task_id"],
            "target_task_id": relationship["source_task_id"],
            "type": inverse_type
        })
        
        # 記錄活動日誌
        await create_activity_log(
            user_id=current_user_id,
            action_type="relationship_deleted",
            target_type="relationship",
            target_id=relationship_id,
            project_id=str(relationship["project_id"]),
            details={
                "source_task_id": str(relationship["source_task_id"]),
                "target_task_id": str(relationship["target_task_id"]),
                "type": relationship["type"]
            }
        )
        
        # 發布關係刪除事件
        await redis_manager.publish_event(
            channel=f"project:{str(relationship['project_id'])}:events",
            event_type="relationship.deleted",
            data={
                "relationship_id": relationship_id,
                "source_task_id": str(relationship["source_task_id"]),
                "target_task_id": str(relationship["target_task_id"]),
                "type": relationship["type"]
            }
        )
        
        await redis_manager.publish_event(
            channel=f"task:{str(relationship['source_task_id'])}:updates",
            event_type="task.relationship_removed",
            data={
                "task_id": str(relationship["source_task_id"]),
                "related_task_id": str(relationship["target_task_id"]),
                "relationship_type": relationship["type"]
            }
        )
        
        return {"message": "Relationship deleted successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting relationship: {str(e)}"
        )
