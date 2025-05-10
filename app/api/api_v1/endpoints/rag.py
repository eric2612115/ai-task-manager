from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query, Path, Body
from typing import Optional, List, Dict, Any

from app.services.embedding_service import EmbeddingService
from app.services.rag_service import RAGService
from app.models.rag_models import (
    EmbeddingRequest,
    SearchRequest,
    RAGQueryRequest,
    RAGQueryResponse
)
from app.core.utils import serialize_mongodb_doc

router = APIRouter()
embedding_service = EmbeddingService()
rag_service = RAGService()

@router.post("/embeddings/generate/{repo_id}", response_model=Dict[str, Any])
async def generate_embeddings(repo_id: str, request: EmbeddingRequest = None, background_tasks: BackgroundTasks = None):
    """生成仓库嵌入向量"""
    try:
        force_regenerate = False
        if request:
            force_regenerate = request.force_regenerate
            
        # 获取当前状态
        current_status = await embedding_service.get_embedding_status(repo_id)
        
        # 如果正在处理中且不强制重新生成，则返回状态
        if current_status and current_status.get("status") == "processing" and not force_regenerate:
            return {
                "success": True,
                "message": "Embedding generation is already in progress.",
                "status": serialize_mongodb_doc(current_status)
            }
        
        # 启动嵌入生成（异步后台任务）
        result = await embedding_service.generate_repository_embeddings(repo_id, force_regenerate)
        
        if result:
            # 获取最新状态
            status = await embedding_service.get_embedding_status(repo_id)
            
            return {
                "success": True,
                "message": "Embedding generation started successfully.",
                "status": serialize_mongodb_doc(status)
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to start embedding generation.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating embeddings: {str(e)}")

@router.get("/embeddings/status/{repo_id}", response_model=Dict[str, Any])
async def get_embedding_status(repo_id: str):
    """获取嵌入生成状态"""
    try:
        status = await embedding_service.get_embedding_status(repo_id)
        
        if not status:
            return {
                "success": True,
                "status": "not_started",
                "message": "No embedding generation has been initiated for this repository."
            }
        
        return {
            "success": True,
            "status": serialize_mongodb_doc(status)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving embedding status: {str(e)}")

@router.post("/search", response_model=Dict[str, Any])
async def semantic_search(request: SearchRequest):
    """执行语义搜索"""
    try:
        results = await rag_service.search(
            query=request.query,
            repo_id=request.repo_id,
            collection=request.collection,
            limit=request.limit,
            file_types=request.file_types
        )
        
        return {
            "success": True,
            "data": results,
            "count": len(results),
            "query": request.query
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing semantic search: {str(e)}")

@router.post("/query", response_model=Dict[str, Any])
async def rag_query(request: RAGQueryRequest):
    """执行RAG查询（包含LLM回答）"""
    try:
        response = await rag_service.rag_query(
            query=request.query,
            repo_id=request.repo_id,
            context_limit=request.context_limit,
            llm_model=request.llm_model,
            llm_provider=request.llm_provider,
            include_code=request.include_code,
            include_docs=request.include_docs,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            file_types=request.file_types
        )
        
        return {
            "success": True,
            "data": response,
            "query": request.query
        }
    except ValueError as e:
        # API密钥或配置错误
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing RAG query: {str(e)}")

@router.delete("/embeddings/{repo_id}", response_model=Dict[str, Any])
async def delete_embeddings(repo_id: str):
    """删除仓库嵌入向量"""
    try:
        result = await embedding_service.delete_embeddings(repo_id)
        
        if result:
            return {
                "success": True,
                "message": f"Embeddings for repository {repo_id} have been deleted successfully."
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to delete embeddings.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting embeddings: {str(e)}") 