from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
from bson import ObjectId

from app.db.mongodb import mongodb
from app.models.other_models import SearchResult

router = APIRouter()

# 獲取當前用戶ID (暫時固定返回一個測試用戶ID)
async def get_current_user_id():
    # 實際應用中，應該從JWT令牌或session中獲取經過認證的用戶ID
    # 這里為了測試，返回一個固定的測試用戶ID
    return "507f1f77bcf86cd799439011"  # 模擬用戶ID

@router.get("/", response_model=List[SearchResult])
async def search(
    q: str = Query(..., min_length=1, description="搜尋關鍵字"),
    project_id: Optional[str] = None,
    target_types: Optional[List[str]] = Query(None, description="限定搜尋的實體類型，例如: task, comment, project"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    全文搜尋 Projects, Tasks, Comments, Sprints, Boards, Tags, Relationships, Attachments。
    """
    try:
        # 驗證 project_id 格式
        if project_id and not ObjectId.is_valid(project_id):
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid project ID format")
        
        # 驗證 target_types 是否為支持的類型
        valid_types = [
            "project", "task", "comment", "sprint", "board", 
            "tag", "relationship", "attachment"
        ]
        
        if target_types:
            for t in target_types:
                if t not in valid_types:
                    raise HTTPException(
                        status_code=HTTP_400_BAD_REQUEST, 
                        detail=f"Invalid target type: {t}. Valid types are: {', '.join(valid_types)}"
                    )
        
        # 如果沒有指定，默認搜尋所有類型
        if not target_types:
            target_types = valid_types
        
        # 收集所有搜尋結果
        all_results = []
        
        # 在每個指定的集合中搜尋
        if "project" in target_types:
            project_results = await search_projects(q, project_id, skip, limit)
            all_results.extend(project_results)
            
        if "task" in target_types:
            task_results = await search_tasks(q, project_id, skip, limit)
            all_results.extend(task_results)
            
        if "comment" in target_types:
            comment_results = await search_comments(q, project_id, skip, limit)
            all_results.extend(comment_results)
            
        if "sprint" in target_types:
            sprint_results = await search_sprints(q, project_id, skip, limit)
            all_results.extend(sprint_results)
            
        if "board" in target_types:
            board_results = await search_boards(q, project_id, skip, limit)
            all_results.extend(board_results)
            
        if "tag" in target_types:
            tag_results = await search_tags(q, skip, limit)
            all_results.extend(tag_results)
        
        # 按相關性分數排序
        all_results.sort(key=lambda x: x["score"], reverse=True)
        
        # 應用全局分頁
        paginated_results = all_results[skip:skip + limit]
        
        # 轉換成 SearchResult 模型
        return [
            SearchResult(
                type=result["type"],
                id=str(result["id"]),
                score=result["score"],
                highlight=result.get("highlight"),
                data=result.get("data", {})
            ) for result in paginated_results
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error performing search: {str(e)}"
        )

async def search_projects(q: str, project_id: Optional[str], skip: int, limit: int) -> List[dict]:
    """搜尋專案"""
    # 構建搜尋查詢
    search_query = {"$text": {"$search": q}}
    
    # 如果指定了 project_id，則只搜尋該專案
    if project_id:
        search_query["_id"] = ObjectId(project_id)
    
    # 執行聚合查詢
    pipeline = [
        {"$match": search_query},
        {"$project": {
            "score": {"$meta": "textScore"},
            "name": 1,
            "description": 1
        }},
        {"$sort": {"score": -1}},
        {"$skip": skip},
        {"$limit": limit}
    ]
    
    cursor = mongodb.db.projects.aggregate(pipeline)
    
    results = []
    async for doc in cursor:
        # 提取高亮文本
        highlight = doc.get("name", "")
        if len(highlight) > 100:
            highlight = highlight[:97] + "..."
        
        results.append({
            "type": "project",
            "id": doc["_id"],
            "score": doc["score"],
            "highlight": highlight,
            "data": {
                "name": doc.get("name"),
                "description": doc.get("description")
            }
        })
    
    return results

async def search_tasks(q: str, project_id: Optional[str], skip: int, limit: int) -> List[dict]:
    """搜尋任務"""
    # 構建搜尋查詢
    search_query = {"$text": {"$search": q}}
    
    # 如果指定了 project_id，則只搜尋該專案下的任務
    if project_id:
        search_query["project_id"] = ObjectId(project_id)
    
    # 執行聚合查詢
    pipeline = [
        {"$match": search_query},
        {"$project": {
            "score": {"$meta": "textScore"},
            "summary": 1,
            "description": 1,
            "status": 1,
            "project_id": 1
        }},
        {"$sort": {"score": -1}},
        {"$skip": skip},
        {"$limit": limit}
    ]
    
    cursor = mongodb.db.tasks.aggregate(pipeline)
    
    results = []
    async for doc in cursor:
        # 提取高亮文本
        highlight = doc.get("summary", "")
        if len(highlight) > 100:
            highlight = highlight[:97] + "..."
        
        results.append({
            "type": "task",
            "id": doc["_id"],
            "score": doc["score"],
            "highlight": highlight,
            "data": {
                "summary": doc.get("summary"),
                "status": doc.get("status"),
                "project_id": str(doc.get("project_id"))
            }
        })
    
    return results

async def search_comments(q: str, project_id: Optional[str], skip: int, limit: int) -> List[dict]:
    """搜尋評論"""
    # 構建搜尋查詢
    search_query = {"$text": {"$search": q}}
    
    # 如果指定了 project_id，需要先獲取該專案下的所有任務ID
    if project_id:
        task_ids = [
            task["_id"] async for task in mongodb.db.tasks.find(
                {"project_id": ObjectId(project_id)},
                {"_id": 1}
            )
        ]
        if task_ids:
            search_query["task_id"] = {"$in": task_ids}
        else:
            # 如果專案下沒有任務，則返回空結果
            return []
    
    # 執行聚合查詢
    pipeline = [
        {"$match": search_query},
        {"$project": {
            "score": {"$meta": "textScore"},
            "content": 1,
            "task_id": 1,
            "author_id": 1
        }},
        {"$sort": {"score": -1}},
        {"$skip": skip},
        {"$limit": limit}
    ]
    
    cursor = mongodb.db.comments.aggregate(pipeline)
    
    results = []
    async for doc in cursor:
        # 提取高亮文本 (從HTML內容中提取純文本，這里簡化處理)
        content = doc.get("content", "")
        # 簡單去除HTML標籤
        import re
        content_text = re.sub(r'<[^>]+>', '', content)
        highlight = content_text[:100] + "..." if len(content_text) > 100 else content_text
        
        # 獲取相關任務信息
        task = None
        if "task_id" in doc:
            task = await mongodb.db.tasks.find_one(
                {"_id": doc["task_id"]},
                {"summary": 1, "project_id": 1}
            )
        
        results.append({
            "type": "comment",
            "id": doc["_id"],
            "score": doc["score"],
            "highlight": highlight,
            "data": {
                "task_id": str(doc.get("task_id")),
                "author_id": str(doc.get("author_id")),
                "task_summary": task.get("summary") if task else None,
                "project_id": str(task.get("project_id")) if task else None
            }
        })
    
    return results

async def search_sprints(q: str, project_id: Optional[str], skip: int, limit: int) -> List[dict]:
    """搜尋衝刺"""
    # 構建搜尋查詢
    search_query = {"$text": {"$search": q}}
    
    # 如果指定了 project_id，則只搜尋該專案下的衝刺
    if project_id:
        search_query["project_id"] = ObjectId(project_id)
    
    # 執行聚合查詢
    pipeline = [
        {"$match": search_query},
        {"$project": {
            "score": {"$meta": "textScore"},
            "name": 1,
            "state": 1,
            "project_id": 1
        }},
        {"$sort": {"score": -1}},
        {"$skip": skip},
        {"$limit": limit}
    ]
    
    cursor = mongodb.db.sprints.aggregate(pipeline)
    
    results = []
    async for doc in cursor:
        results.append({
            "type": "sprint",
            "id": doc["_id"],
            "score": doc["score"],
            "highlight": doc.get("name", ""),
            "data": {
                "name": doc.get("name"),
                "state": doc.get("state"),
                "project_id": str(doc.get("project_id"))
            }
        })
    
    return results

async def search_boards(q: str, project_id: Optional[str], skip: int, limit: int) -> List[dict]:
    """搜尋看板"""
    # 構建搜尋查詢
    search_query = {"$text": {"$search": q}}
    
    # 如果指定了 project_id，則只搜尋該專案下的看板
    if project_id:
        search_query["project_id"] = ObjectId(project_id)
    
    # 執行聚合查詢
    pipeline = [
        {"$match": search_query},
        {"$project": {
            "score": {"$meta": "textScore"},
            "name": 1,
            "type": 1,
            "project_id": 1
        }},
        {"$sort": {"score": -1}},
        {"$skip": skip},
        {"$limit": limit}
    ]
    
    cursor = mongodb.db.boards.aggregate(pipeline)
    
    results = []
    async for doc in cursor:
        results.append({
            "type": "board",
            "id": doc["_id"],
            "score": doc["score"],
            "highlight": doc.get("name", ""),
            "data": {
                "name": doc.get("name"),
                "board_type": doc.get("type"),
                "project_id": str(doc.get("project_id"))
            }
        })
    
    return results

async def search_tags(q: str, skip: int, limit: int) -> List[dict]:
    """搜尋標籤"""
    # 構建搜尋查詢（標籤通常使用精確匹配或前綴匹配）
    search_query = {"name": {"$regex": f"^{q}", "$options": "i"}}
    
    # 執行查詢
    cursor = mongodb.db.tags.find(search_query).sort([("usage_count", -1)]).skip(skip).limit(limit)
    
    results = []
    async for doc in cursor:
        # 計算相關性分數（基於使用量）
        score = min(doc.get("usage_count", 0) / 100.0, 1.0)  # 最大值為 1.0
        
        results.append({
            "type": "tag",
            "id": doc["_id"],
            "score": score,
            "highlight": doc.get("name", ""),
            "data": {
                "name": doc.get("name"),
                "usage_count": doc.get("usage_count", 0)
            }
        })
    
    return results
