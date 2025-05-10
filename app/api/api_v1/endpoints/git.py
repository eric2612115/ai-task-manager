from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, Path, Body
from pydantic import BaseModel, Field
from bson import ObjectId
from datetime import datetime

from app.models.git_models import GitCredentialCreate, GitCredentialUpdate, GitCredentialTest, RepositoryCreate, RepositoryUpdate
from app.services.git_service import GitService
from app.services.git_sync_service import GitSyncService
from app.core.utils import serialize_mongodb_doc

router = APIRouter()
git_service = GitService()
git_sync_service = GitSyncService()

# ============== 凭证管理 API ==============

@router.post("/credentials", response_model=dict)
async def create_git_credential(credential: GitCredentialCreate, background_tasks: BackgroundTasks):
    """创建Git凭证并在后台测试连接"""
    try:
        # 创建凭证
        result = await git_service.create_credential(credential.model_dump())
        
        # 在后台测试连接并更新状态
        credential_id = str(result["_id"])
        background_tasks.add_task(git_service.test_connection, credential_id)
        
        return {
            "success": True,
            "data": serialize_mongodb_doc(result),
            "message": "Credential created successfully, connection test running in background"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/credentials", response_model=dict)
async def get_git_credentials(skip: int = 0, limit: int = 100):
    """获取所有Git凭证"""
    try:
        result = await git_service.get_credentials(skip, limit)
        return {
            "success": True,
            "data": serialize_mongodb_doc(result),
            "count": len(result)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/credentials/{credential_id}", response_model=dict)
async def get_git_credential(credential_id: str):
    """获取单个Git凭证"""
    try:
        result = await git_service.get_credential(credential_id)
        if not result:
            raise HTTPException(status_code=404, detail="Credential not found")
            
        return {
            "success": True,
            "data": serialize_mongodb_doc(result)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/credentials/{credential_id}", response_model=dict)
async def update_git_credential(credential_id: str, credential: GitCredentialUpdate):
    """更新Git凭证"""
    try:
        result = await git_service.update_credential(credential_id, credential.model_dump(exclude_none=True))
        if not result:
            raise HTTPException(status_code=404, detail="Credential not found")
            
        return {
            "success": True,
            "data": serialize_mongodb_doc(result),
            "message": "Credential updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/credentials/{credential_id}", response_model=dict)
async def delete_git_credential(credential_id: str):
    """删除Git凭证"""
    try:
        result = await git_service.delete_credential(credential_id)
        if not result:
            raise HTTPException(status_code=404, detail="Credential not found")
            
        return {
            "success": True,
            "message": "Credential deleted successfully"
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/credentials/{credential_id}/test", response_model=dict)
async def test_git_credential(credential_id: str):
    """测试Git凭证连接"""
    try:
        # 先获取当前凭证
        credential = await git_service.get_credential(credential_id)
        if not credential:
            raise HTTPException(status_code=404, detail="Credential not found")
            
        # 测试连接
        result = await git_service.test_connection(credential_id)
        
        # 再次获取凭证以获取更新后的状态
        updated_credential = await git_service.get_credential(credential_id)
        
        return {
            "success": True,
            "connected": result,
            "message": "Connection successful" if result else "Connection failed",
            "status": {
                "status": updated_credential.get("status", "unknown"),
                "last_validated": updated_credential.get("last_validated"),
                "platform": updated_credential.get("platform", "unknown")
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/credentials/test-token", response_model=dict)
async def test_git_token(credential: GitCredentialTest):
    """直接测试Git token有效性，无需先保存凭证"""
    try:
        result = await git_service.test_token_directly(
            credential.platform, 
            credential.token, 
            credential.base_url
        )
        
        # 构建状态信息
        status = "active" if result.get("valid", False) else "invalid"
        
        return {
            "success": True,
            "data": result,
            "status": {
                "status": status,
                "platform": credential.platform,
                "base_url": credential.base_url,
                "last_validated": datetime.utcnow().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============== 仓库管理 API ==============

@router.get("/repos/discover", response_model=dict)
async def discover_repositories(credential_id: str):
    """发现可访问的仓库"""
    try:
        result = await git_service.discover_repositories(credential_id)
        return {
            "success": True,
            "data": serialize_mongodb_doc(result),
            "count": len(result)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/repos", response_model=dict)
async def create_repository(repo: RepositoryCreate):
    """创建仓库记录"""
    try:
        result = await git_service.create_repository(repo.model_dump())
        return {
            "success": True,
            "data": serialize_mongodb_doc(result),
            "message": "Repository created successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/repos", response_model=dict)
async def get_repositories(skip: int = 0, limit: int = 100):
    """获取所有仓库"""
    try:
        result = await git_service.get_repositories(skip, limit)
        return {
            "success": True,
            "data": serialize_mongodb_doc(result),
            "count": len(result)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/repos/{repo_id}", response_model=dict)
async def get_repository(repo_id: str):
    """获取单个仓库"""
    try:
        result = await git_service.get_repository(repo_id)
        if not result:
            raise HTTPException(status_code=404, detail="Repository not found")
            
        return {
            "success": True,
            "data": serialize_mongodb_doc(result)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/repos/{repo_id}", response_model=dict)
async def update_repository(repo_id: str, repo: RepositoryUpdate):
    """更新仓库"""
    try:
        result = await git_service.update_repository(repo_id, repo.model_dump(exclude_none=True))
        if not result:
            raise HTTPException(status_code=404, detail="Repository not found")
            
        return {
            "success": True,
            "data": serialize_mongodb_doc(result),
            "message": "Repository updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/repos/{repo_id}", response_model=dict)
async def delete_repository(repo_id: str):
    """删除仓库"""
    try:
        result = await git_service.delete_repository(repo_id)
        if not result:
            raise HTTPException(status_code=404, detail="Repository not found")
            
        return {
            "success": True,
            "message": "Repository deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============== 同步操作 API ==============

@router.post("/repos/{repo_id}/sync", response_model=dict)
async def sync_repository(
    repo_id: str, 
    background_tasks: BackgroundTasks, 
    sync_type: str = Query("full", description="同步类型：full或incremental")
):
    """同步仓库"""
    # 验证同步类型
    if sync_type not in ["full", "incremental"]:
        raise HTTPException(status_code=400, detail="Invalid sync type, must be 'full' or 'incremental'")
    
    try:
        # 检查仓库是否存在
        repo = await git_service.get_repository(repo_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        # 检查仓库状态
        if repo.get("sync_status") == "syncing":
            return {
                "success": False,
                "message": "Repository is already syncing",
                "sync_status": repo.get("sync_status")
            }
        
        # 在后台执行同步
        background_tasks.add_task(git_sync_service.sync_repository, repo_id, sync_type)
        
        return {
            "success": True,
            "message": f"Repository synchronization ({sync_type}) started",
            "sync_status": "syncing"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/repos/{repo_id}/sync/status", response_model=dict)
async def get_sync_status(repo_id: str):
    """获取仓库同步状态"""
    try:
        result = await git_sync_service.get_sync_status(repo_id)
        return {
            "success": True,
            "data": serialize_mongodb_doc(result)
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/repos/{repo_id}/sync/history", response_model=dict)
async def get_sync_history(repo_id: str, skip: int = 0, limit: int = 10):
    """获取仓库同步历史"""
    try:
        result = await git_sync_service.get_sync_history(repo_id, skip, limit)
        return {
            "success": True,
            "data": serialize_mongodb_doc(result),
            "count": len(result)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 