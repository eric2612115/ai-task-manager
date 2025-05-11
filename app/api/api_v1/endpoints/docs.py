from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Path, Body
from pydantic import BaseModel

from app.models.doc_models import DocCreate, DocUpdate, DocGenerateRequest
from app.services.doc_service import DocService
from app.core.utils import serialize_mongodb_doc

router = APIRouter()
doc_service = DocService()

@router.post("", response_model=dict)
async def create_document(doc: DocCreate):
    """创建文档"""
    try:
        result = await doc_service.create_document(doc.model_dump())
        return {
            "success": True,
            "data": serialize_mongodb_doc(result),
            "message": "Document created successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=dict)
async def get_documents(project_id: Optional[str] = None, skip: int = 0, limit: int = 100):
    """获取文档列表"""
    try:
        result = await doc_service.get_documents(project_id, skip, limit)
        return {
            "success": True,
            "data": serialize_mongodb_doc(result),
            "count": len(result)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{doc_id}", response_model=dict)
async def get_document(doc_id: str):
    """获取单个文档"""
    try:
        result = await doc_service.get_document(doc_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "success": True,
            "data": serialize_mongodb_doc(result)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{doc_id}", response_model=dict)
async def update_document(doc_id: str, doc: DocUpdate, user_id: Optional[str] = None):
    """更新文档"""
    try:
        result = await doc_service.update_document(doc_id, doc.model_dump(exclude_none=True), user_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "success": True,
            "data": serialize_mongodb_doc(result),
            "message": "Document updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{doc_id}", response_model=dict)
async def delete_document(doc_id: str):
    """删除文档"""
    try:
        result = await doc_service.delete_document(doc_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "success": True,
            "message": "Document deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{doc_id}/versions", response_model=dict)
async def get_document_versions(doc_id: str, skip: int = 0, limit: int = 20):
    """获取文档版本历史"""
    try:
        result = await doc_service.get_document_versions(doc_id, skip, limit)
        
        return {
            "success": True,
            "data": serialize_mongodb_doc(result),
            "count": len(result)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{doc_id}/versions/{version_number}", response_model=dict)
async def get_document_version(doc_id: str, version_number: int):
    """获取指定版本的文档"""
    try:
        result = await doc_service.get_document_version(doc_id, version_number)
        
        if not result:
            raise HTTPException(status_code=404, detail="Document version not found")
        
        return {
            "success": True,
            "data": serialize_mongodb_doc(result)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/projects/{project_id}/generate", response_model=dict)
async def generate_documentation(project_id: str, request: DocGenerateRequest):
    """生成文档"""
    try:
        result = await doc_service.generate_documentation(
            project_id,
            request.source_files,
            request.title if hasattr(request, 'title') else "Generated Documentation",
            request.doc_type
        )
        
        return {
            "success": True,
            "data": serialize_mongodb_doc(result),
            "message": "Document generated successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 