import asyncio
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

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
from app.models.rag_models import RAGQueryResponse, SearchResult

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        """初始化RAG服务"""
        self.embedding_service = EmbeddingService()
        self._llms = {}  # 缓存LLM实例
        logger.info("RAGService initialized")

    async def search(self, query: str, repo_id: str, collection: Optional[str] = None, limit: int = 5, file_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """执行语义搜索"""
        return await self.embedding_service.search(query, repo_id, collection, limit, file_types)

    async def rag_query(self, 
                        query: str, 
                        repo_id: str, 
                        context_limit: int = 5, 
                        llm_model: Optional[str] = None, 
                        llm_provider: Optional[str] = None,
                        include_code: bool = True, 
                        include_docs: bool = True,
                        temperature: float = 0.7,
                        max_tokens: int = 1000,
                        file_types: Optional[List[str]] = None) -> RAGQueryResponse:
        """执行RAG查询"""
        start_time = time.time()
        
        # 确定要搜索的集合
        collection = None
        if include_code and not include_docs:
            collection = "code"
        elif include_docs and not include_code:
            collection = "docs"
        
        # 执行搜索
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
                language=result["language"],
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
            else:
                context_parts.append(f"[Source {i+1}: Document - {file_name}]")
            
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