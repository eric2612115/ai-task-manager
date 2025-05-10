import aiohttp
import base64
import os
import logging
import urllib.parse
from typing import List, Dict, Optional, Union, Any
from datetime import datetime
from bson import ObjectId
import asyncio

from app.core.config import settings
from app.db.mongodb import mongodb
from app.services.git_service import GitService

logger = logging.getLogger(__name__)

class GitSyncService:
    def __init__(self):
        self.git_service = GitService()

    async def sync_repository(self, repo_id: str, sync_type: str = "full") -> Dict:
        """同步仓库"""
        repo = await mongodb.db.repositories.find_one({"_id": ObjectId(repo_id)})
        if not repo:
            raise ValueError("Repository not found")
        
        # 更新仓库状态为同步中
        await mongodb.db.repositories.update_one(
            {"_id": ObjectId(repo_id)},
            {"$set": {"sync_status": "syncing"}}
        )
        
        # 创建同步记录
        sync_history = {
            "repository_id": ObjectId(repo_id),
            "sync_type": sync_type,
            "started_at": datetime.utcnow(),
            "status": "running",
            "files_processed": 0,
            "files_added": 0,
            "files_updated": 0,
            "files_deleted": 0
        }
        
        sync_result = await mongodb.db.sync_history.insert_one(sync_history)
        sync_id = sync_result.inserted_id
        
        try:
            if sync_type == "full":
                await self._full_sync(repo, sync_id)
            else:
                await self._incremental_sync(repo, sync_id)
            
            # 更新同步成功状态
            await mongodb.db.sync_history.update_one(
                {"_id": sync_id},
                {"$set": {
                    "status": "completed",
                    "completed_at": datetime.utcnow()
                }}
            )
            
            # 更新仓库同步状态
            await mongodb.db.repositories.update_one(
                {"_id": ObjectId(repo_id)},
                {"$set": {
                    "sync_status": "completed",
                    "last_synced_at": datetime.utcnow()
                }}
            )
            
        except Exception as e:
            logger.error(f"Repository sync failed: {str(e)}")
            
            # 更新同步失败状态
            await mongodb.db.sync_history.update_one(
                {"_id": sync_id},
                {"$set": {
                    "status": "failed",
                    "completed_at": datetime.utcnow(),
                    "error_message": str(e)
                }}
            )
            
            await mongodb.db.repositories.update_one(
                {"_id": ObjectId(repo_id)},
                {"$set": {"sync_status": "failed"}}
            )
            
            raise
        
        return await mongodb.db.sync_history.find_one({"_id": sync_id})
    
    async def get_sync_status(self, repo_id: str) -> Dict:
        """获取仓库同步状态"""
        repo = await mongodb.db.repositories.find_one(
            {"_id": ObjectId(repo_id)},
            {"sync_status": 1, "last_synced_at": 1}
        )
        
        if not repo:
            raise ValueError("Repository not found")
        
        # 查找最近的同步历史
        latest_sync = await mongodb.db.sync_history.find_one(
            {"repository_id": ObjectId(repo_id)},
            sort=[("started_at", -1)]
        )
        
        result = {
            "sync_status": repo.get("sync_status", "pending"),
            "last_synced_at": repo.get("last_synced_at"),
            "latest_sync": latest_sync
        }
        
        return result
    
    async def get_sync_history(self, repo_id: str, skip: int = 0, limit: int = 10) -> List[Dict]:
        """获取仓库同步历史"""
        cursor = mongodb.db.sync_history.find(
            {"repository_id": ObjectId(repo_id)}
        ).sort("started_at", -1).skip(skip).limit(limit)
        
        return await cursor.to_list(length=limit)

    async def _full_sync(self, repo: Dict, sync_id: ObjectId):
        """全量同步"""
        credential = await mongodb.db.git_credentials.find_one({"_id": repo["credential_id"]})
        if not credential:
            raise ValueError("Credential not found")
        
        token = self.git_service.decrypt_token(credential["token"])
        
        # 标记所有现有文件为删除状态
        await mongodb.db.code_files.update_many(
            {"repository_id": repo["_id"]},
            {"$set": {"is_deleted": True}}
        )
        
        if repo["platform"] == "github":
            await self._sync_github_files(repo, credential, token, sync_id)
        else:  # gitlab
            await self._sync_gitlab_files(repo, credential, token, sync_id)
    
    async def _incremental_sync(self, repo: Dict, sync_id: ObjectId):
        """增量同步"""
        if not repo.get("last_commit_sha"):
            # 如果没有上次同步记录，执行全量同步
            return await self._full_sync(repo, sync_id)
        
        credential = await mongodb.db.git_credentials.find_one({"_id": repo["credential_id"]})
        if not credential:
            raise ValueError("Credential not found")
        
        token = self.git_service.decrypt_token(credential["token"])
        
        if repo["platform"] == "github":
            await self._incremental_sync_github(repo, credential, token, sync_id)
        else:  # gitlab
            await self._incremental_sync_gitlab(repo, credential, token, sync_id)
    
    async def _sync_github_files(self, repo: Dict, credential: Dict, token: str, sync_id: ObjectId):
        """同步GitHub文件"""
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        async with aiohttp.ClientSession() as session:
            # 获取默认分支的最新commit
            branch_url = f"https://api.github.com/repos/{repo['full_name']}/branches/{repo['default_branch']}"
            async with session.get(branch_url, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Failed to get branch info: {response.status}")
                
                branch_data = await response.json()
                latest_commit_sha = branch_data["commit"]["sha"]
            
            # 获取文件树
            tree_url = f"https://api.github.com/repos/{repo['full_name']}/git/trees/{latest_commit_sha}?recursive=1"
            async with session.get(tree_url, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Failed to get tree: {response.status}")
                
                tree_data = await response.json()
            
            files_processed = 0
            files_added = 0
            files_updated = 0
            
            # 处理每个文件
            for item in tree_data["tree"]:
                if item["type"] == "blob":  # 只处理文件，不处理目录
                    files_processed += 1
                    
                    try:
                        file_path = item["path"]
                        
                        # 判断是否为二进制文件，跳过
                        if self._is_likely_binary(file_path):
                            continue
                        
                        # 获取文件内容
                        file_url = f"https://api.github.com/repos/{repo['full_name']}/contents/{file_path}?ref={repo['default_branch']}"
                        async with session.get(file_url, headers=headers) as file_response:
                            if file_response.status != 200:
                                continue
                            
                            file_data = await file_response.json()
                            
                            # 解码文件内容
                            try:
                                content = base64.b64decode(file_data["content"]).decode("utf-8")
                            except:
                                # 二进制文件或解码失败，跳过
                                continue
                            
                            # 检查文件是否已存在
                            existing_file = await mongodb.db.code_files.find_one({
                                "repository_id": repo["_id"],
                                "file_path": file_path
                            })
                            
                            file_doc = {
                                "repository_id": repo["_id"],
                                "file_path": file_path,
                                "file_name": os.path.basename(file_path),
                                "content": content,
                                "code_language": self._detect_language(file_path),
                                "size_bytes": file_data["size"],
                                "line_count": content.count('\n') + 1,
                                "commit_sha": latest_commit_sha,
                                "branch": repo["default_branch"],
                                "last_modified": datetime.utcnow(),
                                "is_deleted": False,
                                "updated_at": datetime.utcnow()
                            }
                            
                            if existing_file:
                                # 更新现有文件
                                await mongodb.db.code_files.update_one(
                                    {"_id": existing_file["_id"]},
                                    {"$set": file_doc}
                                )
                                files_updated += 1
                            else:
                                # 创建新文件
                                file_doc["created_at"] = datetime.utcnow()
                                await mongodb.db.code_files.insert_one(file_doc)
                                files_added += 1
                    
                    except Exception as e:
                        logger.error(f"Error processing file: {str(e)}")
                        continue
                    
                    # 定期更新同步进度
                    if files_processed % 20 == 0:
                        await mongodb.db.sync_history.update_one(
                            {"_id": sync_id},
                            {"$set": {
                                "files_processed": files_processed,
                                "files_added": files_added,
                                "files_updated": files_updated
                            }}
                        )
            
            # 更新同步历史记录
            files_deleted = await mongodb.db.code_files.count_documents({
                "repository_id": repo["_id"],
                "is_deleted": True
            })
            
            await mongodb.db.sync_history.update_one(
                {"_id": sync_id},
                {"$set": {
                    "files_processed": files_processed,
                    "files_added": files_added,
                    "files_updated": files_updated,
                    "files_deleted": files_deleted,
                    "to_commit": latest_commit_sha
                }}
            )
            
            # 更新仓库信息
            await mongodb.db.repositories.update_one(
                {"_id": repo["_id"]},
                {"$set": {
                    "last_commit_sha": latest_commit_sha
                }}
            )
    
    async def _sync_gitlab_files(self, repo: Dict, credential: Dict, token: str, sync_id: ObjectId):
        """同步GitLab文件"""
        base_url = credential.get("base_url", "https://gitlab.com")
        
        headers = {
            "PRIVATE-TOKEN": token
        }
        
        async with aiohttp.ClientSession() as session:
            # 获取默认分支的最新commit
            project_id = urllib.parse.quote(repo["full_name"], safe='')
            branch_url = f"{base_url}/api/v4/projects/{project_id}/repository/branches/{repo['default_branch']}"
            
            async with session.get(branch_url, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Failed to get branch info: {response.status}")
                
                branch_data = await response.json()
                latest_commit_sha = branch_data["commit"]["id"]
            
            # 获取仓库文件树
            tree_url = f"{base_url}/api/v4/projects/{project_id}/repository/tree?recursive=true&per_page=100"
            
            files_processed = 0
            files_added = 0
            files_updated = 0
            page = 1
            
            all_files = []
            
            # 获取所有文件列表
            while True:
                async with session.get(f"{tree_url}&page={page}", headers=headers) as response:
                    if response.status != 200:
                        break
                    
                    tree_data = await response.json()
                    if not tree_data:
                        break
                    
                    all_files.extend([item for item in tree_data if item["type"] == "blob"])
                    
                    if len(tree_data) < 100:
                        break
                    
                    page += 1
            
            # 处理每个文件
            for item in all_files:
                files_processed += 1
                
                try:
                    file_path = item["path"]
                    
                    # 判断是否为二进制文件，跳过
                    if self._is_likely_binary(file_path):
                        continue
                    
                    # 获取文件内容
                    encoded_path = urllib.parse.quote(file_path, safe='')
                    file_url = f"{base_url}/api/v4/projects/{project_id}/repository/files/{encoded_path}/raw?ref={repo['default_branch']}"
                    
                    async with session.get(file_url, headers=headers) as file_response:
                        if file_response.status != 200:
                            continue
                        
                        content = await file_response.text()
                        
                        # 检查文件是否已存在
                        existing_file = await mongodb.db.code_files.find_one({
                            "repository_id": repo["_id"],
                            "file_path": file_path
                        })
                        
                        file_doc = {
                            "repository_id": repo["_id"],
                            "file_path": file_path,
                            "file_name": os.path.basename(file_path),
                            "content": content,
                            "code_language": self._detect_language(file_path),
                            "size_bytes": len(content),
                            "line_count": content.count('\n') + 1,
                            "commit_sha": latest_commit_sha,
                            "branch": repo["default_branch"],
                            "last_modified": datetime.utcnow(),
                            "is_deleted": False,
                            "updated_at": datetime.utcnow()
                        }
                        
                        if existing_file:
                            # 更新现有文件
                            await mongodb.db.code_files.update_one(
                                {"_id": existing_file["_id"]},
                                {"$set": file_doc}
                            )
                            files_updated += 1
                        else:
                            # 创建新文件
                            file_doc["created_at"] = datetime.utcnow()
                            await mongodb.db.code_files.insert_one(file_doc)
                            files_added += 1
                
                except Exception as e:
                    logger.error(f"Error processing file: {str(e)}")
                    continue
                
                # 定期更新同步进度
                if files_processed % 20 == 0:
                    await mongodb.db.sync_history.update_one(
                        {"_id": sync_id},
                        {"$set": {
                            "files_processed": files_processed,
                            "files_added": files_added,
                            "files_updated": files_updated
                        }}
                    )
            
            # 更新同步历史记录
            files_deleted = await mongodb.db.code_files.count_documents({
                "repository_id": repo["_id"],
                "is_deleted": True
            })
            
            await mongodb.db.sync_history.update_one(
                {"_id": sync_id},
                {"$set": {
                    "files_processed": files_processed,
                    "files_added": files_added,
                    "files_updated": files_updated,
                    "files_deleted": files_deleted,
                    "to_commit": latest_commit_sha
                }}
            )
            
            # 更新仓库信息
            await mongodb.db.repositories.update_one(
                {"_id": repo["_id"]},
                {"$set": {
                    "last_commit_sha": latest_commit_sha
                }}
            )
    
    async def _incremental_sync_github(self, repo: Dict, credential: Dict, token: str, sync_id: ObjectId):
        """GitHub增量同步"""
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        async with aiohttp.ClientSession() as session:
            # 获取最新commit
            branch_url = f"https://api.github.com/repos/{repo['full_name']}/branches/{repo['default_branch']}"
            async with session.get(branch_url, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Failed to get branch info: {response.status}")
                branch_data = await response.json()
                latest_commit_sha = branch_data["commit"]["sha"]
            
            # 如果没有新提交，直接返回
            if latest_commit_sha == repo["last_commit_sha"]:
                await mongodb.db.sync_history.update_one(
                    {"_id": sync_id},
                    {"$set": {
                        "status": "completed",
                        "completed_at": datetime.utcnow(),
                        "files_processed": 0,
                        "from_commit": repo["last_commit_sha"],
                        "to_commit": latest_commit_sha
                    }}
                )
                return
            
            # 获取两个commit之间的差异
            compare_url = f"https://api.github.com/repos/{repo['full_name']}/compare/{repo['last_commit_sha']}...{latest_commit_sha}"
            async with session.get(compare_url, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Failed to get comparison: {response.status}")
                compare_data = await response.json()
            
            files_processed = 0
            files_added = 0
            files_updated = 0
            files_deleted = 0
            
            # 处理变更的文件
            for file in compare_data.get("files", []):
                files_processed += 1
                file_path = file["filename"]
                
                # 判断是否为二进制文件，跳过
                if self._is_likely_binary(file_path):
                    continue
                
                if file["status"] == "removed":
                    # 标记文件为删除
                    await mongodb.db.code_files.update_one(
                        {
                            "repository_id": repo["_id"],
                            "file_path": file_path
                        },
                        {"$set": {"is_deleted": True, "updated_at": datetime.utcnow()}}
                    )
                    files_deleted += 1
                
                elif file["status"] in ["added", "modified"]:
                    # 获取文件内容
                    file_url = f"https://api.github.com/repos/{repo['full_name']}/contents/{file_path}?ref={latest_commit_sha}"
                    async with session.get(file_url, headers=headers) as file_response:
                        if file_response.status != 200:
                            continue
                        
                        file_data = await file_response.json()
                        
                        try:
                            content = base64.b64decode(file_data["content"]).decode("utf-8")
                        except:
                            continue
                        
                        # 检查文件是否已存在
                        existing_file = await mongodb.db.code_files.find_one({
                            "repository_id": repo["_id"],
                            "file_path": file_path
                        })
                        
                        file_doc = {
                            "repository_id": repo["_id"],
                            "file_path": file_path,
                            "file_name": os.path.basename(file_path),
                            "content": content,
                            "code_language": self._detect_language(file_path),
                            "size_bytes": file_data["size"],
                            "line_count": content.count('\n') + 1,
                            "commit_sha": latest_commit_sha,
                            "branch": repo["default_branch"],
                            "last_modified": datetime.utcnow(),
                            "is_deleted": False,
                            "updated_at": datetime.utcnow()
                        }
                        
                        # 添加作者信息
                        if compare_data.get("commits") and len(compare_data["commits"]) > 0:
                            latest_commit = compare_data["commits"][-1]
                            if latest_commit.get("commit") and latest_commit["commit"].get("author"):
                                file_doc["author"] = latest_commit["commit"]["author"].get("name", "unknown")
                        
                        if existing_file:
                            # 保存版本历史
                            version_doc = {
                                "file_id": existing_file["_id"],
                                "commit_sha": repo["last_commit_sha"],
                                "content": existing_file.get("content", ""),
                                "diff": file.get("patch", ""),
                                "author": file_doc.get("author", "unknown"),
                                "commit_message": "",
                                "committed_at": datetime.utcnow(),
                                "created_at": datetime.utcnow()
                            }
                            
                            # 添加提交信息
                            for commit in compare_data.get("commits", []):
                                if commit.get("sha") == latest_commit_sha:
                                    version_doc["commit_message"] = commit.get("commit", {}).get("message", "")
                                    break
                            
                            await mongodb.db.code_file_versions.insert_one(version_doc)
                            
                            # 更新文件
                            await mongodb.db.code_files.update_one(
                                {"_id": existing_file["_id"]},
                                {"$set": file_doc}
                            )
                            files_updated += 1
                        else:
                            # 新文件
                            file_doc["created_at"] = datetime.utcnow()
                            await mongodb.db.code_files.insert_one(file_doc)
                            files_added += 1
                
                # 定期更新同步进度
                if files_processed % 10 == 0:
                    await mongodb.db.sync_history.update_one(
                        {"_id": sync_id},
                        {"$set": {
                            "files_processed": files_processed,
                            "files_added": files_added,
                            "files_updated": files_updated,
                            "files_deleted": files_deleted
                        }}
                    )
            
            # 更新同步记录
            await mongodb.db.sync_history.update_one(
                {"_id": sync_id},
                {"$set": {
                    "files_processed": files_processed,
                    "files_added": files_added,
                    "files_updated": files_updated,
                    "files_deleted": files_deleted,
                    "from_commit": repo["last_commit_sha"],
                    "to_commit": latest_commit_sha
                }}
            )
            
            # 更新仓库信息
            await mongodb.db.repositories.update_one(
                {"_id": repo["_id"]},
                {"$set": {
                    "last_commit_sha": latest_commit_sha
                }}
            )
    
    async def _incremental_sync_gitlab(self, repo: Dict, credential: Dict, token: str, sync_id: ObjectId):
        """GitLab增量同步"""
        base_url = credential.get("base_url", "https://gitlab.com")
        project_id = urllib.parse.quote(repo["full_name"], safe='')
        
        headers = {
            "PRIVATE-TOKEN": token
        }
        
        async with aiohttp.ClientSession() as session:
            # 获取最新commit
            branch_url = f"{base_url}/api/v4/projects/{project_id}/repository/branches/{repo['default_branch']}"
            
            async with session.get(branch_url, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Failed to get branch info: {response.status}")
                
                branch_data = await response.json()
                latest_commit_sha = branch_data["commit"]["id"]
            
            # 如果没有新提交，直接返回
            if latest_commit_sha == repo["last_commit_sha"]:
                await mongodb.db.sync_history.update_one(
                    {"_id": sync_id},
                    {"$set": {
                        "status": "completed",
                        "completed_at": datetime.utcnow(),
                        "files_processed": 0,
                        "from_commit": repo["last_commit_sha"],
                        "to_commit": latest_commit_sha
                    }}
                )
                return
            
            # 获取两个commit之间的差异
            compare_url = f"{base_url}/api/v4/projects/{project_id}/repository/compare?from={repo['last_commit_sha']}&to={latest_commit_sha}"
            
            async with session.get(compare_url, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Failed to get comparison: {response.status}")
                
                compare_data = await response.json()
            
            files_processed = 0
            files_added = 0
            files_updated = 0
            files_deleted = 0
            
            # 处理变更的文件
            for file in compare_data.get("diffs", []):
                files_processed += 1
                file_path = file["new_path"]
                
                # 判断是否为二进制文件，跳过
                if self._is_likely_binary(file_path):
                    continue
                
                # GitLab使用new_path和old_path来标识文件操作
                if file["new_path"] == "/dev/null":  # 文件被删除
                    # 标记文件为删除
                    await mongodb.db.code_files.update_one(
                        {
                            "repository_id": repo["_id"],
                            "file_path": file["old_path"]
                        },
                        {"$set": {"is_deleted": True, "updated_at": datetime.utcnow()}}
                    )
                    files_deleted += 1
                    continue
                
                # 获取文件内容
                encoded_path = urllib.parse.quote(file_path, safe='')
                file_url = f"{base_url}/api/v4/projects/{project_id}/repository/files/{encoded_path}/raw?ref={latest_commit_sha}"
                
                async with session.get(file_url, headers=headers) as file_response:
                    if file_response.status != 200:
                        continue
                    
                    content = await file_response.text()
                    
                    # 检查文件是否已存在
                    existing_file = await mongodb.db.code_files.find_one({
                        "repository_id": repo["_id"],
                        "file_path": file_path
                    })
                    
                    file_doc = {
                        "repository_id": repo["_id"],
                        "file_path": file_path,
                        "file_name": os.path.basename(file_path),
                        "content": content,
                        "code_language": self._detect_language(file_path),
                        "size_bytes": len(content),
                        "line_count": content.count('\n') + 1,
                        "commit_sha": latest_commit_sha,
                        "branch": repo["default_branch"],
                        "last_modified": datetime.utcnow(),
                        "is_deleted": False,
                        "updated_at": datetime.utcnow()
                    }
                    
                    # 添加作者信息
                    if compare_data.get("commits") and len(compare_data["commits"]) > 0:
                        latest_commit = compare_data["commits"][-1]
                        if latest_commit.get("author_name"):
                            file_doc["author"] = latest_commit["author_name"]
                    
                    if existing_file:
                        # 保存版本历史
                        version_doc = {
                            "file_id": existing_file["_id"],
                            "commit_sha": repo["last_commit_sha"],
                            "content": existing_file.get("content", ""),
                            "diff": file.get("diff", ""),
                            "author": file_doc.get("author", "unknown"),
                            "commit_message": "",
                            "committed_at": datetime.utcnow(),
                            "created_at": datetime.utcnow()
                        }
                        
                        # 添加提交信息
                        for commit in compare_data.get("commits", []):
                            if commit.get("id") == latest_commit_sha:
                                version_doc["commit_message"] = commit.get("message", "")
                                break
                        
                        await mongodb.db.code_file_versions.insert_one(version_doc)
                        
                        # 更新文件
                        await mongodb.db.code_files.update_one(
                            {"_id": existing_file["_id"]},
                            {"$set": file_doc}
                        )
                        files_updated += 1
                    else:
                        # 新文件
                        file_doc["created_at"] = datetime.utcnow()
                        await mongodb.db.code_files.insert_one(file_doc)
                        files_added += 1
            
            # 更新同步记录
            await mongodb.db.sync_history.update_one(
                {"_id": sync_id},
                {"$set": {
                    "files_processed": files_processed,
                    "files_added": files_added,
                    "files_updated": files_updated,
                    "files_deleted": files_deleted,
                    "from_commit": repo["last_commit_sha"],
                    "to_commit": latest_commit_sha
                }}
            )
            
            # 更新仓库信息
            await mongodb.db.repositories.update_one(
                {"_id": repo["_id"]},
                {"$set": {
                    "last_commit_sha": latest_commit_sha
                }}
            )
    
    def _detect_language(self, file_path: str) -> Optional[str]:
        """根据文件扩展名检测语言"""
        ext_to_lang = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".go": "go",
            ".rs": "rust",
            ".php": "php",
            ".rb": "ruby",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".sh": "shell",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
            ".xml": "xml",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
            ".sql": "sql",
            ".md": "markdown",
        }
        
        _, ext = os.path.splitext(file_path.lower())
        return ext_to_lang.get(ext)
    
    def _is_likely_binary(self, file_path: str) -> bool:
        """判断文件是否可能是二进制文件"""
        binary_extensions = [
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".ico", ".svg",
            ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
            ".zip", ".rar", ".tar", ".gz", ".7z",
            ".exe", ".dll", ".so", ".dylib", ".class", ".jar", ".war",
            ".mp3", ".mp4", ".avi", ".mov", ".wmv", ".flv"
        ]
        
        _, ext = os.path.splitext(file_path.lower())
        return ext in binary_extensions 