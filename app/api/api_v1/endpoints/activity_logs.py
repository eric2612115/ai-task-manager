from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from starlette.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
from bson import ObjectId

from app.db.mongodb import mongodb
from app.models.other_models import ActivityLogEntry

router = APIRouter()

# 獲取當前用戶ID (暫時固定返回一個測試用戶ID)
async def get_current_user_id():
    # 實際應用中，應該從JWT令牌或session中獲取經過認證的用戶ID
    # 這里為了測試，返回一個固定的測試用戶ID
    return "507f1f77bcf86cd799439011"  # 模擬用戶ID

@router.get("/projects/{project_id}", response_model=List[ActivityLogEntry])
async def get_project_activity_logs(
    project_id: str = Path(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    action_type: Optional[str] = None,
    target_type: Optional[str] = None,
    user_id: Optional[str] = None,
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
        
        # 構建查詢條件
        query = {"project_id": ObjectId(project_id)}
        
        if action_type:
            query["action_type"] = action_type
            
        if target_type:
            query["target_type"] = target_type
            
        if user_id:
            query["user_id"] = ObjectId(user_id)
        
        # 查詢活動日誌
        logs_cursor = mongodb.db.activity_logs.find(query).sort([("timestamp", -1)]).skip(skip).limit(limit)
        logs = await logs_cursor.to_list(length=limit)
        
        return logs
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching project activity logs: {str(e)}"
        )

@router.get("/users/{user_id}", response_model=List[ActivityLogEntry])
async def get_user_activity_logs(
    user_id: str = Path(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    action_type: Optional[str] = None,
    target_type: Optional[str] = None,
    project_id: Optional[str] = None,
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
        
        # 構建查詢條件
        query = {"user_id": ObjectId(user_id)}
        
        if action_type:
            query["action_type"] = action_type
            
        if target_type:
            query["target_type"] = target_type
            
        if project_id:
            query["project_id"] = ObjectId(project_id)
        
        # 查詢活動日誌
        logs_cursor = mongodb.db.activity_logs.find(query).sort([("timestamp", -1)]).skip(skip).limit(limit)
        logs = await logs_cursor.to_list(length=limit)
        
        return logs
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user activity logs: {str(e)}"
        )
