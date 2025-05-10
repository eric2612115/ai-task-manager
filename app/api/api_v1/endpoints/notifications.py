from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pymongo import ReturnDocument
from starlette.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR, HTTP_200_OK
from bson import ObjectId

from app.db.mongodb import mongodb
from app.db.redis import redis_manager
from app.models.other_models import Notification

router = APIRouter()

# 獲取當前用戶ID (暫時固定返回一個測試用戶ID)
async def get_current_user_id():
    # 實際應用中，應該從JWT令牌或session中獲取經過認證的用戶ID
    # 這里為了測試，返回一個固定的測試用戶ID
    return "507f1f77bcf86cd799439011"  # 模擬用戶ID

@router.get("/users/{user_id}/", response_model=List[Notification])
async def get_user_notifications(
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
        
        # 構建查詢條件
        query = {"recipient_id": ObjectId(user_id)}
        
        if is_read is not None:
            query["is_read"] = is_read
            
        if type:
            query["type"] = type
        
        # 查詢通知
        notifications_cursor = mongodb.db.notifications.find(query).sort([("created_at", -1)]).skip(skip).limit(limit)
        notifications = await notifications_cursor.to_list(length=limit)
        
        return notifications
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user notifications: {str(e)}"
        )

@router.put("/{notification_id}/read", response_model=Notification)
async def mark_notification_read(
    notification_id: str = Path(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    將指定通知標記為已讀。
    """
    try:
        # 查找通知
        notification = await mongodb.db.notifications.find_one({"_id": ObjectId(notification_id)})
        if not notification:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Notification not found")
        
        # 在實際應用中，應驗證當前用戶是否有權標記此通知
        # if str(notification["recipient_id"]) != current_user_id:
        #     raise HTTPException(status_code=403, detail="Access denied")
        
        # 如果通知已經是已讀狀態，直接返回
        if notification.get("is_read", False):
            return notification
        
        # 更新通知為已讀
        updated_notification = await mongodb.db.notifications.find_one_and_update(
            {"_id": ObjectId(notification_id)},
            {"$set": {"is_read": True}},
            return_document=ReturnDocument.AFTER
        )
        
        # 發布通知更新事件
        await redis_manager.publish_event(
            channel=f"user:{str(notification['recipient_id'])}:notifications",
            event_type="notification.updated",
            data={
                "notification_id": notification_id,
                "is_read": True
            }
        )
        
        return updated_notification
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error marking notification as read: {str(e)}"
        )

@router.put("/users/{user_id}/mark_all_read")
async def mark_all_notifications_read(
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
        
        # 更新所有未讀通知
        result = await mongodb.db.notifications.update_many(
            {
                "recipient_id": ObjectId(user_id),
                "is_read": False
            },
            {"$set": {"is_read": True}}
        )
        
        # 發布通知批量更新事件
        await redis_manager.publish_event(
            channel=f"user:{user_id}:notifications",
            event_type="notification.bulk_updated",
            data={
                "all_marked_read": True,
                "count": result.modified_count
            }
        )
        
        return {
            "message": "All notifications marked as read",
            "count": result.modified_count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error marking all notifications as read: {str(e)}"
        )
