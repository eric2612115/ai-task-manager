import os
import uuid
import aiofiles
from typing import Optional
from fastapi import UploadFile, HTTPException
from datetime import datetime
from starlette.status import HTTP_413_REQUEST_ENTITY_TOO_LARGE, HTTP_400_BAD_REQUEST

from app.core.config import settings
from app.db.mongodb import mongodb
from bson import ObjectId

async def save_upload_file(
    upload_file: UploadFile,
    uploaded_by: str,
    attached_to_task: Optional[str] = None,
    attached_to_comment: Optional[str] = None
) -> dict:
    """
    保存上傳的文件並創建附件記錄
    
    Args:
        upload_file: 上傳的文件
        uploaded_by: 上傳用戶的ID
        attached_to_task: 關聯的任務ID (可選)
        attached_to_comment: 關聯的評論ID (可選)
        
    Returns:
        創建的附件記錄
    """
    # 檢查文件大小
    file_size = 0
    chunk_size = 1024 * 1024  # 1MB
    while chunk := await upload_file.read(chunk_size):
        file_size += len(chunk)
        if file_size > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE/1024/1024}MB"
            )
    
    # 重置文件讀取位置
    await upload_file.seek(0)
    
    # 檢查文件類型
    content_type = upload_file.content_type
    if content_type not in settings.ALLOWED_UPLOAD_TYPES:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {settings.ALLOWED_UPLOAD_TYPES}"
        )
    
    # 創建唯一的檔案名
    file_extension = os.path.splitext(upload_file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
    
    # 保存文件到本地存儲
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        async with aiofiles.open(file_path, 'wb') as out_file:
            while content := await upload_file.read(1024 * 1024):  # 1MB chunks
                await out_file.write(content)
    except Exception as e:
        # 如果保存失敗，刪除可能部分寫入的文件
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # 生成可訪問的URL
    # 在實際應用中，這可能是通過配置的CDN或Web服務器URL
    file_url = f"/uploads/{unique_filename}"
    
    # 創建附件記錄
    now = datetime.utcnow()
    attachment = {
        "file_name": upload_file.filename,
        "file_size": file_size,
        "content_type": content_type,
        "storage_path": file_path,
        "url": file_url,
        "uploaded_by": ObjectId(uploaded_by),
        "uploaded_at": now,
        "attached_to_task": ObjectId(attached_to_task) if attached_to_task else None,
        "attached_to_comment": ObjectId(attached_to_comment) if attached_to_comment else None
    }
    
    # 儲存附件元信息到數據庫
    result = await mongodb.db.attachments.insert_one(attachment)
    attachment["_id"] = result.inserted_id
    
    return attachment

async def delete_attachment(attachment_id: str) -> bool:
    """
    刪除附件及其關聯的文件
    
    Args:
        attachment_id: 附件ID
        
    Returns:
        是否成功刪除
    """
    # 獲取附件記錄
    attachment = await mongodb.db.attachments.find_one({"_id": ObjectId(attachment_id)})
    if not attachment:
        return False
    
    # 刪除實際檔案
    file_path = attachment.get("storage_path")
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file {file_path}: {str(e)}")
    
    # 刪除附件記錄
    result = await mongodb.db.attachments.delete_one({"_id": ObjectId(attachment_id)})
    
    return result.deleted_count > 0
