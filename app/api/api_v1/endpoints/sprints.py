from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from pymongo import ReturnDocument
from starlette.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
from bson import ObjectId

from app.db.mongodb import mongodb
from app.db.redis import redis_manager
from app.models.sprint_models import Sprint, SprintCreate, SprintUpdate
from app.services.activity_log_service import create_activity_log

router = APIRouter()

# 獲取當前用戶ID (暫時固定返回一個測試用戶ID)
async def get_current_user_id():
    # 實際應用中，應該從JWT令牌或session中獲取經過認證的用戶ID
    # 這里為了測試，返回一個固定的測試用戶ID
    return "507f1f77bcf86cd799439011"  # 模擬用戶ID

@router.post("/projects/{project_id}/sprints/", response_model=Sprint, status_code=HTTP_201_CREATED)
async def create_sprint(
    project_id: str = Path(...),
    sprint_data: SprintCreate = Body(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    在指定專案下創建新衝刺。
    """
    try:
        # 確認專案存在
        project = await mongodb.db.projects.find_one({"_id": ObjectId(project_id)})
        if not project:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Project not found")
        
        now = datetime.utcnow()
        
        # 構建衝刺文檔
        sprint = {
            "project_id": ObjectId(project_id),
            "name": sprint_data.name,
            "start_date": sprint_data.start_date,
            "end_date": sprint_data.end_date,
            "state": sprint_data.state,
            "created_at": now,
            "updated_at": now
        }
        
        # 插入衝刺
        result = await mongodb.db.sprints.insert_one(sprint)
        if not result.inserted_id:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create sprint"
            )
        
        # 獲取插入後的完整衝刺文檔
        created_sprint = await mongodb.db.sprints.find_one({"_id": result.inserted_id})
        
        # 記錄活動日誌
        await create_activity_log(
            user_id=current_user_id,
            action_type="sprint_created",
            target_type="sprint",
            target_id=str(result.inserted_id),
            project_id=project_id,
            details={
                "name": sprint_data.name,
                "state": sprint_data.state
            }
        )
        
        # 發布衝刺創建事件
        await redis_manager.publish_event(
            channel=f"project:{project_id}:events",
            event_type="sprint.created",
            data={
                "sprint_id": str(result.inserted_id),
                "name": sprint_data.name,
                "state": sprint_data.state
            }
        )
        
        return created_sprint
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating sprint: {str(e)}"
        )

@router.get("/projects/{project_id}/sprints/", response_model=List[Sprint])
async def get_project_sprints(
    project_id: str = Path(...),
    state: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    獲取指定專案下的所有衝刺列表。
    """
    try:
        # 確認專案存在
        project = await mongodb.db.projects.find_one({"_id": ObjectId(project_id)})
        if not project:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Project not found")
        
        # 構建查詢條件
        query = {"project_id": ObjectId(project_id)}
        
        if state:
            query["state"] = state
        
        # 查詢衝刺
        sprints_cursor = mongodb.db.sprints.find(query).sort([("created_at", -1)]).skip(skip).limit(limit)
        sprints = await sprints_cursor.to_list(length=limit)
        
        return sprints
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching project sprints: {str(e)}"
        )

@router.get("/{sprint_id}", response_model=Sprint)
async def get_sprint(
    sprint_id: str = Path(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    獲取單個衝刺詳情。
    """
    try:
        sprint = await mongodb.db.sprints.find_one({"_id": ObjectId(sprint_id)})
        if not sprint:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Sprint not found")
        
        return sprint
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching sprint: {str(e)}"
        )

@router.put("/{sprint_id}", response_model=Sprint)
async def update_sprint(
    sprint_id: str = Path(...),
    sprint_data: SprintUpdate = Body(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    更新衝刺信息。
    """
    try:
        # 查找衝刺
        sprint = await mongodb.db.sprints.find_one({"_id": ObjectId(sprint_id)})
        if not sprint:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Sprint not found")
        
        # 收集變更信息，用於活動日誌
        changes = {}
        update_data = {}
        
        # 檢查並更新各個字段
        if sprint_data.name is not None and sprint_data.name != sprint["name"]:
            update_data["name"] = sprint_data.name
            changes["name"] = {"old": sprint["name"], "new": sprint_data.name}
        
        if sprint_data.start_date is not None and sprint_data.start_date != sprint.get("start_date"):
            update_data["start_date"] = sprint_data.start_date
            changes["start_date"] = {"old": sprint.get("start_date"), "new": sprint_data.start_date}
        
        if sprint_data.end_date is not None and sprint_data.end_date != sprint.get("end_date"):
            update_data["end_date"] = sprint_data.end_date
            changes["end_date"] = {"old": sprint.get("end_date"), "new": sprint_data.end_date}
        
        if sprint_data.state is not None and sprint_data.state != sprint["state"]:
            update_data["state"] = sprint_data.state
            changes["state"] = {"old": sprint["state"], "new": sprint_data.state}
        
        # 如果沒有變更，直接返回現有衝刺
        if not update_data:
            return sprint
        
        # 更新時間戳
        update_data["updated_at"] = datetime.utcnow()
        
        # 執行更新
        updated_sprint = await mongodb.db.sprints.find_one_and_update(
            {"_id": ObjectId(sprint_id)},
            {"$set": update_data},
            return_document=ReturnDocument.AFTER
        )
        
        # 記錄活動日誌
        await create_activity_log(
            user_id=current_user_id,
            action_type="sprint_updated",
            target_type="sprint",
            target_id=sprint_id,
            project_id=str(sprint["project_id"]),
            details=changes
        )
        
        # 如果狀態改變，記錄狀態變更活動
        if "state" in changes:
            await create_activity_log(
                user_id=current_user_id,
                action_type="sprint_state_changed",
                target_type="sprint",
                target_id=sprint_id,
                project_id=str(sprint["project_id"]),
                details={"state": changes["state"]}
            )
        
        # 發布衝刺更新事件
        await redis_manager.publish_event(
            channel=f"project:{str(sprint['project_id'])}:events",
            event_type="sprint.updated",
            data={
                "sprint_id": sprint_id,
                "updated_fields": list(changes.keys())
            }
        )
        
        return updated_sprint
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating sprint: {str(e)}"
        )

@router.delete("/{sprint_id}")
async def delete_sprint(
    sprint_id: str = Path(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    刪除衝刺，並將所有屬於該衝刺的任務的 sprint_id 設為 null。
    """
    try:
        # 查找衝刺
        sprint = await mongodb.db.sprints.find_one({"_id": ObjectId(sprint_id)})
        if not sprint:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Sprint not found")
        
        project_id = str(sprint["project_id"])
        sprint_name = sprint["name"]
        
        # 移除事务，直接执行数据库操作
        # 将所有属于该冲刺的任务的sprint_id设为null
        await mongodb.db.tasks.update_many(
            {"sprint_id": ObjectId(sprint_id)},
            {"$set": {"sprint_id": None}}
        )
        
        # 删除冲刺
        await mongodb.db.sprints.delete_one({"_id": ObjectId(sprint_id)})
        
        # 记录活动日志
        await create_activity_log(
            user_id=current_user_id,
            action_type="sprint_deleted",
            target_type="sprint",
            target_id=sprint_id,
            project_id=project_id,
            details={"name": sprint_name}
        )
        
        # 發布衝刺刪除事件
        await redis_manager.publish_event(
            channel=f"project:{project_id}:events",
            event_type="sprint.deleted",
            data={
                "sprint_id": sprint_id,
                "name": sprint_name
            }
        )
        
        return {"message": "Sprint deleted successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting sprint: {str(e)}"
        )
