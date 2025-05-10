import unittest
import asyncio
from unittest.mock import patch, MagicMock
import pytest
from bson import ObjectId

from app.services.embedding_service import EmbeddingService

# 设置测试环境
pytestmark = pytest.mark.asyncio

# 测试数据
MOCK_REPO_ID = "507f1f77bcf86cd799439011"
MOCK_OBJECT_ID = ObjectId(MOCK_REPO_ID)

MOCK_CODE_FILES = [
    {
        "_id": ObjectId("507f1f77bcf86cd799439012"),
        "repository_id": MOCK_OBJECT_ID,
        "file_path": "src/main.py",
        "file_name": "main.py",
        "content": "def hello_world():\n    print('Hello, World!')\n\nif __name__ == '__main__':\n    hello_world()",
        "code_language": "python",
        "is_deleted": False
    },
    {
        "_id": ObjectId("507f1f77bcf86cd799439013"),
        "repository_id": MOCK_OBJECT_ID,
        "file_path": "src/utils.js",
        "file_name": "utils.js",
        "content": "function formatDate(date) {\n  return new Date(date).toLocaleDateString();\n}\n\nexport { formatDate };",
        "code_language": "javascript",
        "is_deleted": False
    }
]

MOCK_DOCS = [
    {
        "_id": ObjectId("507f1f77bcf86cd799439014"),
        "repository_id": MOCK_OBJECT_ID,
        "title": "Getting Started",
        "content": "# Getting Started\n\nThis is a guide to help you get started with the project.\n\n## Installation\n\n```bash\nnpm install\n```",
        "is_deleted": False
    }
]

class TestEmbeddingService(unittest.TestCase):
    """测试嵌入服务"""
    
    def setUp(self):
        """设置测试环境"""
        self.embedding_service = EmbeddingService()
        
        # 模拟ChromaDB集合
        self.mock_code_collection = MagicMock()
        self.mock_doc_collection = MagicMock()
        
        # 设置模拟ChromaDB的返回值
        self.embedding_service._code_collection = self.mock_code_collection
        self.embedding_service._doc_collection = self.mock_doc_collection
        
        # 模拟代码和文档嵌入方法
        self.embedding_service.generate_code_embeddings_sync = MagicMock(return_value=[[0.1] * 768])
        self.embedding_service.generate_doc_embeddings_sync = MagicMock(return_value=[[0.2] * 384])
        
    @patch('app.services.embedding_service.mongodb')
    async def test_get_embedding_status(self, mock_mongodb):
        """测试获取嵌入状态"""
        # 设置模拟返回值
        mock_status = {
            "_id": ObjectId("507f1f77bcf86cd799439015"),
            "repository_id": MOCK_OBJECT_ID,
            "status": "completed",
            "code_progress": 1.0,
            "docs_progress": 1.0
        }
        mock_mongodb.db.embedding_status.find_one.return_value = mock_status
        
        # 调用方法
        status = await self.embedding_service.get_embedding_status(MOCK_REPO_ID)
        
        # 验证结果
        self.assertEqual(status, mock_status)
        mock_mongodb.db.embedding_status.find_one.assert_called_once_with({"repository_id": MOCK_OBJECT_ID})
    
    @patch('app.services.embedding_service.mongodb')
    @patch.object(EmbeddingService, 'initialize_models')
    async def test_generate_repository_embeddings(self, mock_initialize, mock_mongodb):
        """测试生成仓库嵌入"""
        # 设置模拟返回值
        mock_initialize.return_value = True
        mock_mongodb.db.embedding_status.find_one.return_value = None
        mock_mongodb.db.embedding_status.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        
        # 调用方法
        result = await self.embedding_service.generate_repository_embeddings(MOCK_REPO_ID)
        
        # 验证结果
        self.assertTrue(result)
        mock_initialize.assert_called_once()
        mock_mongodb.db.embedding_status.find_one.assert_called_once()
        mock_mongodb.db.embedding_status.insert_one.assert_called_once()
    
    def test_chunk_code(self):
        """测试代码分块"""
        # 测试Python代码
        python_code = "def hello_world():\n    print('Hello, World!')\n"
        python_chunks = self.embedding_service.chunk_code(python_code, "python")
        self.assertGreaterEqual(len(python_chunks), 1)
        
        # 测试JavaScript代码
        js_code = "function formatDate(date) {\n  return new Date(date).toLocaleDateString();\n}\n"
        js_chunks = self.embedding_service.chunk_code(js_code, "javascript")
        self.assertGreaterEqual(len(js_chunks), 1)
    
    def test_chunk_doc(self):
        """测试文档分块"""
        doc_content = "# Getting Started\n\nThis is a guide to help you get started with the project.\n\n## Installation\n\n```bash\nnpm install\n```"
        doc_chunks = self.embedding_service.chunk_doc(doc_content)
        self.assertGreaterEqual(len(doc_chunks), 1)
    
    @patch('app.services.embedding_service.mongodb')
    async def test_search_code(self, mock_mongodb):
        """测试代码搜索"""
        # 设置模拟ChromaDB查询结果
        self.mock_code_collection.query.return_value = {
            "ids": [["doc1"]],
            "documents": [["def hello_world():"]],
            "metadatas": [[{
                "file_id": "507f1f77bcf86cd799439012",
                "file_path": "src/main.py",
                "file_name": "main.py",
                "language": "python"
            }]],
            "distances": [[0.1]]
        }
        
        # 设置MongoDB返回完整文件
        mock_mongodb.db.code_files.find_one.return_value = MOCK_CODE_FILES[0]
        
        # 调用方法
        await self.embedding_service.initialize_models = MagicMock(return_value=True)
        result = await self.embedding_service.search_code("hello world", MOCK_REPO_ID, 5)
        
        # 验证结果
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["file_id"], "507f1f77bcf86cd799439012")
        self.assertEqual(result[0]["language"], "python")
        self.mock_code_collection.query.assert_called_once()
    
    @patch('app.services.embedding_service.mongodb')
    async def test_delete_embeddings(self, mock_mongodb):
        """测试删除嵌入"""
        # 设置模拟
        self.mock_code_collection.delete.return_value = None
        self.mock_doc_collection.delete.return_value = None
        mock_mongodb.db.embedding_status.delete_many.return_value = MagicMock(deleted_count=1)
        
        # 调用方法
        await self.embedding_service.initialize_models = MagicMock(return_value=True)
        result = await self.embedding_service.delete_embeddings(MOCK_REPO_ID)
        
        # 验证结果
        self.assertTrue(result)
        self.mock_code_collection.delete.assert_called_once_with(where={"repo_id": MOCK_REPO_ID})
        self.mock_doc_collection.delete.assert_called_once_with(where={"repo_id": MOCK_REPO_ID})
        mock_mongodb.db.embedding_status.delete_many.assert_called_once() 