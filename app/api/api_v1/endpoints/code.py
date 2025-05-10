from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from pydantic import BaseModel

from app.models.code_models import CodeSearchQuery
from app.services.code_service import CodeService
from app.core.utils import serialize_mongodb_doc

router = APIRouter()
code_service = CodeService()

@router.get("/repos/{repo_id}/tree", response_model=dict)
async def get_file_tree(repo_id: str, include_deleted: bool = False):
    """获取仓库文件树结构"""
    try:
        result = await code_service.get_file_tree(repo_id, include_deleted)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/files/{file_id}", response_model=dict)
async def get_file(file_id: str):
    """获取文件内容"""
    try:
        result = await code_service.get_file(file_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="File not found")
        
        return {
            "success": True,
            "data": serialize_mongodb_doc(result)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/repos/{repo_id}/files", response_model=dict)
async def get_file_by_path(repo_id: str, path: str):
    """根据路径获取文件"""
    try:
        result = await code_service.get_file_by_path(repo_id, path)
        
        if not result:
            raise HTTPException(status_code=404, detail="File not found")
        
        return {
            "success": True,
            "data": serialize_mongodb_doc(result)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/files/{file_id}/versions", response_model=dict)
async def get_file_versions(file_id: str, skip: int = 0, limit: int = 10):
    """获取文件版本历史"""
    try:
        result = await code_service.get_file_versions(file_id, skip, limit)
        
        return {
            "success": True,
            "data": serialize_mongodb_doc(result),
            "count": len(result)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/search", response_model=dict)
async def search_code(query: CodeSearchQuery):
    """搜索代码内容"""
    try:
        result = await code_service.search_code(
            str(query.repository_id), 
            query.query, 
            query.file_extensions,
            query.limit
        )
        
        return {
            "success": True,
            "data": result,
            "count": len(result)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 