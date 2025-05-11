from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body, status
from typing import Optional, List
from . import schemas, services
from app.core.utils import get_current_user_id  # Assumed auth dependency

router = APIRouter(prefix="/ai/config", tags=["AI Provider Configuration"])

# Create a new AI provider configuration
@router.post("/providers/", response_model=schemas.AIConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_ai_provider_config(
    config_data: schemas.AIConfigCreate,
    current_user_id: str = Depends(get_current_user_id)
):
    """Create a new AI provider configuration"""
    try:
        new_config = await services.create_new_ai_config(current_user_id, config_data)
        return new_config
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create AI provider configuration: {str(e)}"
        )

# Get list of AI provider configurations
@router.get("/providers/", response_model=schemas.AIConfigListResponse)
async def get_ai_provider_configs(
    provider_name: Optional[str] = Query(None, description="Filter by provider name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
    current_user_id: str = Depends(get_current_user_id)
):
    """Get all AI provider configurations for the current user"""
    configs, total = await services.get_all_ai_configs_for_user(
        current_user_id, provider_name, is_active, skip, limit
    )
    return {
        "success": True,
        "data": configs,
        "total": total,
        "skip": skip,
        "limit": limit
    }

# Get a single AI provider configuration
@router.get("/providers/{config_id}", response_model=schemas.AIConfigResponse)
async def get_ai_provider_config(
    config_id: str = Path(..., description="The ID of the AI provider configuration"),
    current_user_id: str = Depends(get_current_user_id)
):
    """Get a specific AI provider configuration by ID"""
    config = await services.get_ai_config_detail_by_id(current_user_id, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI provider configuration with ID {config_id} not found"
        )
    return config

# Update an AI provider configuration
@router.put("/providers/{config_id}", response_model=schemas.AIConfigResponse)
async def update_ai_provider_config(
    config_id: str = Path(..., description="The ID of the AI provider configuration to update"),
    update_data: schemas.AIConfigUpdate = Body(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """Update an existing AI provider configuration"""
    updated_config = await services.update_existing_ai_config(
        current_user_id, config_id, update_data
    )
    if not updated_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI provider configuration with ID {config_id} not found"
        )
    return updated_config

# Delete an AI provider configuration
@router.delete("/providers/{config_id}", response_model=schemas.GeneralSuccessMessage)
async def delete_ai_provider_config(
    config_id: str = Path(..., description="The ID of the AI provider configuration to delete"),
    current_user_id: str = Depends(get_current_user_id)
):
    """Delete an AI provider configuration"""
    deleted_count = await services.delete_ai_config_by_id(current_user_id, config_id)
    if deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI provider configuration with ID {config_id} not found"
        )
    return {
        "success": True,
        "message": "AI provider configuration deleted successfully"
    }

# Get list of supported AI providers
@router.get("/supported-providers/", response_model=schemas.SupportedProvidersListResponse)
async def get_supported_providers():
    """Get a list of supported AI providers with their configuration schemas"""
    providers = await services.get_supported_providers()
    return {
        "success": True,
        "data": providers
    }

# Update supported AI providers
@router.put("/supported-providers/", response_model=schemas.SupportedProvidersListResponse)
async def update_supported_providers(
    data: schemas.UpdateSupportedProvidersRequest = Body(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """Update the list of supported AI providers with their configuration schemas"""
    try:
        providers = await services.update_supported_providers(data.providers)
        return {
            "success": True,
            "data": providers
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update supported providers: {str(e)}"
        )

# Update provider models based on model name list
@router.post("/supported-providers/update-models", response_model=schemas.SupportedProvidersListResponse)
async def update_provider_models(
    ai_model_names: List[str] = Body(..., embed=True),
    current_user_id: str = Depends(get_current_user_id)
):
    """Update provider models based on a list of model names"""
    try:
        providers = await services.update_provider_models(ai_model_names)
        return {
            "success": True,
            "data": providers
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update provider models: {str(e)}"
        ) 