from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from starlette.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
from bson import ObjectId

from app.db.mongodb import mongodb
from app.models.other_models import ActivityLogEntry
from app.services.activity_log_service import (
    get_activity_logs_by_project,
    get_activity_logs_by_user,
    get_activity_logs_by_target,
    get_entity_change_history,
    get_activity_summary,
    ACTIVITY_TYPES,
    TARGET_TYPES
)

router = APIRouter()

# 獲取當前用戶ID (暫時固定返回一個測試用戶ID)
async def get_current_user_id():
    # 實際應用中，應該從JWT令牌或session中獲取經過認證的用戶ID
    # 這里為了測試，返回一個固定的測試用戶ID
    return "507f1f77bcf86cd799439011"  # 模擬用戶ID

@router.get("/projects/{project_id}", response_model=List[ActivityLogEntry])
async def get_project_activity_logs(
    project_id: str = Path(...),
    action_type: Optional[str] = None,
    target_type: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    獲取專案的活動日誌，支持過濾和分頁。
    """
    try:
        # 確認專案存在
        project = await mongodb.db.projects.find_one({"_id": ObjectId(project_id)})
        if not project:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Project not found")
        
        logs = await get_activity_logs_by_project(
            project_id=project_id,
            action_type=action_type,
            target_type=target_type,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=limit
        )
        
        return logs
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching project activity logs: {str(e)}"
        )

@router.get("/users/{user_id}", response_model=List[ActivityLogEntry])
async def get_user_activity_logs(
    user_id: str = Path(...),
    action_type: Optional[str] = None,
    target_type: Optional[str] = None,
    project_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    獲取用戶的活動日誌，支持過濾和分頁。
    """
    try:
        # 確認用戶存在
        user = await mongodb.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")
        
        logs = await get_activity_logs_by_user(
            user_id=user_id,
            action_type=action_type,
            target_type=target_type,
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=limit
        )
        
        return logs
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user activity logs: {str(e)}"
        )

@router.get("/targets/{target_type}/{target_id}", response_model=List[ActivityLogEntry])
async def get_target_activity_logs(
    target_type: str = Path(...),
    target_id: str = Path(...),
    action_type: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    獲取特定目標實體的活動日誌，支持過濾和分頁。
    """
    try:
        # 验证目标类型是否有效
        if target_type not in TARGET_TYPES.values():
            raise HTTPException(status_code=400, detail=f"Invalid target type: {target_type}")
        
        # 确认目标实体存在
        collection_name = f"{target_type}s" if target_type != "attachment" else "attachments"
        entity = await mongodb.db[collection_name].find_one({"_id": ObjectId(target_id)})
        if not entity:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"{target_type.capitalize()} not found")
        
        logs = await get_activity_logs_by_target(
            target_type=target_type,
            target_id=target_id,
            action_type=action_type,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=limit
        )
        
        return logs
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching target activity logs: {str(e)}"
        )

@router.get("/history/{target_type}/{target_id}", response_model=List[Dict[str, Any]])
async def get_change_history(
    target_type: str = Path(...),
    target_id: str = Path(...),
    field: Optional[str] = None,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    获取实体特定字段的变更历史。
    """
    try:
        # 验证目标类型是否有效
        if target_type not in TARGET_TYPES.values():
            raise HTTPException(status_code=400, detail=f"Invalid target type: {target_type}")
        
        history = await get_entity_change_history(
            target_type=target_type,
            target_id=target_id,
            field=field
        )
        
        return history
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching change history: {str(e)}"
        )

@router.get("/summary", response_model=Dict[str, Any])
async def get_summary(
    project_id: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    获取活动统计摘要。
    """
    try:
        # 如果提供了项目ID，确认项目存在
        if project_id:
            project = await mongodb.db.projects.find_one({"_id": ObjectId(project_id)})
            if not project:
                raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Project not found")
        
        # 如果提供了用户ID，确认用户存在
        if user_id:
            user = await mongodb.db.users.find_one({"_id": ObjectId(user_id)})
            if not user:
                raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")
        
        summary = await get_activity_summary(
            project_id=project_id,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching activity summary: {str(e)}"
        )

@router.get("/types", response_model=Dict[str, str])
async def get_activity_types():
    """
    获取所有支持的活动类型。
    """
    return ACTIVITY_TYPES

@router.get("/target_types", response_model=Dict[str, str])
async def get_target_types():
    """
    获取所有支持的目标实体类型。
    """
    return TARGET_TYPES
