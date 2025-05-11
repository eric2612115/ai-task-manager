import aiohttp
import base64
import urllib.parse
from typing import List, Dict, Optional, Union
from datetime import datetime
from cryptography.fernet import Fernet
from bson import ObjectId
import logging

from app.core.config import settings
from app.db.mongodb import mongodb

logger = logging.getLogger(__name__)

class GitService:
    def __init__(self):
        # 使用settings中的密钥进行加密
        self.cipher = Fernet(settings.ENCRYPTION_KEY.encode())
    
    def encrypt_token(self, token: str) -> str:
        """加密Git token"""
        return self.cipher.encrypt(token.encode()).decode()
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """解密Git token"""
        return self.cipher.decrypt(encrypted_token.encode()).decode()
    
    async def create_credential(self, data: Dict) -> Dict:
        """创建Git凭证"""
        # 加密token
        data["token"] = self.encrypt_token(data["token"])
        data["created_at"] = datetime.utcnow()
        data["updated_at"] = datetime.utcnow()
        
        result = await mongodb.db.git_credentials.insert_one(data)
        return await mongodb.db.git_credentials.find_one({"_id": result.inserted_id})
    
    async def get_credentials(self, skip: int = 0, limit: int = 100) -> List[Dict]:
        """获取所有Git凭证"""
        cursor = mongodb.db.git_credentials.find().skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def get_credential(self, credential_id: str) -> Optional[Dict]:
        """获取单个Git凭证"""
        return await mongodb.db.git_credentials.find_one({"_id": ObjectId(credential_id)})
    
    async def update_credential(self, credential_id: str, data: Dict) -> Optional[Dict]:
        """更新Git凭证"""
        credential = await self.get_credential(credential_id)
        if not credential:
            return None
        
        update_data = {"updated_at": datetime.utcnow()}
        
        if "name" in data:
            update_data["name"] = data["name"]
        
        if "base_url" in data:
            update_data["base_url"] = data["base_url"]
        
        if "token" in data:
            update_data["token"] = self.encrypt_token(data["token"])
            update_data["status"] = "active"  # 更新token后重置状态
            update_data["last_validated"] = None  # 清除上次验证时间
        
        if "status" in data:
            update_data["status"] = data["status"]
        
        await mongodb.db.git_credentials.update_one(
            {"_id": ObjectId(credential_id)},
            {"$set": update_data}
        )
        
        return await self.get_credential(credential_id)
    
    async def delete_credential(self, credential_id: str) -> bool:
        """删除Git凭证"""
        # 检查是否有仓库使用此凭证
        repos_count = await mongodb.db.repositories.count_documents({"credential_id": ObjectId(credential_id)})
        if repos_count > 0:
            raise ValueError(f"Cannot delete credential with {repos_count} associated repositories")
        
        result = await mongodb.db.git_credentials.delete_one({"_id": ObjectId(credential_id)})
        return result.deleted_count > 0
    
    async def test_connection(self, credential_id: str) -> bool:
        """测试Git连接"""
        credential = await self.get_credential(credential_id)
        if not credential:
            raise ValueError("Credential not found")
        
        token = self.decrypt_token(credential["token"])
        success = False
        
        try:
            if credential["platform"] == "github":
                success = await self._test_github_connection(token)
            elif credential["platform"] == "gitlab":
                success = await self._test_gitlab_connection(token, credential.get("base_url"))
            
            # 更新凭证状态
            status = "active" if success else "invalid"
            await mongodb.db.git_credentials.update_one(
                {"_id": ObjectId(credential_id)},
                {"$set": {
                    "status": status,
                    "last_validated": datetime.utcnow()
                }}
            )
            
            return success
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            
            # 更新凭证状态为无效
            await mongodb.db.git_credentials.update_one(
                {"_id": ObjectId(credential_id)},
                {"$set": {
                    "status": "invalid",
                    "last_validated": datetime.utcnow()
                }}
            )
            
            return False
    
    async def _test_github_connection(self, token: str) -> bool:
        """测试GitHub连接"""
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.github.com/user", headers=headers) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"GitHub connection test failed: {str(e)}")
            return False
    
    async def _test_gitlab_connection(self, token: str, base_url: Optional[str] = None) -> bool:
        """测试GitLab连接"""
        url = f"{base_url or 'https://gitlab.com'}/api/v4/user"
        headers = {
            "PRIVATE-TOKEN": token
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"GitLab connection test failed: {str(e)}")
            return False
    
    async def test_token_directly(self, platform: str, token: str, base_url: Optional[str] = None) -> Dict:
        """直接测试Git token有效性，无需先保存凭证"""
        success = False
        message = ""
        user_info = {}
        
        try:
            if platform == "github":
                success, user_info = await self._test_github_token_details(token)
            elif platform == "gitlab":
                success, user_info = await self._test_gitlab_token_details(token, base_url)
            else:
                message = f"Unsupported platform: {platform}"
            
            if success:
                message = "Connection successful"
            else:
                message = "Invalid token or API access denied"
                
            return {
                "valid": success,
                "message": message,
                "user_info": user_info
            }
        except Exception as e:
            logger.error(f"Token test failed: {str(e)}")
            return {
                "valid": False,
                "message": f"Connection error: {str(e)}",
                "user_info": {}
            }
    
    async def _test_github_token_details(self, token: str) -> tuple[bool, Dict]:
        """测试GitHub token并返回用户信息"""
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.github.com/user", headers=headers) as response:
                    if response.status == 200:
                        user_data = await response.json()
                        return True, {
                            "username": user_data.get("login"),
                            "name": user_data.get("name"),
                            "email": user_data.get("email"),
                            "avatar_url": user_data.get("avatar_url")
                        }
                    return False, {}
        except Exception as e:
            logger.error(f"GitHub token test failed: {str(e)}")
            return False, {}
    
    async def _test_gitlab_token_details(self, token: str, base_url: Optional[str] = None) -> tuple[bool, Dict]:
        """测试GitLab token并返回用户信息"""
        url = f"{base_url or 'https://gitlab.com'}/api/v4/user"
        headers = {
            "PRIVATE-TOKEN": token
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        user_data = await response.json()
                        return True, {
                            "username": user_data.get("username"),
                            "name": user_data.get("name"),
                            "email": user_data.get("email"),
                            "avatar_url": user_data.get("avatar_url")
                        }
                    return False, {}
        except Exception as e:
            logger.error(f"GitLab token test failed: {str(e)}")
            return False, {}
    
    async def discover_repositories(self, credential_id: str) -> List[Dict]:
        """发现可访问的仓库"""
        credential = await self.get_credential(credential_id)
        if not credential:
            raise ValueError("Credential not found")
        
        token = self.decrypt_token(credential["token"])
        
        if credential["platform"] == "github":
            repos = await self._discover_github_repos(token)
        elif credential["platform"] == "gitlab":
            repos = await self._discover_gitlab_repos(token, credential.get("base_url"))
        else:
            repos = []
        
        # 更新凭证状态
        await mongodb.db.git_credentials.update_one(
            {"_id": ObjectId(credential_id)},
            {"$set": {
                "status": "active",
                "last_validated": datetime.utcnow()
            }}
        )
        
        # 标记现有仓库
        for repo in repos:
            query = {
                "full_name": repo["full_name"],
                "platform": repo["platform"]
            }
            
            # 如果请求中包含project_id，将其添加到查询条件中
            if "project_id" in repo:
                query["project_id"] = ObjectId(repo["project_id"])
                
            existing = await mongodb.db.repositories.find_one(query)
            
            if existing:
                repo["exists"] = True
                repo["id"] = str(existing["_id"])
            else:
                repo["exists"] = False
        
        return repos
    
    async def _discover_github_repos(self, token: str) -> List[Dict]:
        """发现GitHub仓库"""
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        repos = []
        page = 1
        
        try:
            async with aiohttp.ClientSession() as session:
                while True:
                    async with session.get(
                        f"https://api.github.com/user/repos?page={page}&per_page=100",
                        headers=headers
                    ) as response:
                        if response.status != 200:
                            break
                        
                        data = await response.json()
                        if not data:
                            break
                        
                        for repo in data:
                            repos.append({
                                "platform": "github",
                                "owner": repo["owner"]["login"],
                                "name": repo["name"],
                                "full_name": repo["full_name"],
                                "default_branch": repo.get("default_branch", "main"),
                                "description": repo.get("description"),
                                "is_private": repo.get("private", False)
                            })
                        
                        page += 1
                        
                        # 限制最多获取500个仓库
                        if len(repos) >= 500 or len(data) < 100:
                            break
        except Exception as e:
            logger.error(f"GitHub repository discovery failed: {str(e)}")
        
        return repos
    
    async def _discover_gitlab_repos(self, token: str, base_url: Optional[str] = None) -> List[Dict]:
        """发现GitLab仓库"""
        base_url = base_url or "https://gitlab.com"
        url = f"{base_url}/api/v4/projects?membership=true&per_page=100"
        headers = {
            "PRIVATE-TOKEN": token
        }
        
        repos = []
        page = 1
        
        try:
            async with aiohttp.ClientSession() as session:
                while True:
                    async with session.get(
                        f"{url}&page={page}",
                        headers=headers
                    ) as response:
                        if response.status != 200:
                            break
                        
                        data = await response.json()
                        if not data:
                            break
                        
                        for repo in data:
                            # GitLab的full_name是path_with_namespace
                            repos.append({
                                "platform": "gitlab",
                                "owner": repo.get("namespace", {}).get("path", ""),
                                "name": repo.get("name", ""),
                                "full_name": repo.get("path_with_namespace", ""),
                                "default_branch": repo.get("default_branch", "main"),
                                "description": repo.get("description"),
                                "is_private": not repo.get("public", True)
                            })
                        
                        page += 1
                        
                        # 限制最多获取500个仓库
                        if len(repos) >= 500 or len(data) < 100:
                            break
        except Exception as e:
            logger.error(f"GitLab repository discovery failed: {str(e)}")
        
        return repos
    
    async def create_repository(self, data: Dict) -> Dict:
        """创建仓库记录"""
        # 先检查凭证是否存在
        credential = await self.get_credential(str(data["credential_id"]))
        if not credential:
            raise ValueError("Credential not found")
        
        # 检查是否已存在
        query = {
            "full_name": data["full_name"],
            "platform": data["platform"]
        }
        
        # 如果提供了project_id，则加入查询条件
        if "project_id" in data and data["project_id"] is not None:
            query["project_id"] = ObjectId(data["project_id"])
        
        existing = await mongodb.db.repositories.find_one(query)
        
        if existing:
            raise ValueError(f"Repository {data['full_name']} already exists")
        
        # 准备数据
        repo_data = {
            "credential_id": ObjectId(data["credential_id"]),
            "platform": data["platform"],
            "owner": data["owner"],
            "name": data["name"],
            "full_name": data["full_name"],
            "default_branch": data.get("default_branch", "main"),
            "description": data.get("description"),
            "is_private": data.get("is_private", False),
            "sync_enabled": data.get("sync_enabled", True),
            "sync_branches": data.get("sync_branches", ["main", "master", "develop"]),
            "sync_status": "pending",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # 添加project_id（如果存在）
        if "project_id" in data and data["project_id"] is not None:
            repo_data["project_id"] = ObjectId(data["project_id"])
        
        result = await mongodb.db.repositories.insert_one(repo_data)
        return await mongodb.db.repositories.find_one({"_id": result.inserted_id})
    
    async def get_repositories(self, skip: int = 0, limit: int = 100, project_id: Optional[str] = None) -> List[Dict]:
        """获取所有仓库，可选按项目ID过滤"""
        # 构建查询条件
        query = {}
        if project_id:
            query["project_id"] = ObjectId(project_id)
            
        cursor = mongodb.db.repositories.find(query).skip(skip).limit(limit)
        repos = await cursor.to_list(length=limit)
        
        # 添加凭证信息
        for repo in repos:
            if "credential_id" in repo:
                credential = await mongodb.db.git_credentials.find_one(
                    {"_id": repo["credential_id"]},
                    {"name": 1, "platform": 1, "status": 1}
                )
                if credential:
                    repo["credential"] = {
                        "id": str(credential["_id"]),
                        "name": credential["name"],
                        "platform": credential["platform"],
                        "status": credential["status"]
                    }
        
        return repos
    
    async def get_repository(self, repo_id: str) -> Optional[Dict]:
        """获取单个仓库"""
        repo = await mongodb.db.repositories.find_one({"_id": ObjectId(repo_id)})
        
        if not repo:
            return None
        
        # 添加凭证信息
        if "credential_id" in repo:
            credential = await mongodb.db.git_credentials.find_one(
                {"_id": repo["credential_id"]},
                {"name": 1, "platform": 1, "status": 1}
            )
            if credential:
                repo["credential"] = {
                    "id": str(credential["_id"]),
                    "name": credential["name"],
                    "platform": credential["platform"],
                    "status": credential["status"]
                }
        
        return repo
    
    async def update_repository(self, repo_id: str, data: Dict) -> Optional[Dict]:
        """更新仓库"""
        repo = await self.get_repository(repo_id)
        if not repo:
            return None
        
        update_data = {"updated_at": datetime.utcnow()}
        
        # 更新字段
        for field in ["default_branch", "sync_enabled", "sync_branches", "description"]:
            if field in data:
                update_data[field] = data[field]
        
        await mongodb.db.repositories.update_one(
            {"_id": ObjectId(repo_id)},
            {"$set": update_data}
        )
        
        return await self.get_repository(repo_id)
    
    async def delete_repository(self, repo_id: str) -> bool:
        """删除仓库"""
        # 先删除相关文件和同步历史
        await mongodb.db.code_files.delete_many({"repository_id": ObjectId(repo_id)})
        await mongodb.db.code_file_versions.delete_many({"file_id": {"$in": await self._get_file_ids(repo_id)}})
        await mongodb.db.sync_history.delete_many({"repository_id": ObjectId(repo_id)})
        
        # 删除仓库文档
        result = await mongodb.db.repositories.delete_one({"_id": ObjectId(repo_id)})
        return result.deleted_count > 0
    
    async def _get_file_ids(self, repo_id: str) -> List[ObjectId]:
        """获取仓库下所有文件ID"""
        cursor = mongodb.db.code_files.find(
            {"repository_id": ObjectId(repo_id)},
            {"_id": 1}
        )
        files = await cursor.to_list(length=10000)
        return [file["_id"] for file in files] 