from datetime import datetime
from typing import List
from fastapi import APIRouter, Body, Depends, HTTPException, Path
from pymongo import ReturnDocument
from starlette.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
from bson import ObjectId
import re

from app.db.mongodb import mongodb
from app.db.redis import redis_manager
from app.models.comment_models import Comment, CommentCreate, CommentUpdate
from app.services.activity_log_service import create_activity_log
from app.services.upload_service import delete_attachment

router = APIRouter()

# 獲取當前用戶ID (暫時固定返回一個測試用戶ID)
async def get_current_user_id():
    # 實際應用中，應該從JWT令牌或session中獲取經過認證的用戶ID
    # 這里為了測試，返回一個固定的測試用戶ID
    return "507f1f77bcf86cd799439011"  # 模擬用戶ID

def extract_mentioned_users(content: str) -> List[str]:
    """
    從評論內容中提取 @提及 的用戶名
    """
    # 簡單去除HTML標籤後提取用戶名
    text_content = re.sub(r'<[^>]+>', '', content)
    # 匹配 @username 格式
    mentions = re.findall(r'@(\w+)', text_content)
    # 返回唯一的用戶名列表
    return list(set(mentions))

async def create_notification(recipient_id: str, sender_id: str, type: str, message: str, target_type: str, target_id: str):
    """
    創建通知並發布實時事件
    """
    notification = {
        "recipient_id": ObjectId(recipient_id),
        "sender_id": ObjectId(sender_id),
        "type": type,
        "message": message,
        "target_type": target_type,
        "target_id": ObjectId(target_id),
        "is_read": False,
        "created_at": datetime.utcnow()
    }
    
    result = await mongodb.db.notifications.insert_one(notification)
    
    # 發布通知事件
    await redis_manager.publish_event(
        channel=f"user:{recipient_id}:notifications",
        event_type="notification.created",
        data={
            "notification_id": str(result.inserted_id),
            "type": type,
            "message": message,
            "target_type": target_type,
            "target_id": target_id
        }
    )

