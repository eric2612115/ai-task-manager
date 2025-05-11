# Suggested file: app/ai_configs/services.py
# Implementation for AI configuration services

from . import schemas
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timezone
import uuid
import json
from pydantic import ValidationError

# Import encryption utilities and database client
# Will create these if they don't exist
from app.core.encryption_util import encrypt, decrypt
from app.core.db_client import get_db_client

async def create_new_ai_config(user_id: str, config_data: schemas.AIConfigCreate) -> schemas.AIConfigResponse:
    """Create a new AI provider configuration for a user"""
    # 1. Encrypt API key
    encrypted_api_key = encrypt(config_data.api_key)
    
    # 2. Encrypt sensitive fields in additional_config
    encrypted_additional_config = encrypt_sensitive_additional_config(
        config_data.provider_name, 
        config_data.additional_config
    )
    
    # 3. Create database document
    db_client = await get_db_client()
    db_doc = {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "provider_name": config_data.provider_name.value,
        "display_name": config_data.display_name or f"{config_data.provider_name.value} Config",
        "api_key_encrypted": encrypted_api_key,
        "is_active": config_data.is_active,
        "models": config_data.models or [],
        "additional_config_encrypted": encrypted_additional_config,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    
    # 4. Insert into database
    await db_client.ai_provider_configs.insert_one(db_doc)
    
    # 5. Convert DB document to response schema
    response_data = {
        "id": db_doc["_id"],
        "user_id": db_doc["user_id"],
        "provider_name": db_doc["provider_name"],
        "display_name": db_doc["display_name"],
        "is_active": db_doc["is_active"],
        "models": db_doc["models"],
        "additional_config": mask_sensitive_fields(
            config_data.provider_name, 
            config_data.additional_config
        ),
        "created_at": db_doc["created_at"],
        "updated_at": db_doc["updated_at"]
    }
    
    return schemas.AIConfigResponse(**response_data)

async def get_all_ai_configs_for_user(
    user_id: str, 
    provider_name: Optional[str] = None, 
    is_active: Optional[bool] = None,
    skip: int = 0, 
    limit: int = 20
) -> Tuple[List[schemas.AIConfigResponse], int]:
    """Get all AI provider configurations for a user with optional filters"""
    # 1. Build query filters
    query = {"user_id": user_id}
    if provider_name:
        query["provider_name"] = provider_name
    if is_active is not None:
        query["is_active"] = is_active
    
    # 2. Query database
    db_client = await get_db_client()
    total = await db_client.ai_provider_configs.count_documents(query)
    cursor = db_client.ai_provider_configs.find(query).skip(skip).limit(limit).sort("created_at", -1)
    
    # 3. Format response
    configs = []
    async for doc in cursor:
        # Convert ObjectId to string if needed
        doc["id"] = doc.pop("_id")
        
        # Mask sensitive info in additional_config
        if "additional_config_encrypted" in doc and doc["additional_config_encrypted"]:
            decrypted_config = json.loads(decrypt(doc["additional_config_encrypted"]))
            provider_enum = schemas.AIProviderName(doc["provider_name"])
            doc["additional_config"] = mask_sensitive_fields(provider_enum, decrypted_config)
        else:
            doc["additional_config"] = {}
        
        # Remove encrypted fields from response
        doc.pop("api_key_encrypted", None)
        doc.pop("additional_config_encrypted", None)
        
        configs.append(schemas.AIConfigResponse(**doc))
    
    return configs, total

async def get_ai_config_detail_by_id(user_id: str, config_id: str) -> Optional[schemas.AIConfigResponse]:
    """Get detailed information about a specific AI provider configuration"""
    # 1. Find document by ID and user_id
    db_client = await get_db_client()
    doc = await db_client.ai_provider_configs.find_one({
        "_id": config_id,
        "user_id": user_id
    })
    
    if not doc:
        return None
    
    # 2. Format response
    doc["id"] = doc.pop("_id")
    
    # 3. Mask sensitive info in additional_config
    if "additional_config_encrypted" in doc and doc["additional_config_encrypted"]:
        decrypted_config = json.loads(decrypt(doc["additional_config_encrypted"]))
        provider_enum = schemas.AIProviderName(doc["provider_name"])
        doc["additional_config"] = mask_sensitive_fields(provider_enum, decrypted_config)
    else:
        doc["additional_config"] = {}
    
    # 4. Remove encrypted fields from response
    doc.pop("api_key_encrypted", None)
    doc.pop("additional_config_encrypted", None)
    
    return schemas.AIConfigResponse(**doc)

async def update_existing_ai_config(
    user_id: str, 
    config_id: str, 
    update_data: schemas.AIConfigUpdate
) -> Optional[schemas.AIConfigResponse]:
    """Update an existing AI provider configuration"""
    # 1. Find the existing config
    db_client = await get_db_client()
    existing_config = await db_client.ai_provider_configs.find_one({
        "_id": config_id,
        "user_id": user_id
    })
    
    if not existing_config:
        return None
    
    # 2. Prepare update data
    update_dict = {}
    
    # Handle display_name update
    if update_data.display_name is not None:
        update_dict["display_name"] = update_data.display_name
    
    # Handle API key update (with encryption)
    if update_data.api_key:
        update_dict["api_key_encrypted"] = encrypt(update_data.api_key)
    
    # Handle is_active update
    if update_data.is_active is not None:
        update_dict["is_active"] = update_data.is_active
    
    # Handle models update
    if update_data.models is not None:
        update_dict["models"] = update_data.models
    
    # Handle additional_config update (with encryption)
    if update_data.additional_config is not None:
        provider_enum = schemas.AIProviderName(existing_config["provider_name"])
        encrypted_additional_config = encrypt_sensitive_additional_config(
            provider_enum, 
            update_data.additional_config
        )
        update_dict["additional_config_encrypted"] = encrypted_additional_config
    
    # Always update the updated_at timestamp
    update_dict["updated_at"] = datetime.now(timezone.utc)
    
    # 3. Update in database
    if update_dict:
        await db_client.ai_provider_configs.update_one(
            {"_id": config_id, "user_id": user_id},
            {"$set": update_dict}
        )
    
    # 4. Return updated config
    return await get_ai_config_detail_by_id(user_id, config_id)

async def delete_ai_config_by_id(user_id: str, config_id: str) -> int:
    """Delete an AI provider configuration"""
    db_client = await get_db_client()
    result = await db_client.ai_provider_configs.delete_one({
        "_id": config_id,
        "user_id": user_id
    })
    return result.deleted_count

# Store supported providers in-memory cache
_supported_providers_cache = None

async def get_supported_providers() -> List[schemas.SupportedProvider]:
    """Get list of supported AI providers with their configuration schemas"""
    global _supported_providers_cache
    
    # Return cached providers if available
    if _supported_providers_cache is not None:
        return _supported_providers_cache
    
    # Try to load from database first
    db_client = await get_db_client()
    db_providers = await db_client.supported_ai_providers.find({}).to_list(length=None)
    
    if db_providers and len(db_providers) > 0:
        # Convert from database format to schema
        providers = []
        for provider in db_providers:
            provider_data = {
                "provider_name": provider["provider_name"],
                "display_name": provider["display_name"],
                "credentials_schema": provider["credentials_schema"],
                "models": provider.get("models", [])
            }
            providers.append(schemas.SupportedProvider(**provider_data))
        
        _supported_providers_cache = providers
        return providers
    
    # If no data in database, return hardcoded defaults
    providers = [
        schemas.SupportedProvider(
            provider_name=schemas.AIProviderName.OPENAI,
            display_name="OpenAI",
            credentials_schema={
                "api_key": schemas.SupportedProviderCredentialItem(
                    type="password", 
                    required=True, 
                    label="API Key"
                )
            },
            models=[
                schemas.SupportedProviderModelInfo(id="gpt-4o", name="GPT-4o"),
                schemas.SupportedProviderModelInfo(id="gpt-4-turbo", name="GPT-4 Turbo"),
                schemas.SupportedProviderModelInfo(id="gpt-3.5-turbo", name="GPT-3.5 Turbo"),
            ]
        ),
        schemas.SupportedProvider(
            provider_name=schemas.AIProviderName.GOOGLE,
            display_name="Google AI",
            credentials_schema={
                "api_key": schemas.SupportedProviderCredentialItem(
                    type="password", 
                    required=True, 
                    label="API Key (Google AI Studio)"
                )
            },
            models=[
                schemas.SupportedProviderModelInfo(id="gemini-1.5-pro-latest", name="Gemini 1.5 Pro"),
                schemas.SupportedProviderModelInfo(id="gemini-1.5-flash-latest", name="Gemini 1.5 Flash"),
            ]
        ),
        schemas.SupportedProvider(
            provider_name=schemas.AIProviderName.ANTHROPIC,
            display_name="Anthropic",
            credentials_schema={
                "api_key": schemas.SupportedProviderCredentialItem(
                    type="password", 
                    required=True, 
                    label="API Key"
                )
            },
            models=[
                schemas.SupportedProviderModelInfo(id="claude-3-opus-20240229", name="Claude 3 Opus"),
                schemas.SupportedProviderModelInfo(id="claude-3-sonnet-20240229", name="Claude 3 Sonnet"),
                schemas.SupportedProviderModelInfo(id="claude-3-haiku-20240307", name="Claude 3 Haiku"),
            ]
        ),
        schemas.SupportedProvider(
            provider_name=schemas.AIProviderName.AZURE_OPENAI,
            display_name="Azure OpenAI",
            credentials_schema={
                "api_key": schemas.SupportedProviderCredentialItem(
                    type="password", 
                    required=True, 
                    label="API Key"
                ),
                "azure_base_url": schemas.SupportedProviderCredentialItem(
                    type="text", 
                    required=True, 
                    label="Azure Endpoint URL"
                ),
                "azure_deployment_name": schemas.SupportedProviderCredentialItem(
                    type="text", 
                    required=True, 
                    label="Deployment Name"
                )
            },
            models=[]  # Azure models are determined by deployment
        ),
        schemas.SupportedProvider(
            provider_name=schemas.AIProviderName.AWS_BEDROCK,
            display_name="AWS Bedrock",
            credentials_schema={
                "aws_access_key_id": schemas.SupportedProviderCredentialItem(
                    type="text", 
                    required=True, 
                    label="AWS Access Key ID"
                ),
                "aws_secret_access_key": schemas.SupportedProviderCredentialItem(
                    type="password", 
                    required=True, 
                    label="AWS Secret Access Key"
                ),
                "aws_region": schemas.SupportedProviderCredentialItem(
                    type="text", 
                    required=True, 
                    label="AWS Region"
                )
            },
            models=[
                schemas.SupportedProviderModelInfo(id="anthropic.claude-3-sonnet-20240229-v1:0", name="Claude 3 Sonnet (AWS)"),
                schemas.SupportedProviderModelInfo(id="anthropic.claude-3-haiku-20240307-v1:0", name="Claude 3 Haiku (AWS)"),
            ]
        ),
    ]
    
    # Set the cache
    _supported_providers_cache = providers
    
    # Also save to database for persistence
    try:
        for provider in providers:
            await db_client.supported_ai_providers.update_one(
                {"provider_name": provider.provider_name},
                {"$set": provider.model_dump()},
                upsert=True
            )
    except Exception as e:
        print(f"Error saving providers to database: {e}")
    
    return providers

async def update_supported_providers(providers: List[schemas.SupportedProvider]) -> List[schemas.SupportedProvider]:
    """Update the list of supported AI providers with their configuration schemas"""
    global _supported_providers_cache
    
    # Clear cache
    _supported_providers_cache = None
    
    # Save to database
    db_client = await get_db_client()
    
    for provider in providers:
        await db_client.supported_ai_providers.update_one(
            {"provider_name": provider.provider_name},
            {"$set": provider.model_dump()},
            upsert=True
        )
    
    # Set new cache
    _supported_providers_cache = providers
    
    return providers

async def update_provider_models(ai_model_names: List[str]) -> List[schemas.SupportedProvider]:
    """Update provider models based on a list of model names"""
    # Get current providers
    providers = await get_supported_providers()
    
    # Group models by provider
    provider_models = {
        schemas.AIProviderName.OPENAI: [],
        schemas.AIProviderName.GOOGLE: [],
        schemas.AIProviderName.ANTHROPIC: [],
        schemas.AIProviderName.XAI: [],
        schemas.AIProviderName.CURSOR: [],
        schemas.AIProviderName.DEEPSEEK: [],
    }
    
    for model_name in ai_model_names:
        if model_name.startswith("gpt-"):
            provider_models[schemas.AIProviderName.OPENAI].append(model_name)
        elif model_name.startswith("gemini-"):
            provider_models[schemas.AIProviderName.GOOGLE].append(model_name)
        elif model_name.startswith("claude-"):
            provider_models[schemas.AIProviderName.ANTHROPIC].append(model_name)
        elif model_name.startswith("grok-"):
            provider_models[schemas.AIProviderName.XAI].append(model_name)
        elif model_name.startswith("cursor-"):
            provider_models[schemas.AIProviderName.CURSOR].append(model_name)
        elif model_name.startswith("deepseek-"):
            provider_models[schemas.AIProviderName.DEEPSEEK].append(model_name)
        elif model_name.startswith("o1-") or model_name.startswith("o3-") or model_name.startswith("o4-") or model_name == "o1" or model_name == "o3" or model_name == "o4":
            # Opus models like o1, o3 belong to Anthropic
            provider_models[schemas.AIProviderName.ANTHROPIC].append(model_name)
    
    # Update each provider's models
    for provider in providers:
        if provider.provider_name in provider_models and provider_models[provider.provider_name]:
            # Create model info objects for each model name
            provider.models = [
                schemas.SupportedProviderModelInfo(id=model, name=model)
                for model in provider_models[provider.provider_name]
            ]
    
    # Add new providers if needed
    existing_provider_names = {p.provider_name for p in providers}
    
    # Add Cursor provider if it has models but doesn't exist yet
    if schemas.AIProviderName.CURSOR not in existing_provider_names and provider_models[schemas.AIProviderName.CURSOR]:
        providers.append(
            schemas.SupportedProvider(
                provider_name=schemas.AIProviderName.CURSOR,
                display_name="Cursor AI",
                credentials_schema={
                    "api_key": schemas.SupportedProviderCredentialItem(
                        type="password", 
                        required=True, 
                        label="API Key"
                    )
                },
                models=[
                    schemas.SupportedProviderModelInfo(id=model, name=model)
                    for model in provider_models[schemas.AIProviderName.CURSOR]
                ]
            )
        )
    
    # Add DeepSeek provider if it has models but doesn't exist yet
    if schemas.AIProviderName.DEEPSEEK not in existing_provider_names and provider_models[schemas.AIProviderName.DEEPSEEK]:
        providers.append(
            schemas.SupportedProvider(
                provider_name=schemas.AIProviderName.DEEPSEEK,
                display_name="DeepSeek AI",
                credentials_schema={
                    "api_key": schemas.SupportedProviderCredentialItem(
                        type="password", 
                        required=True, 
                        label="API Key"
                    )
                },
                models=[
                    schemas.SupportedProviderModelInfo(id=model, name=model)
                    for model in provider_models[schemas.AIProviderName.DEEPSEEK]
                ]
            )
        )
    
    # Add xAI provider if it has models but doesn't exist yet
    if schemas.AIProviderName.XAI not in existing_provider_names and provider_models[schemas.AIProviderName.XAI]:
        providers.append(
            schemas.SupportedProvider(
                provider_name=schemas.AIProviderName.XAI,
                display_name="xAI (Grok)",
                credentials_schema={
                    "api_key": schemas.SupportedProviderCredentialItem(
                        type="password", 
                        required=True, 
                        label="API Key"
                    )
                },
                models=[
                    schemas.SupportedProviderModelInfo(id=model, name=model)
                    for model in provider_models[schemas.AIProviderName.XAI]
                ]
            )
        )
    
    # Save updated providers
    return await update_supported_providers(providers)

# Helper functions
def encrypt_sensitive_additional_config(provider: schemas.AIProviderName, additional_config: Optional[Dict[str, Any]]) -> Optional[str]:
    """Encrypt sensitive fields in additional_config based on provider type"""
    if not additional_config:
        return None
    
    # Create a copy to avoid modifying the original
    encrypted_config = additional_config.copy()
    
    if provider == schemas.AIProviderName.AWS_BEDROCK:
        if "aws_access_key_id" in encrypted_config:
            encrypted_config["aws_access_key_id"] = encrypt(encrypted_config["aws_access_key_id"])
        if "aws_secret_access_key" in encrypted_config:
            encrypted_config["aws_secret_access_key"] = encrypt(encrypted_config["aws_secret_access_key"])
    
    # Handle other providers with sensitive additional_config fields
    # e.g., Azure OpenAI, etc.
    
    # Return JSON string of encrypted config
    return json.dumps(encrypted_config)

def mask_sensitive_fields(provider: schemas.AIProviderName, config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Create masked version of sensitive fields for API responses"""
    if not config:
        return {}
    
    # Create a copy to avoid modifying the original
    masked_config = config.copy()
    
    if provider == schemas.AIProviderName.AWS_BEDROCK:
        if "aws_access_key_id" in masked_config:
            masked_config["aws_access_key_id"] = "****" + masked_config["aws_access_key_id"][-4:]
        if "aws_secret_access_key" in masked_config:
            masked_config["aws_secret_access_key"] = "****" + masked_config["aws_secret_access_key"][-4:]
    
    # Handle other providers with sensitive additional_config fields
    
    return masked_config