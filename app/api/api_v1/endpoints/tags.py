from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from starlette.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
from bson import ObjectId

from app.db.mongodb import mongodb
from app.models.other_models import Tag

router = APIRouter()

# 獲取當前用戶ID (暫時固定返回一個測試用戶ID)
async def get_current_user_id():
    # 實際應用中，應該從JWT令牌或session中獲取經過認證的用戶ID
    # 這里為了測試，返回一個固定的測試用戶ID
    return "507f1f77bcf86cd799439011"  # 模擬用戶ID

@router.get("/", response_model=List[Tag])
async def get_tags(
    search: Optional[str] = None,
    sort_by: Optional[str] = "name",
    sort_order: Optional[str] = "asc",
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    project_id: Optional[str] = None,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    獲取系統中所有已使用的標籤列表，用於前端自動完成或標籤選擇器。
    """
    try:
        # 構建查詢條件
        query = {"usage_count": {"$gt": 0}}  # 只返回使用過的標籤
        
        if search:
            # 使用正則表達式進行前綴匹配
            query["name"] = {"$regex": f"^{search}", "$options": "i"}
        
        if project_id:
            # 如果指定了專案ID，則只查詢該專案下的任務使用的標籤
            # 這需要一個複雜的聚合查詢
            task_tags = set()
            async for task in mongodb.db.tasks.find(
                {"project_id": ObjectId(project_id)},
                {"tags": 1}
            ):
                if "tags" in task:
                    task_tags.update(task["tags"])
                    
            if task_tags:
                query["name"] = {"$in": list(task_tags)}
            else:
                # 如果專案下沒有任務使用標籤，則返回空列表
                return []
        
        # 決定排序方式
        sort_direction = 1 if sort_order.lower() == "asc" else -1
        
        if sort_by == "usage_count":
            sort_options = [("usage_count", sort_direction)]
        else:  # 默認按名稱排序
            sort_options = [("name", sort_direction)]
        
        # 執行查詢
        tags_cursor = mongodb.db.tags.find(query).sort(sort_options).skip(skip).limit(limit)
        tags = await tags_cursor.to_list(length=limit)
        
        return tags
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching tags: {str(e)}"
        )
