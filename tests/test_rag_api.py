import json
from unittest.mock import patch, MagicMock
from bson import ObjectId
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.models.rag_models import EmbeddingStatus, RAGQueryResponse, SearchResult

# 测试客户端
client = TestClient(app)

# 测试数据
MOCK_REPO_ID = "507f1f77bcf86cd799439011"
MOCK_OBJECT_ID = ObjectId(MOCK_REPO_ID)

MOCK_EMBEDDING_STATUS = {
    "_id": str(ObjectId("507f1f77bcf86cd799439015")),
    "repository_id": str(MOCK_OBJECT_ID),
    "status": "completed",
    "code_progress": 1.0,
    "docs_progress": 1.0,
    "total_code_files": 10,
    "processed_code_files": 10,
    "total_docs": 5,
    "processed_docs": 5,
    "last_updated": "2024-05-10T10:00:00"
}

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
    }
]

MOCK_RAG_RESPONSE = {
    "query": "如何使用formatDate函数?",
    "answer": "要使用formatDate函数，您需要先从utils.js文件中导入它，然后传入一个日期参数。",
    "sources": MOCK_SEARCH_RESULTS,
    "execution_time": 1.5
}

@patch('app.api.api_v1.endpoints.rag.embedding_service')
def test_generate_embeddings(mock_embedding_service):
    """测试生成嵌入API"""
    # 设置模拟
    mock_embedding_service.get_embedding_status.return_value = None
    mock_embedding_service.generate_repository_embeddings.return_value = True
    mock_embedding_service.get_embedding_status.side_effect = [None, MOCK_EMBEDDING_STATUS]
    
    # 发送请求
    response = client.post(f"/api/v1/rag/embeddings/generate/{MOCK_REPO_ID}")
    
    # 验证结果
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "status" in data
    mock_embedding_service.generate_repository_embeddings.assert_called_once_with(MOCK_REPO_ID, False)

@patch('app.api.api_v1.endpoints.rag.embedding_service')
def test_get_embedding_status(mock_embedding_service):
    """测试获取嵌入状态API"""
    # 设置模拟
    mock_embedding_service.get_embedding_status.return_value = MOCK_EMBEDDING_STATUS
    
    # 发送请求
    response = client.get(f"/api/v1/rag/embeddings/status/{MOCK_REPO_ID}")
    
    # 验证结果
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "status" in data
    mock_embedding_service.get_embedding_status.assert_called_once_with(MOCK_REPO_ID)

@patch('app.api.api_v1.endpoints.rag.rag_service')
def test_semantic_search(mock_rag_service):
    """测试语义搜索API"""
    # 设置模拟
    mock_rag_service.search.return_value = MOCK_SEARCH_RESULTS
    
    # 发送请求
    response = client.post(
        "/api/v1/rag/rag/search",
        json={
            "query": "如何使用formatDate函数?",
            "repo_id": MOCK_REPO_ID,
            "limit": 5
        }
    )
    
    # 验证结果
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 1
    assert data["count"] == 1
    assert data["query"] == "如何使用formatDate函数?"
    mock_rag_service.search.assert_called_once()

@patch('app.api.api_v1.endpoints.rag.rag_service')
def test_rag_query(mock_rag_service):
    """测试RAG查询API"""
    # 设置模拟
    mock_rag_service.rag_query.return_value = RAGQueryResponse(**MOCK_RAG_RESPONSE)
    
    # 发送请求
    response = client.post(
        "/api/v1/rag/rag/query",
        json={
            "query": "如何使用formatDate函数?",
            "repo_id": MOCK_REPO_ID,
            "context_limit": 5,
            "include_code": True,
            "include_docs": True
        }
    )
    
    # 验证结果
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["query"] == "如何使用formatDate函数?"
    assert data["data"]["answer"] == "要使用formatDate函数，您需要先从utils.js文件中导入它，然后传入一个日期参数。"
    assert len(data["data"]["sources"]) == 1
    mock_rag_service.rag_query.assert_called_once()

@patch('app.api.api_v1.endpoints.rag.embedding_service')
def test_delete_embeddings(mock_embedding_service):
    """测试删除嵌入API"""
    # 设置模拟
    mock_embedding_service.delete_embeddings.return_value = True
    
    # 发送请求
    response = client.delete(f"/api/v1/rag/embeddings/{MOCK_REPO_ID}")
    
    # 验证结果
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "message" in data
    mock_embedding_service.delete_embeddings.assert_called_once_with(MOCK_REPO_ID) 