from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query, Path, Body
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId

from app.services.embedding_service import EmbeddingService
from app.services.rag_service import RAGService
from app.services.rag_visualization_service import rag_visualization_service
from app.models.rag_models import (
    EmbeddingRequest,
    SearchRequest,
    RAGQueryRequest,
    RAGQueryResponse,
    UnifiedSearchRequest
)
from app.core.utils import serialize_mongodb_doc
from app.db.mongodb import mongodb

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

@router.get("/visualization/message/{message_id}", response_model=Dict[str, Any])
async def get_message_visualization(message_id: str):
    """
    获取特定消息的RAG可视化数据
    
    Args:
        message_id: 消息ID
    
    Returns:
        可视化数据，包括检索到的源文件、得分等
    """
    try:
        visualization_data = await rag_visualization_service.get_message_visualization(message_id)
        
        if not visualization_data:
            return {
                "success": False,
                "message": "No visualization data found for this message"
            }
        
        return {
            "success": True,
            "data": visualization_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving visualization data: {str(e)}")

@router.post("/visualization/highlight", response_model=Dict[str, Any])
async def highlight_context_matches(request: Dict[str, Any] = Body(...)):
    """
    高亮查询与上下文的匹配部分
    
    请求体:
        {
            "query": "查询文本",
            "context": "上下文内容",
            "language": "编程语言(可选)"
        }
    
    Returns:
        包含高亮信息的数据
    """
    try:
        query = request.get("query")
        context = request.get("context")
        language = request.get("language")
        
        if not query or not context:
            raise HTTPException(status_code=400, detail="Query and context are required")
        
        highlight_data = await rag_visualization_service.highlight_context_matches(
            query=query,
            context=context,
            language=language
        )
        
        return {
            "success": True,
            "data": highlight_data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error highlighting context: {str(e)}")

@router.post("/unified-search", response_model=Dict[str, Any])
async def unified_search(request: UnifiedSearchRequest):
    """
    统一搜索接口，合并所有来源的结果
    
    - 支持代码、文档、任务、评论和外部文档的搜索
    - 可以指定搜索范围和数据源
    """
    try:
        results = await rag_service.unified_search(
            query=request.query,
            repo_id=request.repo_id,
            project_id=request.project_id,
            include_code=request.include_code,
            include_docs=request.include_docs,
            include_tasks=request.include_tasks,
            include_comments=request.include_comments,
            include_external_docs=request.include_external_docs,
            limit=request.limit
        )
        
        return {
            "success": True,
            "data": results,
            "count": len(results),
            "query": request.query
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing unified search: {str(e)}")

@router.post("/interactions", response_model=Dict[str, Any])
async def record_user_interaction(interaction: Dict[str, Any] = Body(...)):
    """
    记录用户与搜索结果的交互
    
    请求体:
        {
            "document_id": "文档ID",
            "document_type": "文档类型",
            "interaction_type": "click|helpful|not_helpful|bookmark",
            "project_id": "项目ID",
            "metadata": {
                "query": "搜索查询",
                "position": 2
            }
        }
    """
    try:
        # 验证必要字段
        required_fields = ["document_id", "document_type", "interaction_type"]
        for field in required_fields:
            if field not in interaction:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # 获取或创建用户ID (实际应用中应从认证系统获取)
        user_id = "507f1f77bcf86cd799439011"  # 模拟用户ID
        
        # 准备记录数据
        record = {
            "user_id": ObjectId(user_id),
            "document_id": interaction["document_id"],
            "document_type": interaction["document_type"],
            "interaction_type": interaction["interaction_type"],
            "timestamp": datetime.utcnow(),
            "project_id": ObjectId(interaction["project_id"]) if "project_id" in interaction else None,
            "metadata": interaction.get("metadata", {})
        }
        
        # 插入或更新交互记录
        await mongodb.db.user_document_interactions.update_one(
            {
                "user_id": record["user_id"],
                "document_id": record["document_id"],
                "document_type": record["document_type"]
            },
            {"$set": record, "$inc": {"interaction_count": 1}},
            upsert=True
        )
        
        return {
            "success": True,
            "message": "User interaction recorded successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error recording user interaction: {str(e)}"
        )

@router.post("/rerank-with-feedback", response_model=Dict[str, Any])
async def rerank_with_feedback(request: Dict[str, Any] = Body(...)):
    """
    基于用户历史反馈重排序搜索结果
    
    请求体:
        {
            "query": "查询文本",
            "results": [搜索结果数组],
            "project_id": "项目ID",
            "limit": 5
        }
    """
    try:
        query = request.get("query")
        results = request.get("results", [])
        project_id = request.get("project_id")
        limit = request.get("limit", 5)
        
        if not query or not results:
            raise HTTPException(status_code=400, detail="Query and results are required")
        
        # 获取用户ID (实际应用中应从认证系统获取)
        user_id = "507f1f77bcf86cd799439011"  # 模拟用户ID
        
        # 执行基于用户反馈的重排序
        reranked_results = await rag_service.rerank_with_feedback(
            query=query,
            results=results,
            user_id=user_id,
            project_id=project_id,
            limit=limit
        )
        
        return {
            "success": True,
            "data": reranked_results,
            "count": len(reranked_results)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reranking results: {str(e)}")

@router.post("/advanced-hybrid-search", response_model=Dict[str, Any])
async def advanced_hybrid_search(request: Dict[str, Any] = Body(...)):
    """
    执行高级混合检索
    
    请求体:
        {
            "query": "查询文本",
            "repo_id": "仓库ID",
            "project_id": "项目ID",
            "collection": "code|docs|both",
            "limit": 10,
            "file_types": ["python", "javascript"],
            "use_bm25": true,
            "use_vector": true,
            "fusion_method": "rrf|weighted|simple"
        }
    """
    try:
        query = request.get("query")
        repo_id = request.get("repo_id")
        project_id = request.get("project_id")
        collection = request.get("collection")
        limit = request.get("limit", 10)
        file_types = request.get("file_types")
        use_bm25 = request.get("use_bm25", True)
        use_vector = request.get("use_vector", True)
        fusion_method = request.get("fusion_method", "rrf")
        
        if not query or not repo_id:
            raise HTTPException(status_code=400, detail="Query and repo_id are required")
        
        # 执行高级混合检索
        results = await rag_service.advanced_hybrid_search(
            query=query,
            repo_id=repo_id,
            project_id=project_id,
            collection=collection,
            limit=limit,
            file_types=file_types,
            use_bm25=use_bm25,
            use_vector=use_vector,
            fusion_method=fusion_method
        )
        
        return {
            "success": True,
            "data": results,
            "count": len(results),
            "query": query,
            "fusion_method": fusion_method
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing advanced hybrid search: {str(e)}") 