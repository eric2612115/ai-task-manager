import asyncio
import logging
import os
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Generator
from bson import ObjectId

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from code_chunker import CodeChunker
from langchain.text_splitter import RecursiveCharacterTextSplitter
import torch
from transformers import AutoTokenizer, AutoModel
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.db.mongodb import mongodb
from app.models.rag_models import EmbeddingStatus

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        """初始化嵌入服务，加载模型和ChromaDB客户端"""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # 初始化ChromaDB客户端
        self.client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        
        # 通过延迟加载模型避免不必要的资源消耗
        self._codebert_tokenizer = None
        self._codebert_model = None
        self._sentence_transformer = None
        
        # ChromaDB嵌入函数
        self._code_embedding_function = None
        self._doc_embedding_function = None
        
        # 创建或获取集合
        self._code_collection = None
        self._doc_collection = None
        
        logger.info("EmbeddingService initialized")

    async def initialize_models(self):
        """异步初始化模型（实际加载过程）"""
        if self._codebert_tokenizer is None or self._codebert_model is None:
            loop = asyncio.get_event_loop()
            # 在线程池中加载模型，避免阻塞主事件循环
            self._codebert_tokenizer, self._codebert_model = await loop.run_in_executor(
                None, 
                self._load_codebert_model
            )
            
            # 创建代码嵌入函数 - 使用自定义嵌入函数
            class CodeBertEmbeddingFunction(SentenceTransformerEmbeddingFunction):
                def __init__(self, embedding_service):
                    self.embedding_service = embedding_service
                
                def __call__(self, texts: List[str]) -> List[List[float]]:
                    return self.embedding_service.generate_code_embeddings_sync(texts)
            
            self._code_embedding_function = CodeBertEmbeddingFunction(self)
            
            # 获取代码集合
            self._code_collection = self.get_or_create_collection(
                settings.CHROMA_COLLECTION_CODE,
                self._code_embedding_function
            )
        
        if self._sentence_transformer is None:
            loop = asyncio.get_event_loop()
            # 加载SentenceTransformer模型
            self._sentence_transformer = await loop.run_in_executor(
                None,
                self._load_sentence_transformer
            )
            
            # 创建文档嵌入函数 - 使用自定义嵌入函数
            class DocEmbeddingFunction(SentenceTransformerEmbeddingFunction):
                def __init__(self, embedding_service):
                    self.embedding_service = embedding_service
                
                def __call__(self, texts: List[str]) -> List[List[float]]:
                    return self.embedding_service.generate_doc_embeddings_sync(texts)
            
            self._doc_embedding_function = DocEmbeddingFunction(self)
            
            # 获取文档集合
            self._doc_collection = self.get_or_create_collection(
                settings.CHROMA_COLLECTION_DOCS,
                self._doc_embedding_function
            )
        
        logger.info("Models initialized successfully")
        return True

    def _load_codebert_model(self):
        """加载CodeBERT模型"""
        logger.info(f"Loading CodeBERT model from {settings.CODEBERT_MODEL}")
        tokenizer = AutoTokenizer.from_pretrained(settings.CODEBERT_MODEL)
        model = AutoModel.from_pretrained(settings.CODEBERT_MODEL).to(self.device)
        return tokenizer, model

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

    def generate_code_embeddings_sync(self, texts: List[str]) -> List[List[float]]:
        """同步生成代码嵌入"""
        try:
            # 处理空文本
            if not texts or all(not text.strip() for text in texts):
                return [[0.0] * 768] * len(texts)  # 返回零向量
            
            # 过滤空文本
            valid_texts = [text for text in texts if text.strip()]
            valid_indices = [i for i, text in enumerate(texts) if text.strip()]
            
            if not valid_texts:
                return [[0.0] * 768] * len(texts)
            
            # 使用CodeBERT进行嵌入
            inputs = self._codebert_tokenizer(
                valid_texts, 
                padding=True, 
                truncation=True, 
                return_tensors="pt", 
                max_length=512
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self._codebert_model(**inputs)
                # 使用[CLS]令牌的输出作为整个序列的表示
                embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
            
            # 为所有文本构建结果
            result = [[0.0] * 768] * len(texts)
            for i, idx in enumerate(valid_indices):
                result[idx] = embeddings[i].tolist()
            
            return result
        except Exception as e:
            logger.error(f"Error generating code embeddings: {str(e)}")
            return [[0.0] * 768] * len(texts)  # 出错时返回零向量

    def generate_doc_embeddings_sync(self, texts: List[str]) -> List[List[float]]:
        """同步生成文档嵌入"""
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
            logger.error(f"Error generating document embeddings: {str(e)}")
            return [[0.0] * 384] * len(texts)  # 出错时返回零向量

    def chunk_code(self, content: str, language: Optional[str] = None) -> List[str]:
        """使用code-chunker分割代码"""
        try:
            if not language:
                # 简单启发式方法检测语言
                language = "python"  # 默认为Python
                
                # 根据文件扩展名尝试检测语言
                file_ext_to_lang = {
                    ".py": "python", ".js": "javascript", ".ts": "typescript",
                    ".java": "java", ".cs": "csharp", ".cpp": "cpp", ".c": "c",
                    ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php"
                }
                
                # 尝试获取文件扩展名
                for ext, lang in file_ext_to_lang.items():
                    if content and ext in content.lower():
                        language = lang
                        break
            
            # 导入所需模块
            from code_chunker.models import ChunkerConfig
            
            # 使用CodeChunker处理代码
            config = ChunkerConfig(
                max_chunk_size=512,  # 使用正确的参数名
                overlap_size=50,     # 使用正确的参数名
            )
            
            chunker = CodeChunker(config=config)
            
            # 使用parse方法而不是chunk方法
            parse_result = chunker.parse(content, language=language)
            
            # 从解析结果中提取内容
            chunks = []
            for chunk in parse_result.chunks:
                chunks.append(chunk.content)
                
            return chunks
        except Exception as e:
            logger.error(f"Error chunking code: {str(e)}")
            # 降级为简单分块
            return self._simple_chunk_text(content, 512, 50)

    def chunk_doc(self, content: str) -> List[str]:
        """分割文档内容"""
        try:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,  # 文档分块尺寸
                chunk_overlap=100,
                length_function=len,
                is_separator_regex=False
            )
            chunks = text_splitter.split_text(content)
            return chunks
        except Exception as e:
            logger.error(f"Error chunking document: {str(e)}")
            # 降级为简单分块
            return self._simple_chunk_text(content, 1000, 100)

    def _simple_chunk_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """简单的文本分块方法（作为备选）"""
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunks.append(text[start:end])
            start = start + chunk_size - overlap
        
        return chunks

    async def generate_repository_embeddings(self, repo_id: str, force_regenerate: bool = False) -> bool:
        """为整个代码仓库生成嵌入"""
        repo_obj_id = ObjectId(repo_id)
        
        # 先检查模型是否已初始化
        await self.initialize_models()
        
        # 检查是否已存在进行中的任务
        existing_status = await mongodb.db.embedding_status.find_one({
            "repository_id": repo_obj_id,
            "status": {"$in": ["pending", "processing"]}
        })
        
        if existing_status and not force_regenerate:
            logger.info(f"Embedding generation already in progress for repository {repo_id}")
            return False
        
        # 创建或更新状态记录
        status_data = {
            "repository_id": repo_obj_id,
            "status": "processing",
            "code_progress": 0.0,
            "docs_progress": 0.0,
            "last_updated": datetime.utcnow(),
            "total_code_files": 0,
            "processed_code_files": 0,
            "total_docs": 0,
            "processed_docs": 0
        }
        
        if existing_status:
            await mongodb.db.embedding_status.update_one(
                {"_id": existing_status["_id"]},
                {"$set": status_data}
            )
            status_id = existing_status["_id"]
        else:
            result = await mongodb.db.embedding_status.insert_one(status_data)
            status_id = result.inserted_id
        
        # 在后台执行嵌入生成
        asyncio.create_task(self._process_repository_embeddings(repo_id, status_id))
        
        return True
    
    async def _process_repository_embeddings(self, repo_id: str, status_id: ObjectId):
        """处理仓库的嵌入生成（后台任务）"""
        repo_obj_id = ObjectId(repo_id)
        
        try:
            # 获取仓库信息
            repo = await mongodb.db.repositories.find_one({"_id": repo_obj_id})
            if not repo:
                await self._update_embedding_status(status_id, {"status": "failed", "error_message": "Repository not found"})
                return False
            
            # 处理代码文件
            await self._process_code_files(repo_id, status_id)
            
            # 处理文档
            await self._process_docs(repo_id, status_id)
            
            # 更新状态为完成
            await self._update_embedding_status(status_id, {
                "status": "completed",
                "code_progress": 1.0,
                "docs_progress": 1.0,
                "last_updated": datetime.utcnow()
            })
            
            logger.info(f"Completed embedding generation for repository {repo_id}")
            return True
            
        except Exception as e:
            error_message = f"Error processing repository embeddings: {str(e)}"
            logger.error(error_message)
            await self._update_embedding_status(status_id, {"status": "failed", "error_message": error_message})
            return False

    async def _process_code_files(self, repo_id: str, status_id: ObjectId):
        """处理代码文件嵌入"""
        repo_obj_id = ObjectId(repo_id)
        
        # 获取所有代码文件
        code_files_cursor = mongodb.db.code_files.find({
            "repository_id": repo_obj_id,
            "is_deleted": False
        })
        
        code_files = await code_files_cursor.to_list(length=None)
        total_files = len(code_files)
        
        # 更新状态
        await self._update_embedding_status(status_id, {
            "total_code_files": total_files,
            "processed_code_files": 0
        })
        
        if total_files == 0:
            logger.info(f"No code files found for repository {repo_id}")
            return
        
        # 删除现有嵌入（如果存在）
        try:
            self._code_collection.delete(where={"repo_id": repo_id})
            logger.info(f"Deleted existing code embeddings for repository {repo_id}")
        except Exception as e:
            logger.info(f"No existing code embeddings to delete for repository {repo_id}: {str(e)}")
        
        # 批量处理代码文件
        batch_size = 10
        processed_count = 0
        
        for i in range(0, total_files, batch_size):
            batch = code_files[i:i+batch_size]
            
            for file in batch:
                try:
                    # 根据语言分块代码
                    language = file.get("code_language")
                    content = file.get("content", "")
                    file_path = file.get("file_path", "")
                    
                    if not content.strip():
                        logger.warning(f"Empty content for file {file_path}")
                        continue
                    
                    # 分块代码
                    chunks = self.chunk_code(content, language)
                    
                    if not chunks:
                        logger.warning(f"No chunks generated for file {file_path}")
                        continue
                    
                    # 准备元数据和ID，确保没有 None 值
                    ids = [f"{repo_id}_{file['_id']}_{i}" for i in range(len(chunks))]
                    metadatas = []
                    
                    for i in range(len(chunks)):
                        metadata = {
                            "repo_id": repo_id,
                            "file_id": str(file["_id"]),
                            "file_path": file_path or "",
                            "file_name": file.get("file_name", "") or "",
                            "language": language or "unknown",
                            "chunk_index": i,
                            "total_chunks": len(chunks)
                        }
                        metadatas.append(metadata)
                    
                    # 添加到ChromaDB
                    self._code_collection.add(
                        documents=chunks,
                        ids=ids,
                        metadatas=metadatas
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing file {file.get('file_path')}: {str(e)}")
                
                processed_count += 1
                
                # 更新进度
                progress = processed_count / total_files
                await self._update_embedding_status(status_id, {
                    "code_progress": progress,
                    "processed_code_files": processed_count
                })
        
        logger.info(f"Processed {processed_count} code files for repository {repo_id}")

    async def _process_docs(self, repo_id: str, status_id: ObjectId):
        """处理文档嵌入"""
        repo_obj_id = ObjectId(repo_id)
        
        # 获取所有文档
        docs_cursor = mongodb.db.project_documentations.find({
            "repository_id": repo_obj_id,
            "is_deleted": False
        })
        
        docs = await docs_cursor.to_list(length=None)
        total_docs = len(docs)
        
        # 更新状态
        await self._update_embedding_status(status_id, {
            "total_docs": total_docs,
            "processed_docs": 0
        })
        
        if total_docs == 0:
            logger.info(f"No docs found for repository {repo_id}")
            return
        
        # 删除现有嵌入（如果存在）
        try:
            self._doc_collection.delete(where={"repo_id": repo_id})
            logger.info(f"Deleted existing doc embeddings for repository {repo_id}")
        except Exception as e:
            logger.info(f"No existing doc embeddings to delete for repository {repo_id}: {str(e)}")
        
        # 批量处理文档
        batch_size = 5
        processed_count = 0
        
        for i in range(0, total_docs, batch_size):
            batch = docs[i:i+batch_size]
            
            for doc in batch:
                try:
                    content = doc.get("content", "")
                    
                    if not content.strip():
                        logger.warning(f"Empty content for doc {doc.get('title')}")
                        continue
                    
                    # 分块文档
                    chunks = self.chunk_doc(content)
                    
                    if not chunks:
                        logger.warning(f"No chunks generated for doc {doc.get('title')}")
                        continue
                    
                    # 准备元数据和ID，确保没有 None 值
                    ids = [f"{repo_id}_doc_{doc['_id']}_{i}" for i in range(len(chunks))]
                    metadatas = []
                    
                    for i in range(len(chunks)):
                        metadata = {
                            "repo_id": repo_id,
                            "doc_id": str(doc["_id"]),
                            "title": doc.get("title", "") or "",
                            "chunk_index": i,
                            "total_chunks": len(chunks),
                            "type": "document"
                        }
                        metadatas.append(metadata)
                    
                    # 添加到ChromaDB
                    self._doc_collection.add(
                        documents=chunks,
                        ids=ids,
                        metadatas=metadatas
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing doc {doc.get('title')}: {str(e)}")
                
                processed_count += 1
                
                # 更新进度
                progress = processed_count / total_docs
                await self._update_embedding_status(status_id, {
                    "docs_progress": progress,
                    "processed_docs": processed_count
                })
        
        logger.info(f"Processed {processed_count} docs for repository {repo_id}")

    async def _update_embedding_status(self, status_id: ObjectId, updates: Dict[str, Any]):
        """更新嵌入状态"""
        updates["last_updated"] = datetime.utcnow()
        await mongodb.db.embedding_status.update_one(
            {"_id": status_id},
            {"$set": updates}
        )

    async def get_embedding_status(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """获取嵌入状态"""
        repo_obj_id = ObjectId(repo_id)
        status = await mongodb.db.embedding_status.find_one({"repository_id": repo_obj_id})
        return status

    async def delete_embeddings(self, repo_id: str) -> bool:
        """删除特定仓库的所有嵌入"""
        await self.initialize_models()
        
        try:
            # 删除代码嵌入
            self._code_collection.delete(where={"repo_id": repo_id})
            # 删除文档嵌入
            self._doc_collection.delete(where={"repo_id": repo_id})
            
            # 删除状态记录
            repo_obj_id = ObjectId(repo_id)
            await mongodb.db.embedding_status.delete_many({"repository_id": repo_obj_id})
            
            logger.info(f"Deleted all embeddings for repository {repo_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting embeddings for repository {repo_id}: {str(e)}")
            return False

    async def search_code(self, query: str, repo_id: str, limit: int = 5, file_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """搜索代码"""
        await self.initialize_models()
        
        try:
            where_clause = {"repo_id": repo_id}
            
            # 添加文件类型过滤
            if file_types and len(file_types) > 0:
                where_clause["language"] = {"$in": file_types}
            
            results = self._code_collection.query(
                query_texts=[query],
                where=where_clause,
                n_results=limit,
                include=["documents", "metadatas", "distances"]
            )
            
            # 返回结果
            search_results = []
            
            if results["ids"] and len(results["ids"][0]) > 0:
                for i, doc_id in enumerate(results["ids"][0]):
                    metadata = results["metadatas"][0][i]
                    
                    # 获取完整文件内容
                    file_id = metadata.get("file_id")
                    full_file = await mongodb.db.code_files.find_one({"_id": ObjectId(file_id)})
                    
                    if full_file:
                        search_results.append({
                            "file_id": file_id,
                            "file_path": metadata.get("file_path", ""),
                            "file_name": metadata.get("file_name", ""),
                            "content": full_file.get("content", ""),
                            "language": metadata.get("language"),
                            "score": 1.0 - (results["distances"][0][i] if results["distances"] else 0),
                            "type": "code",
                            "metadata": metadata
                        })
            
            return search_results
        
        except Exception as e:
            logger.error(f"Error searching code: {str(e)}")
            return []

    async def search_docs(self, query: str, repo_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """搜索文档"""
        await self.initialize_models()
        
        try:
            results = self._doc_collection.query(
                query_texts=[query],
                where={"repo_id": repo_id},
                n_results=limit,
                include=["documents", "metadatas", "distances"]
            )
            
            # 返回结果
            search_results = []
            
            if results["ids"] and len(results["ids"][0]) > 0:
                for i, doc_id in enumerate(results["ids"][0]):
                    metadata = results["metadatas"][0][i]
                    
                    # 获取完整文档内容
                    doc_id = metadata.get("doc_id")
                    full_doc = await mongodb.db.project_documentations.find_one({"_id": ObjectId(doc_id)})
                    
                    if full_doc:
                        search_results.append({
                            "file_id": doc_id,
                            "file_path": "",  # 文档没有文件路径
                            "file_name": metadata.get("title", ""),
                            "content": full_doc.get("content", ""),
                            "language": "markdown",  # 假设文档是Markdown格式
                            "score": 1.0 - (results["distances"][0][i] if results["distances"] else 0),
                            "type": "doc",
                            "metadata": metadata
                        })
            
            return search_results
        
        except Exception as e:
            logger.error(f"Error searching docs: {str(e)}")
            return []

    async def search(self, query: str, repo_id: str, collection: Optional[str] = None, limit: int = 5, file_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """搜索代码和文档"""
        code_results = []
        doc_results = []
        
        # 根据collection参数决定搜索类型
        if collection is None or collection == "both":
            code_results = await self.search_code(query, repo_id, limit, file_types)
            doc_results = await self.search_docs(query, repo_id, limit)
        elif collection == "code":
            code_results = await self.search_code(query, repo_id, limit, file_types)
        elif collection == "docs":
            doc_results = await self.search_docs(query, repo_id, limit)
        
        # 合并和排序结果
        all_results = code_results + doc_results
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # 返回限制数量的结果
        return all_results[:limit] 