@router.post("/tasks/{task_id}/comments/", response_model=Comment, status_code=HTTP_201_CREATED)
async def create_comment(
    task_id: str = Path(...),
    comment_data: CommentCreate = Body(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    為任務添加評論。
    """
    try:
        # 驗證任務存在
        task = await mongodb.db.tasks.find_one({"_id": ObjectId(task_id)})
        if not task:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Task not found")
        
        now = datetime.utcnow()
        
        # 創建評論文檔
        comment = {
            "task_id": ObjectId(task_id),
            "author_id": ObjectId(current_user_id),
            "content": comment_data.content,
            "attachments": [],
            "created_at": now,
            "updated_at": now
        }
        
        # 插入評論
        result = await mongodb.db.comments.insert_one(comment)
        if not result.inserted_id:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create comment"
            )
        
        # 獲取插入後的完整評論文檔
        created_comment = await mongodb.db.comments.find_one({"_id": result.inserted_id})
        
        # 檢查評論中是否有 @提及 用戶
        mentioned_users = extract_mentioned_users(comment_data.content)
        
        # 記錄活動日誌
        await create_activity_log(
            user_id=current_user_id,
            action_type="comment_added",
            target_type="comment",
            target_id=str(result.inserted_id),
            project_id=str(task["project_id"]),
            details={
                "task_id": task_id,
                "content_preview": comment_data.content[:100] + "..." if len(comment_data.content) > 100 else comment_data.content,
                "mentioned_users": mentioned_users
            }
        )
        
        # 通知任務的指派人和報告人 (如果不是評論者本人)
        if task.get("assignee_id") and str(task["assignee_id"]) != current_user_id:
            await create_notification(
                recipient_id=str(task["assignee_id"]),
                sender_id=current_user_id,
                type="comment_on_my_task",
                message=f"有人在你負責的任務上添加了評論: {task['summary']}",
                target_type="comment",
                target_id=str(result.inserted_id)
            )
        
        if str(task["reporter_id"]) != current_user_id and (not task.get("assignee_id") or str(task["reporter_id"]) != str(task["assignee_id"])):
            await create_notification(
                recipient_id=str(task["reporter_id"]),
                sender_id=current_user_id,
                type="comment_on_my_task",
                message=f"有人在你報告的任務上添加了評論: {task['summary']}",
                target_type="comment",
                target_id=str(result.inserted_id)
            )
        
        # 處理 @提及
        for username in mentioned_users:
            # 查找被提及的用戶
            mentioned_user = await mongodb.db.users.find_one({"username": username})
            if mentioned_user and str(mentioned_user["_id"]) != current_user_id:
                await create_notification(
                    recipient_id=str(mentioned_user["_id"]),
                    sender_id=current_user_id,
                    type="mentioned_me",
                    message=f"有人在評論中提及了你 @{username}",
                    target_type="comment",
                    target_id=str(result.inserted_id)
                )
        
        # 發布評論創建事件
        await redis_manager.publish_event(
            channel=f"task:{task_id}:updates",
            event_type="comment.created",
            data={
                "comment_id": str(result.inserted_id),
                "task_id": task_id,
                "author_id": current_user_id,
                "content_preview": comment_data.content[:100] + "..." if len(comment_data.content) > 100 else comment_data.content
            }
        )
        
        # 發布專案事件
        await redis_manager.publish_event(
            channel=f"project:{str(task['project_id'])}:events",
            event_type="comment.created",
            data={
                "comment_id": str(result.inserted_id),
                "task_id": task_id,
                "task_summary": task["summary"],
                "author_id": current_user_id
            }
        )
        
        return created_comment
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating comment: {str(e)}"
        )

@router.get("/tasks/{task_id}/comments/", response_model=List[Comment])
async def get_task_comments(
    task_id: str = Path(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    獲取任務的所有評論列表。
    """
    try:
        # 驗證任務存在
        task = await mongodb.db.tasks.find_one({"_id": ObjectId(task_id)})
        if not task:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Task not found")
        
        # 查詢評論
        comments_cursor = mongodb.db.comments.find({"task_id": ObjectId(task_id)}).sort([("created_at", 1)])
        comments = await comments_cursor.to_list(length=None)
        
        return comments
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching task comments: {str(e)}"
        )

@router.put("/{comment_id}", response_model=Comment)
async def update_comment(
    comment_id: str = Path(...),
    comment_data: CommentUpdate = Body(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    更新評論內容。
    """
    try:
        # 查找評論
        comment = await mongodb.db.comments.find_one({"_id": ObjectId(comment_id)})
        if not comment:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Comment not found")
        
        # 在實際應用中，檢查用戶是否有權限更新此評論
        # if str(comment["author_id"]) != current_user_id:
        #     raise HTTPException(status_code=403, detail="You don't have permission to update this comment")
        
        # 檢查評論中是否有新的 @提及 用戶
        old_mentioned_users = set(extract_mentioned_users(comment["content"]))
        new_mentioned_users = set(extract_mentioned_users(comment_data.content))
        
        # 找出新增的提及
        new_mentions = new_mentioned_users - old_mentioned_users
        
        # 更新評論
        updated_comment = await mongodb.db.comments.find_one_and_update(
            {"_id": ObjectId(comment_id)},
            {
                "$set": {
                    "content": comment_data.content,
                    "updated_at": datetime.utcnow()
                }
            },
            return_document=ReturnDocument.AFTER
        )
        
        # 獲取關聯的任務
        task = await mongodb.db.tasks.find_one({"_id": comment["task_id"]})
        if task:
            # 記錄活動日誌
            await create_activity_log(
                user_id=current_user_id,
                action_type="comment_updated",
                target_type="comment",
                target_id=comment_id,
                project_id=str(task["project_id"]),
                details={
                    "task_id": str(comment["task_id"]),
                    "content_preview": comment_data.content[:100] + "..." if len(comment_data.content) > 100 else comment_data.content
                }
            )
            
            # 處理新增的 @提及
            for username in new_mentions:
                # 查找被提及的用戶
                mentioned_user = await mongodb.db.users.find_one({"username": username})
                if mentioned_user and str(mentioned_user["_id"]) != current_user_id:
                    await create_notification(
                        recipient_id=str(mentioned_user["_id"]),
                        sender_id=current_user_id,
                        type="mentioned_me",
                        message=f"有人在評論中提及了你 @{username}",
                        target_type="comment",
                        target_id=comment_id
                    )
            
            # 發布評論更新事件
            await redis_manager.publish_event(
                channel=f"task:{str(comment['task_id'])}:updates",
                event_type="comment.updated",
                data={
                    "comment_id": comment_id,
                    "task_id": str(comment["task_id"]),
                    "content_preview": comment_data.content[:100] + "..." if len(comment_data.content) > 100 else comment_data.content
                }
            )
        
        return updated_comment
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating comment: {str(e)}"
        )

@router.delete("/{comment_id}")
async def delete_comment(
    comment_id: str = Path(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    刪除評論及其所有關聯附件。
    """
    try:
        # 查找評論
        comment = await mongodb.db.comments.find_one({"_id": ObjectId(comment_id)})
        if not comment:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Comment not found")
        
        # 在實際應用中，檢查用戶是否有權限刪除此評論
        # if str(comment["author_id"]) != current_user_id:
        #     raise HTTPException(status_code=403, detail="You don't have permission to delete this comment")
        
        # 獲取任務信息
        task = await mongodb.db.tasks.find_one({"_id": comment["task_id"]})
        project_id = str(task["project_id"]) if task else None
        
        # 獲取評論的附件ID列表
        attachment_ids = comment.get("attachments", [])
        
        # 使用事務刪除評論及相關數據
        async with await mongodb.client.start_session() as session:
            async with session.start_transaction():
                # 刪除評論
                await mongodb.db.comments.delete_one({"_id": ObjectId(comment_id)}, session=session)
                
                # 獲取與評論關聯的附件記錄
                attachment_records = []
                async for attachment in mongodb.db.attachments.find(
                    {"attached_to_comment": ObjectId(comment_id)},
                    {"_id": 1, "storage_path": 1},
                    session=session
                ):
                    attachment_records.append(attachment)
                
                # 刪除評論的附件記錄
                if attachment_records:
                    await mongodb.db.attachments.delete_many(
                        {"attached_to_comment": ObjectId(comment_id)},
                        session=session
                    )
        
        # 事務之外：刪除附件文件
        for attachment in attachment_records:
            await delete_attachment(str(attachment["_id"]))
        
        # 記錄活動日誌
        if project_id:
            await create_activity_log(
                user_id=current_user_id,
                action_type="comment_deleted",
                target_type="comment",
                target_id=comment_id,
                project_id=project_id,
                details={
                    "task_id": str(comment["task_id"]),
                    "attachments_count": len(attachment_records)
                }
            )
        
        # 發布評論刪除事件
        if task:
            await redis_manager.publish_event(
                channel=f"task:{str(comment['task_id'])}:updates",
                event_type="comment.deleted",
                data={
                    "comment_id": comment_id,
                    "task_id": str(comment["task_id"])
                }
            )
        
        return {"message": "Comment deleted successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting comment: {str(e)}"
        )
