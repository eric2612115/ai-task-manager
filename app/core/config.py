import os
from typing import Dict, Any, List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 應用程式基本配置
    APP_NAME: str = "Task Management API"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True
    
    # MongoDB 配置
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "task_manager_db")
    
    # Redis 配置
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # 文件存儲配置
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))  # 10MB
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
    
    @field_validator("UPLOAD_DIR")
    def create_upload_dir_if_not_exists(cls, v):
        os.makedirs(v, exist_ok=True)
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
