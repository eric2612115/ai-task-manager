import asyncio
import logging
import time
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union

from langchain.schema import Document, BaseMessage
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnableParallel, RunnablePassthrough

# LLM提供商
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.task_embedding_service import task_embedding_service
from app.services.external_document_service import ExternalDocumentService
from app.models.rag_models import RAGQueryResponse, SearchResult

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        """初始化RAG服务"""
        self.embedding_service = EmbeddingService()
        self.external_document_service = ExternalDocumentService()
        self._llms = {}  # 缓存LLM实例
        logger.info("RAGService initialized")

    async def search(self, query: str, repo_id: str, collection: Optional[str] = None, limit: int = 5, file_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """执行语义搜索"""
        return await self.embedding_service.search(query, repo_id, collection, limit, file_types)

    async def hybrid_search(self, 
                            query: str, 
                            repo_id: str, 
                            collection: Optional[str] = None, 
                            limit: int = 5,
                            file_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """执行混合检索（向量搜索+关键词搜索）"""
        # 1. 执行向量搜索
        vector_results = await self.search(query, repo_id, collection, limit, file_types)
        
        # 2. 执行关键词搜索
        keyword_results = await self._keyword_search(query, repo_id, collection, limit, file_types)
        
        # 3. 融合结果
        merged_results = self._merge_search_results(vector_results, keyword_results, limit)
        
        return merged_results

    async def advanced_hybrid_search(self, 
                                   query: str, 
                                   repo_id: str,
                                   project_id: Optional[str] = None,
                                   collection: Optional[str] = None,
                                   limit: int = 5,
                                   file_types: Optional[List[str]] = None,
                                   use_bm25: bool = True,
                                   use_vector: bool = True,
                                   fusion_method: str = "rrf") -> List[Dict[str, Any]]:
        """执行高级混合检索"""
        results = []
        
        # 1. 向量搜索
        if use_vector:
            vector_results = await self.search(query, repo_id, collection, limit, file_types)
            results.append(("vector", vector_results))
        
        # 2. 关键词搜索 (BM25)
        if use_bm25:
            keyword_results = await self._keyword_search(query, repo_id, collection, limit, file_types)
            results.append(("keyword", keyword_results))
        
        # 3. 如果有项目ID，搜索任务和评论
        if project_id:
            # 搜索任务
            task_results = await task_embedding_service.semantic_search_tasks(query, project_id, limit)
            # 转换任务结果格式以匹配其他结果
            formatted_task_results = []
            for task in task_results:
                formatted_task_results.append({
                    "file_id": task.get("id"),
                    "file_path": "",
                    "file_name": task.get("data", {}).get("summary", ""),
                    "content": task.get("highlight", ""),
                    "score": task.get("score", 0),
                    "type": "task",
                    "metadata": task.get("data", {})
                })
            results.append(("task", formatted_task_results))
            
            # 搜索评论
            comment_results = await task_embedding_service.semantic_search_comments(query, project_id, limit)
            # 转换评论结果格式以匹配其他结果
            formatted_comment_results = []
            for comment in comment_results:
                formatted_comment_results.append({
                    "file_id": comment.get("id"),
                    "file_path": "",
                    "file_name": comment.get("data", {}).get("task_summary", ""),
                    "content": comment.get("data", {}).get("content", ""),
                    "score": comment.get("score", 0),
                    "type": "comment",
                    "metadata": comment.get("data", {})
                })
            results.append(("comment", formatted_comment_results))
            
            # 搜索外部文档
            external_doc_results = await self.external_document_service.search_external_docs(query, project_id, limit)
            results.append(("external_doc", external_doc_results))
        
        # 4. 根据指定方法融合结果
        if fusion_method == "rrf":
            merged_results = self._merge_search_results_rrf(results, limit)
        elif fusion_method == "weighted":
            merged_results = self._merge_search_results_weighted(results, limit)
        else:
            merged_results = self._merge_search_results_simple(results, limit)
        
        return merged_results
        
    def _merge_search_results_rrf(self, search_results: List[Tuple[str, List[Dict[str, Any]]]], limit: int = 5) -> List[Dict[str, Any]]:
        """使用Reciprocal Rank Fusion算法融合多个来源的搜索结果"""
        # 1. 创建ID到结果的映射
        id_to_result = {}
        id_to_ranks = {}
        
        # 2. 处理每个来源的结果
        for source_type, results in search_results:
            for i, result in enumerate(results):
                result_id = f"{result['type']}:{result['file_id']}"
                
                if result_id not in id_to_result:
                    id_to_result[result_id] = result
                    id_to_ranks[result_id] = {source_type: i + 1}
                else:
                    id_to_ranks[result_id][source_type] = i + 1
        
        # 3. 计算RRF分数
        k = 60  # 常数参数
        for result_id in id_to_ranks:
            rrf_score = 0
            for source_type, rank in id_to_ranks[result_id].items():
                rrf_score += 1 / (k + rank)
            
            id_to_result[result_id]["rrf_score"] = rrf_score
        
        # 4. 排序并返回结果
        merged_results = list(id_to_result.values())
        merged_results.sort(key=lambda x: x.get("rrf_score", 0), reverse=True)
        
        return merged_results[:limit]
    
    def _merge_search_results_weighted(self, search_results: List[Tuple[str, List[Dict[str, Any]]]], limit: int = 5) -> List[Dict[str, Any]]:
        """使用加权方法融合搜索结果"""
        # 定义不同来源的权重
        weights = {
            "vector": 1.0,
            "keyword": 0.8,
            "task": 0.7,
            "comment": 0.6,
            "external_doc": 0.9
        }
        
        # 创建ID到结果的映射
        id_to_result = {}
        
        # 处理每个来源的结果
        for source_type, results in search_results:
            for i, result in enumerate(results):
                result_id = f"{result['type']}:{result['file_id']}"
                
                # 计算加权分数
                score = result.get("score", 0) * weights.get(source_type, 0.5)
                
                if result_id not in id_to_result:
                    result["weighted_score"] = score
                    id_to_result[result_id] = result
                else:
                    # 如果已存在，取较高的分数
                    id_to_result[result_id]["weighted_score"] = max(
                        id_to_result[result_id].get("weighted_score", 0),
                        score
                    )
        
        # 排序并返回结果
        merged_results = list(id_to_result.values())
        merged_results.sort(key=lambda x: x.get("weighted_score", 0), reverse=True)
        
        return merged_results[:limit]
    
    def _merge_search_results_simple(self, search_results: List[Tuple[str, List[Dict[str, Any]]]], limit: int = 5) -> List[Dict[str, Any]]:
        """简单合并搜索结果（去重）"""
        # 创建ID到结果的映射
        id_to_result = {}
        
        # 处理每个来源的结果
        for source_type, results in search_results:
            for result in results:
                result_id = f"{result['type']}:{result['file_id']}"
                
                if result_id not in id_to_result:
                    id_to_result[result_id] = result
                elif result.get("score", 0) > id_to_result[result_id].get("score", 0):
                    # 如果已存在，保留分数更高的结果
                    id_to_result[result_id] = result
        
        # 排序并返回结果
        merged_results = list(id_to_result.values())
        merged_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return merged_results[:limit]

    async def _keyword_search(self, query: str, repo_id: str, collection: Optional[str] = None, 
                             limit: int = 5, file_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """执行关键词搜索"""
        results = []
        
        try:
            # 构建基本查询
            search_query = {"$text": {"$search": query}}
            
            # 添加仓库ID限制
            search_query["repository_id"] = repo_id
            
            # 添加文件类型过滤
            if file_types and len(file_types) > 0:
                search_query["code_language"] = {"$in": file_types}
            
            # 根据collection参数决定搜索类型
            if collection is None or collection == "code" or collection == "both":
                # 搜索代码文件
                code_files = await self._search_code_files(search_query, limit)
                results.extend(code_files)
            
            if collection is None or collection == "docs" or collection == "both":
                # 搜索文档
                docs = await self._search_docs(search_query, limit)
                results.extend(docs)
            
            # 按相关性得分排序
            results.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            return results[:limit]
        except Exception as e:
            logger.error(f"Error performing keyword search: {str(e)}")
            return []
    
    async def _search_code_files(self, search_query: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """关键词搜索代码文件"""
        try:
            # 执行文本搜索
            cursor = self.embedding_service.mongodb.db.code_files.find(
                search_query,
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(limit)
            
            code_files = await cursor.to_list(length=limit)
            
            # 处理结果
            results = []
            for file in code_files:
                results.append({
                    "file_id": str(file["_id"]),
                    "file_path": file.get("file_path", ""),
                    "file_name": file.get("file_name", ""),
                    "content": file.get("content", ""),
                    "language": file.get("code_language", ""),
                    "score": file.get("score", 0),
                    "type": "code"
                })
            
            return results
        except Exception as e:
            logger.error(f"Error searching code files: {str(e)}")
            return []
    
    async def _search_docs(self, search_query: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """关键词搜索文档"""
        try:
            # 执行文本搜索
            cursor = self.embedding_service.mongodb.db.project_documentations.find(
                search_query,
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(limit)
            
            docs = await cursor.to_list(length=limit)
            
            # 处理结果
            results = []
            for doc in docs:
                results.append({
                    "file_id": str(doc["_id"]),
                    "file_path": "",
                    "file_name": doc.get("title", ""),
                    "content": doc.get("content", ""),
                    "language": "markdown",
                    "score": doc.get("score", 0),
                    "type": "doc"
                })
            
            return results
        except Exception as e:
            logger.error(f"Error searching docs: {str(e)}")
            return []

    def _merge_search_results(self, vector_results: List[Dict[str, Any]], 
                             keyword_results: List[Dict[str, Any]], 
                             limit: int = 5) -> List[Dict[str, Any]]:
        """融合向量搜索和关键词搜索结果"""
        # 使用Reciprocal Rank Fusion (RRF)算法
        
        # 1. 创建ID到结果的映射
        id_to_result = {}
        id_to_ranks = {}
        
        # 2. 处理向量搜索结果
        for i, result in enumerate(vector_results):
            result_id = f"{result['type']}:{result['file_id']}"
            id_to_result[result_id] = result
            id_to_ranks[result_id] = {"vector_rank": i + 1}
        
        # 3. 处理关键词搜索结果
        for i, result in enumerate(keyword_results):
            result_id = f"{result['type']}:{result['file_id']}"
            if result_id not in id_to_result:
                id_to_result[result_id] = result
                id_to_ranks[result_id] = {"keyword_rank": i + 1}
            else:
                id_to_ranks[result_id]["keyword_rank"] = i + 1
        
        # 4. 计算RRF分数
        k = 60  # 常数参数
        for result_id in id_to_ranks:
            vector_rank = id_to_ranks[result_id].get("vector_rank", 1000)
            keyword_rank = id_to_ranks[result_id].get("keyword_rank", 1000)
            rrf_score = 1/(k + vector_rank) + 1/(k + keyword_rank)
            id_to_result[result_id]["rrf_score"] = rrf_score
        
        # 5. 排序并返回结果
        merged_results = list(id_to_result.values())
        merged_results.sort(key=lambda x: x.get("rrf_score", 0), reverse=True)
        
        return merged_results[:limit]

    async def search_all_sources(self, 
                                query: str, 
                                repo_id: Optional[str] = None, 
                                project_id: Optional[str] = None,
                                include_code: bool = True,
                                include_docs: bool = True,
                                include_tasks: bool = True,
                                include_comments: bool = True,
                                include_external_docs: bool = True,
                                limit: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """搜索所有数据源"""
        results = {}
        tasks = []
        
        # 1. 搜索代码和文档
        if (include_code or include_docs) and repo_id:
            code_docs_results = await self.hybrid_search(
                query=query,
                repo_id=repo_id,
                collection="code" if include_code and not include_docs else "docs" if include_docs and not include_code else None,
                limit=limit
            )
            results["code_docs"] = code_docs_results
            tasks.append(("code_docs", code_docs_results))
        
        # 2. 搜索任务
        if include_tasks and project_id:
            task_results = await task_embedding_service.semantic_search_tasks(
                query=query,
                project_id=project_id,
                limit=limit
            )
            results["tasks"] = task_results
            tasks.append(("tasks", task_results))
        
        # 3. 搜索评论
        if include_comments and project_id:
            comment_results = await task_embedding_service.semantic_search_comments(
                query=query,
                project_id=project_id,
                limit=limit
            )
            results["comments"] = comment_results
            tasks.append(("comments", comment_results))
        
        # 4. 搜索外部文档
        if include_external_docs and project_id:
            external_doc_results = await self.external_document_service.search_external_docs(
                query=query,
                project_id=project_id,
                limit=limit
            )
            results["external_docs"] = external_doc_results
            tasks.append(("external_docs", external_doc_results))
        
        # 5. 或者使用统一的散文集合进行搜索
        if project_id and (include_tasks or include_comments):
            content_types = []
            if include_tasks:
                content_types.append("task")
            if include_comments:
                content_types.append("comment")
            
            prose_results = await task_embedding_service.semantic_search_prose(
                query=query,
                project_id=project_id,
                content_types=content_types,
                limit=limit
            )
            results["prose"] = prose_results
        
        return results

    async def unified_search(self,
                            query: str,
                            repo_id: Optional[str] = None,
                            project_id: Optional[str] = None,
                            include_code: bool = True,
                            include_docs: bool = True,
                            include_tasks: bool = True,
                            include_comments: bool = True,
                            include_external_docs: bool = True,
                            limit: int = 10) -> List[Dict[str, Any]]:
        """统一搜索接口，合并所有来源的结果"""
        all_results = []
        
        # 1. 搜索代码和文档
        if (include_code or include_docs) and repo_id:
            code_docs_results = await self.hybrid_search(
                query=query,
                repo_id=repo_id,
                collection="code" if include_code and not include_docs else "docs" if include_docs and not include_code else None,
                limit=limit
            )
            all_results.extend(code_docs_results)
        
        # 2. 搜索任务
        if include_tasks and project_id:
            task_results = await task_embedding_service.semantic_search_tasks(
                query=query,
                project_id=project_id,
                limit=limit
            )
            # 转换任务结果格式以匹配其他结果
            for task in task_results:
                all_results.append({
                    "file_id": task.get("id"),
                    "file_path": "",
                    "file_name": task.get("data", {}).get("summary", ""),
                    "content": task.get("highlight", ""),
                    "score": task.get("score", 0),
                    "type": "task",
                    "metadata": task.get("data", {})
                })
        
        # 3. 搜索评论
        if include_comments and project_id:
            comment_results = await task_embedding_service.semantic_search_comments(
                query=query,
                project_id=project_id,
                limit=limit
            )
            # 转换评论结果格式以匹配其他结果
            for comment in comment_results:
                all_results.append({
                    "file_id": comment.get("id"),
                    "file_path": "",
                    "file_name": comment.get("data", {}).get("task_summary", ""),
                    "content": comment.get("data", {}).get("content", ""),
                    "score": comment.get("score", 0),
                    "type": "comment",
                    "metadata": comment.get("data", {})
                })
        
        # 4. 搜索外部文档
        if include_external_docs and project_id:
            external_doc_results = await self.external_document_service.search_external_docs(
                query=query,
                project_id=project_id,
                limit=limit
            )
            all_results.extend(external_doc_results)
        
        # 5. 按相关性得分排序
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return all_results[:limit]

    async def rerank_results(self, query: str, results: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        """使用轻量级LLM重排序搜索结果"""
        if not results or len(results) <= 1:
            return results
        
        try:
            # 准备上下文
            contexts = []
            for i, result in enumerate(results):
                content = result.get("content", "")
                # 截断内容
                if len(content) > 300:
                    content = content[:300] + "..."
                
                contexts.append({
                    "id": i,
                    "content": content,
                    "type": result.get("type", "unknown")
                })
            
            # 使用LLM进行重排序
            llm = await self._get_llm(provider="openai", model="gpt-3.5-turbo", temperature=0.0)
            
            prompt = f"""
            请根据查询"{query}"对以下内容片段进行相关性排序。
            返回一个JSON数组，包含按相关性从高到低排序的内容ID。
            内容片段:
            {contexts}
            """
            
            response = await llm.ainvoke(prompt)
            
            # 解析响应
            try:
                ranked_ids = json.loads(response)
                
                # 根据排名重新排序结果
                reranked_results = []
                for id in ranked_ids:
                    if id < len(results):
                        reranked_results.append(results[id])
                
                # 添加任何遗漏的结果
                for result in results:
                    if result not in reranked_results:
                        reranked_results.append(result)
                
                return reranked_results[:limit]
            except:
                # 如果解析失败，返回原始结果
                return results
        
        except Exception as e:
            logger.error(f"Error reranking results: {str(e)}")
            return results
            
    async def rerank_with_feedback(self, 
                                  query: str, 
                                  results: List[Dict[str, Any]], 
                                  user_id: str,
                                  project_id: Optional[str] = None,
                                  limit: int = 5) -> List[Dict[str, Any]]:
        """基于用户历史反馈重排序搜索结果"""
        # 获取用户历史交互数据
        user_interactions = await self._get_user_interactions(user_id, project_id)
        
        # 为每个结果计算个性化分数
        for result in results:
            # 基础分数
            base_score = result.get("score", 0)
            
            # 个性化加权
            personalized_score = base_score
            
            # 文档ID
            doc_id = f"{result['type']}:{result['file_id']}"
            
            # 应用用户交互权重
            if doc_id in user_interactions:
                interaction = user_interactions[doc_id]
                # 点击加权
                personalized_score += interaction.get("clicks", 0) * 0.1
                # 有用标记加权
                personalized_score += interaction.get("helpful_marks", 0) * 0.2
                # 收藏加权
                personalized_score += interaction.get("bookmarks", 0) * 0.3
            
            # 保存个性化分数
            result["personalized_score"] = personalized_score
        
        # 按个性化分数排序
        results.sort(key=lambda x: x.get("personalized_score", 0), reverse=True)
        
        return results[:limit]

    async def _get_user_interactions(self, user_id: str, project_id: Optional[str] = None) -> Dict[str, Dict[str, int]]:
        """获取用户与文档的历史交互数据"""
        interactions = {}
        
        # 构建查询条件
        query = {"user_id": ObjectId(user_id)}
        if project_id:
            query["project_id"] = ObjectId(project_id)
        
        # 查询用户交互记录
        cursor = self.embedding_service.mongodb.db.user_document_interactions.find(query)
        
        async for doc in cursor:
            doc_id = doc["document_id"]
            doc_type = doc["document_type"]
            key = f"{doc_type}:{doc_id}"
            
            # 计算不同类型交互的计数
            clicks = 0
            helpful_marks = 0
            bookmarks = 0
            
            if doc["interaction_type"] == "click":
                clicks = doc.get("interaction_count", 1)
            elif doc["interaction_type"] == "helpful":
                helpful_marks = doc.get("interaction_count", 1)
            elif doc["interaction_type"] == "bookmark":
                bookmarks = 1
            
            # 更新或添加交互数据
            if key in interactions:
                interactions[key]["clicks"] += clicks
                interactions[key]["helpful_marks"] += helpful_marks
                interactions[key]["bookmarks"] += bookmarks
            else:
                interactions[key] = {
                    "clicks": clicks,
                    "helpful_marks": helpful_marks,
                    "bookmarks": bookmarks
                }
        
        return interactions

    async def rag_query(self, 
                        query: str, 
                        repo_id: str, 
                        context_limit: int = 5, 
                        llm_model: Optional[str] = None, 
                        llm_provider: Optional[str] = None,
                        include_code: bool = True, 
                        include_docs: bool = True,
                        include_tasks: bool = False,
                        include_comments: bool = False,
                        include_external_docs: bool = False,
                        project_id: Optional[str] = None,
                        use_hybrid_search: bool = False,
                        temperature: float = 0.7,
                        max_tokens: int = 1000,
                        file_types: Optional[List[str]] = None) -> RAGQueryResponse:
        """执行RAG查询"""
        start_time = time.time()
        
        # 执行搜索
        search_results = []
        if use_hybrid_search:
            # 使用混合搜索
            if project_id and (include_tasks or include_comments or include_external_docs):
                # 如果需要包含项目数据，使用统一搜索
                search_results = await self.unified_search(
                    query=query,
                    repo_id=repo_id,
                    project_id=project_id,
                    include_code=include_code,
                    include_docs=include_docs,
                    include_tasks=include_tasks,
                    include_comments=include_comments,
                    include_external_docs=include_external_docs,
                    limit=context_limit
                )
            else:
                # 否则只搜索代码和文档
                search_results = await self.hybrid_search(
                    query=query,
                    repo_id=repo_id,
                    collection=None if include_code and include_docs else "code" if include_code else "docs",
                    limit=context_limit,
                    file_types=file_types
                )
        else:
            # 使用向量搜索
            collection = None
            if include_code and not include_docs:
                collection = "code"
            elif include_docs and not include_code:
                collection = "docs"
            
            search_results = await self.search(
                query=query,
                repo_id=repo_id,
                collection=collection,
                limit=context_limit,
                file_types=file_types
            )
        
        # 如果没有搜索结果，直接向LLM发送查询
        if not search_results:
            llm = await self._get_llm(llm_provider, llm_model, temperature, max_tokens)
            answer = await self._generate_answer_without_context(query, llm)
            
            execution_time = time.time() - start_time
            
            return RAGQueryResponse(
                query=query,
                answer=answer,
                sources=[],
                execution_time=execution_time
            )
        
        # 准备上下文
        context = self._prepare_context(search_results)
        
        # 获取LLM实例
        llm = await self._get_llm(llm_provider, llm_model, temperature, max_tokens)
        
        # 生成回答
        answer = await self._generate_answer_with_context(query, context, llm)
        
        execution_time = time.time() - start_time
        
        # 准备源文件信息
        sources = [
            SearchResult(
                file_id=result["file_id"],
                file_path=result["file_path"],
                file_name=result["file_name"],
                content=self._truncate_content(result["content"]),  # 截断内容以减小响应大小
                language=result.get("language", ""),
                score=result["score"],
                type=result["type"],
                metadata=result.get("metadata", {})
            )
            for result in search_results
        ]
        
        # 返回结果
        return RAGQueryResponse(
            query=query,
            answer=answer,
            sources=sources,
            execution_time=execution_time
        )

    def _truncate_content(self, content: str, max_length: int = 1000) -> str:
        """截断内容以减小响应大小"""
        if len(content) <= max_length:
            return content
        return content[:max_length] + "..."

    def _prepare_context(self, search_results: List[Dict[str, Any]]) -> str:
        """准备上下文信息"""
        context_parts = []
        
        for i, result in enumerate(search_results):
            file_path = result.get("file_path", "")
            file_name = result.get("file_name", "")
            content = result.get("content", "")
            language = result.get("language", "")
            result_type = result.get("type", "code")
            
            # 添加文件来源信息
            if result_type == "code":
                context_parts.append(f"[Source {i+1}: Code File - {file_path}]")
                if language:
                    context_parts.append(f"Language: {language}")
            elif result_type == "doc":
                context_parts.append(f"[Source {i+1}: Document - {file_name}]")
            elif result_type == "external_doc":
                context_parts.append(f"[Source {i+1}: External Document - {file_name}]")
                if result.get("metadata", {}).get("title"):
                    context_parts.append(f"Title: {result['metadata']['title']}")
            elif result_type == "task":
                context_parts.append(f"[Source {i+1}: Task - {file_name}]")
                if result.get("metadata", {}).get("status"):
                    context_parts.append(f"Status: {result['metadata']['status']}")
            elif result_type == "comment":
                task_summary = result.get("metadata", {}).get("task_summary", "")
                context_parts.append(f"[Source {i+1}: Comment on Task - {task_summary}]")
            
            # 添加内容
            context_parts.append(content)
            context_parts.append("---")
        
        return "\n".join(context_parts)

    async def _get_llm(self, provider: Optional[str] = None, model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 1000):
        """获取LLM实例"""
        # 确定提供商
        provider = provider or settings.LLM_PROVIDER
        
        # 缓存键
        cache_key = f"{provider}_{model}_{temperature}_{max_tokens}"
        
        # 检查缓存
        if cache_key in self._llms:
            return self._llms[cache_key]
        
        # 创建新实例
        llm = None
        
        if provider == "openai":
            # 确定模型名称
            model_name = model or "gpt-3.5-turbo"
            
            if not settings.OPENAI_API_KEY:
                raise ValueError("OpenAI API key not set")
            
            llm = ChatOpenAI(
                openai_api_key=settings.OPENAI_API_KEY,
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
        elif provider == "anthropic":
            # 确定模型名称
            model_name = model or "claude-3-sonnet-20240229"
            
            if not settings.ANTHROPIC_API_KEY:
                raise ValueError("Anthropic API key not set")
            
            llm = ChatAnthropic(
                anthropic_api_key=settings.ANTHROPIC_API_KEY,
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
        elif provider == "google":
            # 确定模型名称
            model_name = model or "gemini-pro"
            
            if not settings.GOOGLE_API_KEY:
                raise ValueError("Google API key not set")
            
            llm = ChatGoogleGenerativeAI(
                google_api_key=settings.GOOGLE_API_KEY,
                model=model_name,
                temperature=temperature,
                max_output_tokens=max_tokens
            )
            
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
        
        # 缓存实例
        self._llms[cache_key] = llm
        
        return llm

    async def _generate_answer_with_context(self, query: str, context: str, llm) -> str:
        """使用上下文生成回答"""
        try:
            # 创建提示模板
            prompt = ChatPromptTemplate.from_template("""
            You are a helpful AI assistant that answers questions about code and documentation.
            Use the following context to answer the user's question. If the information is not
            in the context, say that you don't know and recommend what to search for instead.
            Do not make up answers that are not supported by the provided context.
            Do not reference documents, code, or insights not provided in the context.
            
            Context:
            {context}
            
            User's Question: {question}
            
            Answer:
            """)
            
            # 创建Chain
            chain = (
                {"context": lambda x: context, "question": lambda x: query}
                | prompt
                | llm
                | StrOutputParser()
            )
            
            # 执行Chain
            answer = await chain.ainvoke({})
            return answer
        except Exception as e:
            logger.error(f"Error generating answer with context: {str(e)}")
            return f"Error generating answer: {str(e)}"

    async def _generate_answer_without_context(self, query: str, llm) -> str:
        """在没有上下文的情况下生成回答"""
        try:
            # 创建提示模板
            prompt = ChatPromptTemplate.from_template("""
            You are a helpful AI assistant that answers questions about code and documentation.
            Since I don't have specific context about your code repository, I'll provide general guidance.

            User's Question: {question}
            
            Answer:
            """)
            
            # 创建Chain
            chain = (
                {"question": lambda x: query}
                | prompt
                | llm
                | StrOutputParser()
            )
            
            # 执行Chain
            answer = await chain.ainvoke({})
            return answer
        except Exception as e:
            logger.error(f"Error generating answer without context: {str(e)}")
            return f"Error generating answer: {str(e)}" 