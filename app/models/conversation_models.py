from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field
from app.models.base_models import MongoBaseModel, PyObjectId

class MessageRole(str, Enum):
    """消息发送者角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class MessageType(str, Enum):
    """消息类型"""
    TEXT = "text"
    CODE = "code"
    RAG_RESULT = "rag_result"
    TYPING = "typing"
    STATUS = "status"
    ERROR = "error"

class MessageStatus(str, Enum):
    """消息状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EDITED = "edited"

class RagReference(BaseModel):
    """RAG检索引用源"""
    file_id: str
    file_path: str
    file_name: str
    content: str
    score: float
    language: Optional[str] = None
    type: str  # code 或 doc
    metadata: Dict[str, Any] = {}

class Message(MongoBaseModel):
    """对话消息模型"""
    conversation_id: PyObjectId
    user_id: PyObjectId
    role: MessageRole
    content: str
    type: MessageType = MessageType.TEXT
    status: MessageStatus = MessageStatus.COMPLETED
    references: List[RagReference] = []
    edited: bool = False
    edited_at: Optional[datetime] = None
    original_content: Optional[str] = None
    metadata: Dict[str, Any] = {}
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "conversation_id": "507f1f77bcf86cd799439011",
                "user_id": "507f1f77bcf86cd799439012",
                "role": "user",
                "content": "如何实现用户认证功能?",
                "type": "text",
                "status": "completed",
                "created_at": "2023-05-03T10:00:00Z",
                "references": []
            }
        }
    }

class Conversation(MongoBaseModel):
    """对话会话模型"""
    title: str
    user_id: PyObjectId
    project_id: Optional[PyObjectId] = None
    repo_id: Optional[PyObjectId] = None
    is_pinned: bool = False
    last_message_at: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = 0
    settings: Dict[str, Any] = {
        "model": "gemini-2.5-flash-001",
        "temperature": 0.7,
        "max_tokens": 1000,
        "context_limit": 5,
        "include_code": True,
        "include_docs": True
    }
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "项目代码问答",
                "user_id": "507f1f77bcf86cd799439011",
                "project_id": "507f1f77bcf86cd799439013",
                "repo_id": "507f1f77bcf86cd799439014",
                "is_pinned": False,
                "created_at": "2023-05-03T10:00:00Z",
                "last_message_at": "2023-05-03T10:05:00Z",
                "message_count": 5
            }
        }
    }

class ConnectionState(MongoBaseModel):
    """连接状态模型"""
    connection_id: str
    user_id: PyObjectId
    status: str  # connected, disconnected, restored
    connected_at: datetime
    last_ping: datetime = Field(default_factory=datetime.utcnow)
    disconnected_at: Optional[datetime] = None
    active_conversation_id: Optional[str] = None
    client_info: Dict[str, Any] = {}
    restored_connection_id: Optional[str] = None

# API请求和响应模型

class CreateConversationRequest(BaseModel):
    """创建会话请求"""
    title: str
    project_id: Optional[str] = None
    repo_id: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

class MessageRequest(BaseModel):
    """发送消息请求"""
    content: str
    type: MessageType = MessageType.TEXT
    metadata: Dict[str, Any] = {}

class EditMessageRequest(BaseModel):
    """编辑消息请求"""
    content: str
    metadata: Dict[str, Any] = {}

class ConversationSettings(BaseModel):
    """会话设置"""
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    context_limit: Optional[int] = None
    include_code: Optional[bool] = None
    include_docs: Optional[bool] = None

class UpdateConversationRequest(BaseModel):
    """更新会话请求"""
    title: Optional[str] = None
    is_pinned: Optional[bool] = None
    settings: Optional[ConversationSettings] = None 