# Suggested file: app/ai_configs/schemas.py

from pydantic import BaseModel, Field, validator, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
import enum

# 全局配置为避免protected_namespaces问题
model_config = ConfigDict(protected_namespaces=())

class AIProviderName(str, enum.Enum):
    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    AWS_BEDROCK = "aws_bedrock"
    DEEPSEEK = "deepseek"
    XAI = "xai"
    CURSOR = "cursor"

class AIConfigBase(BaseModel):
    provider_name: AIProviderName
    display_name: Optional[str] = None
    is_active: bool = True
    models: Optional[List[str]] = Field(default_factory=list)
    additional_config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    model_config = model_config

class AIConfigCreate(AIConfigBase):
    api_key: str = Field(..., description="The API key for the provider. Will be encrypted by the backend.")

class AIConfigUpdate(BaseModel):
    display_name: Optional[str] = None
    api_key: Optional[str] = Field(None, description="New API key if updating. Will be encrypted.")
    is_active: Optional[bool] = None
    models: Optional[List[str]] = None
    additional_config: Optional[Dict[str, Any]] = None
    
    model_config = model_config

class AIConfigResponse(AIConfigBase):
    id: str
    user_id: str
    # API key is omitted for security. Additional sensitive fields in additional_config should also be masked.
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, use_enum_values=True, **model_config)

class AIConfigListResponse(BaseModel):
    success: bool = True
    data: List[AIConfigResponse]
    total: int
    skip: int
    limit: int
    
    model_config = model_config

class SupportedProviderCredentialItem(BaseModel):
    type: str = Field(description="Input type for frontend, e.g., 'text', 'password'")
    required: bool
    label: str
    
    model_config = model_config

class SupportedProviderModelInfo(BaseModel):
    id: str
    name: str
    
    model_config = model_config

class SupportedProvider(BaseModel):
    provider_name: AIProviderName
    display_name: str
    credentials_schema: Dict[str, SupportedProviderCredentialItem]
    models: List[SupportedProviderModelInfo] = Field(default_factory=list)
    
    model_config = model_config

class SupportedProvidersListResponse(BaseModel):
    success: bool = True
    data: List[SupportedProvider]
    
    model_config = model_config

class UpdateSupportedProvidersRequest(BaseModel):
    """Request model for updating supported providers"""
    providers: List[SupportedProvider]
    
    model_config = model_config

class GeneralSuccessMessage(BaseModel):
    success: bool = True
    message: str
    
    model_config = model_config