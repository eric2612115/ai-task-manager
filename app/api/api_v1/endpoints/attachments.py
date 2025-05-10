import os
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, UploadFile
from starlette.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
from bson import ObjectId

from app.core.config import settings
from app.db.mongodb import mongodb
from app.db.redis import redis_manager
from app.models.base_models import Attachment
from app.services.activity_log_service import create_activity_log
from app.services.upload_service import save_upload_file, delete_attachment

router = APIRouter()

# 獲取當前用戶ID (暫時固定返回一個測試用戶ID)
async def get_current_user_id():
    # 實際應用中，應該從JWT令牌或session中獲取經過認證的用戶ID
    # 這里為了測試，返回一個固定的測試用戶ID
    return "507f1f77bcf86cd799439011"  # 模擬用戶ID

@router.get("/tasks/{task_id}/", response_model=List[Attachment])
async def get_task_attachments(
    task_id: str = Path(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    獲取任務的附件列表。
    """
    try:
        # 驗證任務存在
        task = await mongodb.db.tasks.find_one({"_id": ObjectId(task_id)})
        if not task:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Task not found")
        
        # 查詢附件
        attachments_cursor = mongodb.db.attachments.find({"attached_to_task": ObjectId(task_id)})
        attachments = await attachments_cursor.to_list(length=None)
        
        return attachments
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching task attachments: {str(e)}"
        )

@router.post("/tasks/{task_id}/", response_model=Attachment, status_code=HTTP_201_CREATED)
async def upload_task_attachment(
    task_id: str = Path(...),
    file: UploadFile = File(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    為任務上傳一個附件。
    """
    try:
        # 驗證任務存在
        task = await mongodb.db.tasks.find_one({"_id": ObjectId(task_id)})
        if not task:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Task not found")
        
        # 保存文件並創建附件記錄
        attachment = await save_upload_file(
            upload_file=file,
            uploaded_by=current_user_id,
            attached_to_task=task_id
        )
        
        # 更新任務的附件列表
        await mongodb.db.tasks.update_one(
            {"_id": ObjectId(task_id)},
            {"$push": {"attachments": attachment["_id"]}}
        )
        
        # 記錄活動日誌
        await create_activity_log(
            user_id=current_user_id,
            action_type="attachment_uploaded",
            target_type="attachment",
            target_id=str(attachment["_id"]),
            project_id=str(task["project_id"]),
            details={
                "file_name": attachment["file_name"],
                "file_size": attachment["file_size"],
                "content_type": attachment["content_type"],
                "attached_to_task": task_id
            }
        )
        
        # 發布附件上傳事件
        await redis_manager.publish_event(
            channel=f"task:{task_id}:updates",
            event_type="attachment.uploaded",
            data={
                "attachment_id": str(attachment["_id"]),
                "file_name": attachment["file_name"],
                "url": attachment["url"],
                "task_id": task_id
            }
        )
        
        return attachment
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading attachment: {str(e)}"
        )

@router.get("/comments/{comment_id}/", response_model=List[Attachment])
async def get_comment_attachments(
    comment_id: str = Path(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    獲取評論的附件列表。
    """
    try:
        # 驗證評論存在
        comment = await mongodb.db.comments.find_one({"_id": ObjectId(comment_id)})
        if not comment:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Comment not found")
        
        # 查詢附件
        attachments_cursor = mongodb.db.attachments.find({"attached_to_comment": ObjectId(comment_id)})
        attachments = await attachments_cursor.to_list(length=None)
        
        return attachments
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching comment attachments: {str(e)}"
        )

@router.post("/comments/{comment_id}/", response_model=Attachment, status_code=HTTP_201_CREATED)
async def upload_comment_attachment(
    comment_id: str = Path(...),
    file: UploadFile = File(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    為評論上傳一個附件。
    """
    try:
        # 驗證評論存在
        comment = await mongodb.db.comments.find_one({"_id": ObjectId(comment_id)})
        if not comment:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Comment not found")
        
        # 獲取關聯的任務信息
        task = await mongodb.db.tasks.find_one({"_id": comment["task_id"]})
        if not task:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Associated task not found")
        
        # 保存文件並創建附件記錄
        attachment = await save_upload_file(
            upload_file=file,
            uploaded_by=current_user_id,
            attached_to_comment=comment_id
        )
        
        # 更新評論的附件列表
        await mongodb.db.comments.update_one(
            {"_id": ObjectId(comment_id)},
            {"$push": {"attachments": attachment["_id"]}}
        )
        
        # 記錄活動日誌
        await create_activity_log(
            user_id=current_user_id,
            action_type="attachment_uploaded",
            target_type="attachment",
            target_id=str(attachment["_id"]),
            project_id=str(task["project_id"]),
            details={
                "file_name": attachment["file_name"],
                "file_size": attachment["file_size"],
                "content_type": attachment["content_type"],
                "attached_to_comment": comment_id,
                "task_id": str(comment["task_id"])
            }
        )
        
        # 發布附件上傳事件
        await redis_manager.publish_event(
            channel=f"task:{str(comment['task_id'])}:updates",
            event_type="comment.attachment_uploaded",
            data={
                "attachment_id": str(attachment["_id"]),
                "file_name": attachment["file_name"],
                "url": attachment["url"],
                "comment_id": comment_id,
                "task_id": str(comment["task_id"])
            }
        )
        
        return attachment
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading attachment: {str(e)}"
        )

@router.delete("/{attachment_id}")
async def delete_attachment_endpoint(
    attachment_id: str = Path(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    刪除附件。
    """
    try:
        # 查找附件
        attachment = await mongodb.db.attachments.find_one({"_id": ObjectId(attachment_id)})
        if not attachment:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Attachment not found")
        
        # 確定附件所屬的任務或評論
        task_id = None
        project_id = None
        comment_id = None
        
        if attachment.get("attached_to_task"):
            task_id = attachment["attached_to_task"]
            task = await mongodb.db.tasks.find_one({"_id": task_id})
            if task:
                project_id = task["project_id"]
                
                # 從任務的附件列表中移除
                await mongodb.db.tasks.update_one(
                    {"_id": task_id},
                    {"$pull": {"attachments": ObjectId(attachment_id)}}
                )
        
        if attachment.get("attached_to_comment"):
            comment_id = attachment["attached_to_comment"]
            comment = await mongodb.db.comments.find_one({"_id": comment_id})
            if comment:
                task = await mongodb.db.tasks.find_one({"_id": comment["task_id"]})
                if task:
                    task_id = task["_id"]
                    project_id = task["project_id"]
                
                # 從評論的附件列表中移除
                await mongodb.db.comments.update_one(
                    {"_id": comment_id},
                    {"$pull": {"attachments": ObjectId(attachment_id)}}
                )
        
        # 刪除附件記錄和文件
        success = await delete_attachment(attachment_id)
        if not success:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete attachment"
            )
        
        # 記錄活動日誌
        if project_id:
            await create_activity_log(
                user_id=current_user_id,
                action_type="attachment_deleted",
                target_type="attachment",
                target_id=attachment_id,
                project_id=str(project_id),
                details={
                    "file_name": attachment["file_name"],
                    "attached_to_task": str(task_id) if task_id else None,
                    "attached_to_comment": str(comment_id) if comment_id else None
                }
            )
        
        # 發布附件刪除事件
        if task_id:
            await redis_manager.publish_event(
                channel=f"task:{str(task_id)}:updates",
                event_type="attachment.deleted",
                data={
                    "attachment_id": attachment_id,
                    "file_name": attachment["file_name"],
                    "attached_to_task": str(task_id) if task_id else None,
                    "attached_to_comment": str(comment_id) if comment_id else None
                }
            )
        
        return {"message": "Attachment deleted successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting attachment: {str(e)}"
        )

@router.get("/{attachment_id}", response_model=Attachment)
async def get_attachment(
    attachment_id: str = Path(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    獲取單個附件的元信息。
    """
    try:
        attachment = await mongodb.db.attachments.find_one({"_id": ObjectId(attachment_id)})
        if not attachment:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Attachment not found")
        
        return attachment
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching attachment: {str(e)}"
        )
