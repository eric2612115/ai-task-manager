import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import torch
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.db.mongodb import mongodb

logger = logging.getLogger(__name__)

class TaskEmbeddingService:
    def __init__(self):
        """初始化任务嵌入服务"""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # 初始化ChromaDB客户端
        self.client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        
        # 延迟加载模型
        self._sentence_transformer = None
        
        # ChromaDB嵌入函数
        self._task_embedding_function = None
        
        # 创建或获取集合
        self._task_collection = None
        
        logger.info("TaskEmbeddingService initialized")

    async def initialize_model(self):
        """异步初始化模型"""
        if self._sentence_transformer is None:
            loop = asyncio.get_event_loop()
            # 加载SentenceTransformer模型
            self._sentence_transformer = await loop.run_in_executor(
                None,
                self._load_sentence_transformer
            )
            
            # 直接获取或创建集合，不使用嵌入函数
            try:
                self._task_collection = self.client.get_collection(settings.CHROMA_COLLECTION_TASKS)
                logger.info(f"Retrieved existing collection: {settings.CHROMA_COLLECTION_TASKS}")
            except Exception as e:
                logger.info(f"Creating new collection: {settings.CHROMA_COLLECTION_TASKS}, Error: {str(e)}")
                self._task_collection = self.client.create_collection(
                    name=settings.CHROMA_COLLECTION_TASKS
                )
        
        logger.info("Task embedding model initialized successfully")
        return True

    def _load_sentence_transformer(self):
        """加载SentenceTransformer模型"""
        logger.info(f"Loading SentenceTransformer model from {settings.SENTENCE_TRANSFORMER_MODEL}")
        return SentenceTransformer(settings.SENTENCE_TRANSFORMER_MODEL).to(self.device)

    def get_or_create_collection(self, name: str, embedding_function):
        """创建或获取ChromaDB集合"""
        try:
            collection = self.client.get_collection(name=name, embedding_function=embedding_function)
            logger.info(f"Retrieved existing collection: {name}")
            return collection
        except Exception as e:
            logger.info(f"Creating new collection: {name}, Error: {str(e)}")
            return self.client.create_collection(
                name=name,
                embedding_function=embedding_function
            )

    def generate_task_embeddings_sync(self, texts: List[str]) -> List[List[float]]:
        """同步生成任务嵌入"""
        try:
            # 处理空文本
            if not texts or all(not text.strip() for text in texts):
                return [[0.0] * 384] * len(texts)  # 返回零向量
            
            # 过滤空文本
            valid_texts = [text for text in texts if text.strip()]
            valid_indices = [i for i, text in enumerate(texts) if text.strip()]
            
            if not valid_texts:
                return [[0.0] * 384] * len(texts)
            
            # 使用SentenceTransformer生成嵌入
            embeddings = self._sentence_transformer.encode(valid_texts)
            
            # 为所有文本构建结果
            result = [[0.0] * 384] * len(texts)
            for i, idx in enumerate(valid_indices):
                result[idx] = embeddings[i].tolist()
            
            return result
        except Exception as e:
            logger.error(f"Error generating task embeddings: {str(e)}")
            return [[0.0] * 384] * len(texts)  # 出错时返回零向量

    async def generate_task_embedding(self, task_id: str, summary: str, description: str = None) -> Dict[str, Any]:
        """生成任务的嵌入向量并存储到MongoDB和ChromaDB"""
        await self.initialize_model()
        
        try:
            # 准备文本
            summary_text = summary.strip()
            description_text = description.strip() if description else ""
            
            # 生成嵌入
            task_text = f"{summary_text}\n{description_text}" if description_text else summary_text
            embedding = self.generate_task_embeddings_sync([task_text])[0]
            
            # 更新MongoDB中的任务
            await mongodb.db.tasks.update_one(
                {"_id": ObjectId(task_id)},
                {"$set": {
                    "summary_embedding": embedding if summary_text else None,
                    "updated_at": datetime.utcnow()
                }}
            )
            
            # 添加到ChromaDB
            task = await mongodb.db.tasks.find_one({"_id": ObjectId(task_id)})
            if task:
                # 准备元数据
                metadata = {
                    "task_id": str(task["_id"]),
                    "project_id": str(task["project_id"]),
                    "summary": task.get("summary", ""),
                    "status": task.get("status", ""),
                    "priority": task.get("priority", ""),
                    "created_at": task.get("created_at").isoformat() if task.get("created_at") else "",
                    "updated_at": task.get("updated_at").isoformat() if task.get("updated_at") else ""
                }
                
                # 检查是否已存在，如果存在则更新
                try:
                    self._task_collection.get(ids=[task_id])
                    # 存在，更新
                    self._task_collection.update(
                        ids=[task_id],
                        documents=[task_text],
                        metadatas=[metadata],
                        embeddings=[embedding]
                    )
                    logger.info(f"Updated task embedding for task {task_id}")
                except Exception as e:
                    # 不存在或发生错误，添加
                    try:
                        self._task_collection.add(
                            ids=[task_id],
                            documents=[task_text],
                            metadatas=[metadata],
                            embeddings=[embedding]
                        )
                        logger.info(f"Added task embedding for task {task_id}")
                    except Exception as add_error:
                        logger.error(f"Error adding task embedding to ChromaDB: {str(add_error)}")
            
            return {"task_id": task_id, "success": True}
        except Exception as e:
            logger.error(f"Error generating embedding for task {task_id}: {str(e)}")
            return {"task_id": task_id, "success": False, "error": str(e)}

    async def generate_all_tasks_embeddings(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """为所有任务生成嵌入"""
        await self.initialize_model()
        
        try:
            # 构建查询条件
            query = {}
            if project_id:
                query["project_id"] = ObjectId(project_id)
            
            # 查询任务
            tasks = await mongodb.db.tasks.find(query).to_list(length=None)
            
            logger.info(f"Found {len(tasks)} tasks to generate embeddings for")
            
            # 处理结果
            results = {
                "total": len(tasks),
                "success": 0,
                "failed": 0,
                "failures": []
            }
            
            # 批量处理
            for task in tasks:
                try:
                    logger.info(f"Generating embedding for task {task['_id']}: {task.get('summary', '')}")
                    result = await self.generate_task_embedding(
                        str(task["_id"]), 
                        task.get("summary", ""), 
                        task.get("description", "")
                    )
                    
                    if result["success"]:
                        results["success"] += 1
                    else:
                        results["failed"] += 1
                        results["failures"].append({
                            "task_id": str(task["_id"]),
                            "error": result.get("error", "Unknown error")
                        })
                except Exception as e:
                    logger.error(f"Error generating embedding for task {task['_id']}: {str(e)}")
                    results["failed"] += 1
                    results["failures"].append({
                        "task_id": str(task["_id"]),
                        "error": str(e)
                    })
            
            # 检查ChromaDB中的任务数量
            try:
                count = self._task_collection.count()
                logger.info(f"ChromaDB task collection now has {count} tasks")
            except Exception as e:
                logger.error(f"Error checking ChromaDB task count: {str(e)}")
            
            return results
        except Exception as e:
            logger.error(f"Error generating embeddings for tasks: {str(e)}")
            return {"success": False, "error": str(e)}

    async def semantic_search_tasks(self, query: str, project_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """使用语义搜索查找任务"""
        await self.initialize_model()
        
        try:
            # 检查集合中的任务数量
            try:
                count = self._task_collection.count()
                logger.info(f"ChromaDB task collection has {count} tasks")
                if count == 0:
                    logger.warning("No tasks in ChromaDB collection, returning empty results")
                    return []
            except Exception as e:
                logger.error(f"Error checking ChromaDB task count: {str(e)}")
            
            # 构建查询条件
            where_clause = {}
            if project_id:
                where_clause["project_id"] = project_id
            
            logger.info(f"Performing semantic search with query: '{query}', project_id: {project_id}, where_clause: {where_clause}")
            
            # 执行查询
            results = self._task_collection.query(
                query_texts=[query],
                where=where_clause if where_clause else None,
                n_results=limit,
                include=["documents", "metadatas", "distances"]
            )
            
            logger.info(f"Search results: {results}")
            
            # 处理结果
            search_results = []
            
            if results["ids"] and len(results["ids"][0]) > 0:
                for i, task_id in enumerate(results["ids"][0]):
                    metadata = results["metadatas"][0][i]
                    
                    # 计算得分 (1.0 - 距离)
                    score = 1.0 - (results["distances"][0][i] if results["distances"] else 0)
                    
                    # 获取完整任务
                    task = await mongodb.db.tasks.find_one({"_id": ObjectId(task_id)})
                    
                    if task:
                        # 高亮处理
                        highlight = self._create_highlight(
                            task.get("summary", ""),
                            task.get("description", ""),
                            query
                        )
                        
                        search_results.append({
                            "type": "task",
                            "id": task_id,
                            "score": score,
                            "highlight": highlight,
                            "data": {
                                "summary": task.get("summary", ""),
                                "status": task.get("status", ""),
                                "priority": task.get("priority", ""),
                                "project_id": str(task.get("project_id", "")),
                                "tags": task.get("tags", [])
                            }
                        })
            
            logger.info(f"Processed {len(search_results)} search results")
            return search_results
        except Exception as e:
            logger.error(f"Error performing semantic search: {str(e)}")
            return []

    def _create_highlight(self, summary: str, description: str, query: str, max_length: int = 100) -> str:
        """创建高亮显示文本"""
        import re
        
        # 如果描述为空，直接返回摘要
        if not description:
            return summary[:max_length] + "..." if len(summary) > max_length else summary
        
        # 查找查询词在描述中的位置
        description_lower = description.lower()
        query_lower = query.lower()
        
        if query_lower in description_lower:
            # 找到匹配位置
            match_pos = description_lower.find(query_lower)
            
            # 提取上下文
            start_pos = max(0, match_pos - 40)
            end_pos = min(len(description), match_pos + len(query) + 40)
            
            # 创建带有高亮标记的片段
            context = description[start_pos:end_pos]
            
            # 添加省略号
            if start_pos > 0:
                context = "..." + context
            if end_pos < len(description):
                context = context + "..."
            
            # 添加高亮标记
            pattern = re.compile(re.escape(query), re.IGNORECASE)
            highlighted = pattern.sub(r'<mark>\g<0></mark>', context)
            
            return highlighted
        
        # 如果在描述中找不到查询词，返回摘要
        return summary[:max_length] + "..." if len(summary) > max_length else summary

# 创建单例
task_embedding_service = TaskEmbeddingService() 