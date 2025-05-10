import unittest
import asyncio
from unittest.mock import patch, MagicMock
import pytest
from bson import ObjectId

from app.services.rag_service import RAGService
from app.models.rag_models import RAGQueryResponse, SearchResult

# 设置测试环境
pytestmark = pytest.mark.asyncio

# 测试数据
MOCK_REPO_ID = "507f1f77bcf86cd799439011"
MOCK_QUERY = "如何使用这个项目中的formatDate函数？"

MOCK_SEARCH_RESULTS = [
    {
        "file_id": "507f1f77bcf86cd799439012",
        "file_path": "src/utils.js",
        "file_name": "utils.js",
        "content": "function formatDate(date) {\n  return new Date(date).toLocaleDateString();\n}\n\nexport { formatDate };",
        "language": "javascript",
        "score": 0.95,
        "type": "code",
        "metadata": {
            "repo_id": MOCK_REPO_ID,
            "file_id": "507f1f77bcf86cd799439012",
            "language": "javascript"
        }
    },
    {
        "file_id": "507f1f77bcf86cd799439013",
        "file_path": "",
        "file_name": "API Documentation",
        "content": "# API Documentation\n\n## Utils\n\n### formatDate(date)\n\nFormats a date object to a localized string.\n\n**Parameters:**\n- date: Date object or string\n\n**Returns:**\n- Formatted date string",
        "language": "markdown",
        "score": 0.85,
        "type": "doc",
        "metadata": {
            "repo_id": MOCK_REPO_ID,
            "doc_id": "507f1f77bcf86cd799439013"
        }
    }
]

MOCK_LLM_RESPONSE = "要使用formatDate函数，您需要先从utils.js文件中导入它，然后传入一个日期参数。例如:\n```javascript\nimport { formatDate } from './utils';\n\nconst today = new Date();\nconst formattedDate = formatDate(today);\nconsole.log(formattedDate); // 输出当前日期的本地化字符串\n```\n\n这个函数接受一个日期对象或日期字符串作为参数，并返回一个本地化的日期字符串。"

class TestRAGService(unittest.TestCase):
    """测试RAG服务"""
    
    def setUp(self):
        """设置测试环境"""
        self.rag_service = RAGService()
        self.rag_service.embedding_service = MagicMock()
    
    @patch.object(RAGService, '_get_llm')
    async def test_rag_query_with_context(self, mock_get_llm):
        """测试带上下文的RAG查询"""
        # 设置模拟
        self.rag_service.embedding_service.search.return_value = MOCK_SEARCH_RESULTS
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        
        # 设置模拟LLM生成
        self.rag_service._generate_answer_with_context = MagicMock(return_value=MOCK_LLM_RESPONSE)
        
        # 调用方法
        response = await self.rag_service.rag_query(
            query=MOCK_QUERY,
            repo_id=MOCK_REPO_ID,
            context_limit=2
        )
        
        # 验证结果
        self.assertIsInstance(response, RAGQueryResponse)
        self.assertEqual(response.query, MOCK_QUERY)
        self.assertEqual(response.answer, MOCK_LLM_RESPONSE)
        self.assertEqual(len(response.sources), 2)
        self.rag_service.embedding_service.search.assert_called_once_with(
            query=MOCK_QUERY,
            repo_id=MOCK_REPO_ID,
            collection=None,
            limit=2,
            file_types=None
        )
    
    @patch.object(RAGService, '_get_llm')
    async def test_rag_query_without_context(self, mock_get_llm):
        """测试没有上下文的RAG查询"""
        # 设置模拟
        self.rag_service.embedding_service.search.return_value = []
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        
        # 设置模拟LLM生成
        self.rag_service._generate_answer_without_context = MagicMock(
            return_value="我没有找到相关信息，但通常formatDate函数用于格式化日期。"
        )
        
        # 调用方法
        response = await self.rag_service.rag_query(
            query=MOCK_QUERY,
            repo_id=MOCK_REPO_ID
        )
        
        # 验证结果
        self.assertIsInstance(response, RAGQueryResponse)
        self.assertEqual(response.query, MOCK_QUERY)
        self.assertEqual(len(response.sources), 0)
        self.rag_service.embedding_service.search.assert_called_once()
        self.rag_service._generate_answer_without_context.assert_called_once()
    
    @patch.object(RAGService, '_get_llm')
    async def test_rag_query_filtered_collection(self, mock_get_llm):
        """测试过滤集合的RAG查询"""
        # 设置模拟
        self.rag_service.embedding_service.search.return_value = [MOCK_SEARCH_RESULTS[0]]
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        
        # 设置模拟LLM生成
        self.rag_service._generate_answer_with_context = MagicMock(return_value=MOCK_LLM_RESPONSE)
        
        # 调用方法
        response = await self.rag_service.rag_query(
            query=MOCK_QUERY,
            repo_id=MOCK_REPO_ID,
            include_docs=False,
            include_code=True
        )
        
        # 验证结果
        self.assertEqual(len(response.sources), 1)
        self.rag_service.embedding_service.search.assert_called_once_with(
            query=MOCK_QUERY,
            repo_id=MOCK_REPO_ID,
            collection="code",
            limit=5,
            file_types=None
        )
    
    async def test_prepare_context(self):
        """测试上下文准备"""
        # 调用方法
        context = self.rag_service._prepare_context(MOCK_SEARCH_RESULTS)
        
        # 验证结果
        self.assertIsInstance(context, str)
        self.assertIn("Source 1: Code File - src/utils.js", context)
        self.assertIn("Language: javascript", context)
        self.assertIn("function formatDate", context)
        self.assertIn("Source 2: Document - API Documentation", context)
    
    @patch('app.services.rag_service.ChatOpenAI')
    async def test_get_llm_openai(self, mock_openai):
        """测试获取OpenAI LLM"""
        # 设置模拟
        mock_openai.return_value = MagicMock()
        
        # 调用方法
        with patch('app.services.rag_service.settings') as mock_settings:
            mock_settings.LLM_PROVIDER = "openai"
            mock_settings.OPENAI_API_KEY = "test-key"
            
            llm = await self.rag_service._get_llm(provider="openai", model="gpt-3.5-turbo")
        
        # 验证结果
        self.assertIsNotNone(llm)
        mock_openai.assert_called_once()
    
    @patch('app.services.rag_service.ChatAnthropic')
    async def test_get_llm_anthropic(self, mock_anthropic):
        """测试获取Anthropic LLM"""
        # 设置模拟
        mock_anthropic.return_value = MagicMock()
        
        # 调用方法
        with patch('app.services.rag_service.settings') as mock_settings:
            mock_settings.LLM_PROVIDER = "anthropic"
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            
            llm = await self.rag_service._get_llm(provider="anthropic", model="claude-3-sonnet-20240229")
        
        # 验证结果
        self.assertIsNotNone(llm)
        mock_anthropic.assert_called_once()
    
    @patch('app.services.rag_service.ChatGoogleGenerativeAI')
    async def test_get_llm_google(self, mock_google):
        """测试获取Google LLM"""
        # 设置模拟
        mock_google.return_value = MagicMock()
        
        # 调用方法
        with patch('app.services.rag_service.settings') as mock_settings:
            mock_settings.LLM_PROVIDER = "google"
            mock_settings.GOOGLE_API_KEY = "test-key"
            
            llm = await self.rag_service._get_llm(provider="google", model="gemini-pro")
        
        # 验证结果
        self.assertIsNotNone(llm)
        mock_google.assert_called_once() 