from typing import List, Optional
from fastapi import APIRouter, Query, Depends
from app.services.search_service import SearchService
from app.models.other_models import SearchResult

router = APIRouter()
search_service = SearchService()

@router.get("/search/", response_model=List[SearchResult])
async def search(
    q: str = Query(..., description="搜索关键词"),
    project_id: Optional[str] = Query(None, description="项目ID，用于限制搜索范围"),
    target_types: List[str] = Query(
        ["project", "task", "comment", "sprint", "board", "tag"],
        description="要搜索的目标类型"
    ),
    skip: int = Query(0, description="跳过的结果数量"),
    limit: int = Query(50, description="返回的最大结果数量")
) -> List[SearchResult]:
    """
    统一的搜索接口
    
    - **q**: 搜索关键词
    - **project_id**: 项目ID，用于限制搜索范围
    - **target_types**: 要搜索的目标类型列表
    - **skip**: 跳过的结果数量
    - **limit**: 返回的最大结果数量
    
    返回搜索结果列表，按相关度排序
    """
    return await search_service.search(
        query=q,
        target_types=target_types,
        project_id=project_id,
        skip=skip,
        limit=limit
    ) 