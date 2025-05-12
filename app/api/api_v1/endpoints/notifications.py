from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from starlette.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR, HTTP_200_OK
from bson import ObjectId

from app.db.mongodb import mongodb
from app.db.redis import redis_manager
from app.models.other_models import Notification
from app.services.notification_service import (
    get_user_notifications, 
    mark_notification_as_read, 
    mark_all_notifications_as_read,
    get_unread_notification_count,
    update_user_notification_preferences,
    NOTIFICATION_TYPES
)

router = APIRouter()

# 獲取當前用戶ID (暫時固定返回一個測試用戶ID)
async def get_current_user_id():
    # 實際應用中，應該從JWT令牌或session中獲取經過認證的用戶ID
    # 這里為了測試，返回一個固定的測試用戶ID
    return "507f1f77bcf86cd799439011"  # 模擬用戶ID

@router.get("/users/{user_id}/", response_model=List[Notification])
async def get_notifications(
    user_id: str = Path(...),
    is_read: Optional[bool] = None,
    type: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    獲取指定用戶的通知列表。
    """
    try:
        # 在實際應用中，應驗證當前用戶是否有權查看目標用戶的通知
        # if current_user_id != user_id:
        #     raise HTTPException(status_code=403, detail="Access denied")
        
        notifications = await get_user_notifications(
            user_id=user_id,
            is_read=is_read,
            notification_type=type,
            skip=skip,
            limit=limit
        )
        
        return notifications
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user notifications: {str(e)}"
        )

@router.get("/users/{user_id}/count", response_model=Dict[str, int])
async def get_unread_count(
    user_id: str = Path(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    獲取用戶未讀通知數量。
    """
    try:
        # 在實際應用中，應驗證當前用戶是否有權查看目標用戶的通知
        # if current_user_id != user_id:
        #     raise HTTPException(status_code=403, detail="Access denied")
        
        count = await get_unread_notification_count(user_id)
        
        return {"count": count}
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching unread notification count: {str(e)}"
        )

@router.put("/{notification_id}/read", response_model=Dict[str, Any])
async def mark_notification_read(
    notification_id: str = Path(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    將指定通知標記為已讀。
    """
    try:
        success = await mark_notification_as_read(notification_id)
        
        if not success:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, 
                detail="Notification not found or could not be marked as read"
            )
        
        return {"success": True, "notification_id": notification_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error marking notification as read: {str(e)}"
        )

@router.put("/users/{user_id}/mark_all_read", response_model=Dict[str, Any])
async def mark_all_read(
    user_id: str = Path(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    將指定用戶的所有未讀通知標記為已讀。
    """
    try:
        # 在實際應用中，應驗證當前用戶是否有權標記目標用戶的通知
        # if current_user_id != user_id:
        #     raise HTTPException(status_code=403, detail="Access denied")
        
        count = await mark_all_notifications_as_read(user_id)
        
        return {
            "success": True,
            "message": "All notifications marked as read",
            "count": count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error marking all notifications as read: {str(e)}"
        )

@router.put("/users/{user_id}/preferences", response_model=Dict[str, Any])
async def update_notification_preferences(
    user_id: str = Path(...),
    preferences: Dict[str, bool] = Body(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    更新用户的通知偏好设置。
    
    可以设置每种通知类型是否接收。例如：
    ```
    {
        "task_assigned_to_me": true,
        "status_changed": false,
        "comment_on_my_task": true,
        "mentioned_me": true
    }
    ```
    """
    try:
        # 在實際應用中，應驗證當前用戶是否有權更新目標用戶的偏好設置
        # if current_user_id != user_id:
        #     raise HTTPException(status_code=403, detail="Access denied")
        
        # 验证通知类型是否有效
        for notification_type in preferences.keys():
            if notification_type not in NOTIFICATION_TYPES.values():
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid notification type: {notification_type}"
                )
        
        success = await update_user_notification_preferences(user_id, preferences)
        
        if not success:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update notification preferences"
            )
        
        return {
            "success": True,
            "message": "Notification preferences updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating notification preferences: {str(e)}"
        )

@router.get("/types", response_model=Dict[str, str])
async def get_notification_types():
    """
    获取所有支持的通知类型。
    """
    return NOTIFICATION_TYPES
