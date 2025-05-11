import os
from typing import Dict, Any, List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv, find_dotenv
import secrets
from cryptography.fernet import Fernet

class Settings(BaseSettings):
    load_dotenv(find_dotenv())
    # 應用程式基本配置
    APP_NAME: str = "Task Management API"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True
    
    # MongoDB 配置
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "task_manager_db")
    
    # For compatibility with db_client.py
    MONGODB_URI: str = MONGODB_URL
    MONGODB_DATABASE: str = MONGODB_DB_NAME
    
    # Redis 配置
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # 文件存儲配置
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", 10485760))
    ALLOWED_UPLOAD_TYPES: List[str] = ["image/jpeg", "image/png", "image/gif", "application/pdf", 
                                       "text/plain", "application/msword", 
                                       "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                       "application/vnd.ms-excel", 
                                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]
    
    # CORS配置
    CORS_ORIGINS: List[str] = [
        "*",  # 允许所有来源（开发环境）
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
        "https://lovable.dev",
        "https://*.lovable.dev",
        "https://*.lovable.app",
        "https://lovableproject.com",
        "https://*.lovableproject.com"
    ]
    
    # 安全配置 (為未來的認證模塊預留)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here-for-jwt-tokens")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 小時
    
    # Git凭证加密密钥
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "zULrahkKOCpvWbhfr-PNc_jMTJYqXEucc_Nw85GNjfk=")  # 固定默认密钥，仅用于开发环境
    
    # AI Provider Config encryption settings
    ENCRYPTION_SECRET_KEY: str = os.getenv("ENCRYPTION_SECRET_KEY", "ai-provider-encryption-key-for-secure-storage")
    ENCRYPTION_SALT: str = os.getenv("ENCRYPTION_SALT", "ai-provider-salt-value-for-kdf")
    
    # ChromaDB 配置
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    CHROMA_COLLECTION_CODE: str = os.getenv("CHROMA_COLLECTION_CODE", "code_embeddings")
    CHROMA_COLLECTION_DOCS: str = os.getenv("CHROMA_COLLECTION_DOCS", "doc_embeddings")

    # 模型配置
    CODEBERT_MODEL: str = os.getenv("CODEBERT_MODEL", "microsoft/codebert-base")
    SENTENCE_TRANSFORMER_MODEL: str = os.getenv("SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2")

    # LLM 配置
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")  # openai, anthropic, google
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    
    @field_validator("UPLOAD_DIR")
    def create_upload_dir_if_not_exists(cls, v):
        os.makedirs(v, exist_ok=True)
        return v
    
    # 确保ChromaDB持久化目录存在
    @field_validator("CHROMA_PERSIST_DIR")
    def create_chroma_dir_if_not_exists(cls, v):
        os.makedirs(v, exist_ok=True)
        return v
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True
    }

settings = Settings()
