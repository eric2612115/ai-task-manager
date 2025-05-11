from typing import List, Dict, Optional, Union
from datetime import datetime
from bson import ObjectId
import logging

from app.db.mongodb import mongodb

logger = logging.getLogger(__name__)

class DocService:
    async def create_document(self, data: Dict) -> Dict:
        """创建文档"""
        # 验证项目是否存在
        project = await mongodb.db.projects.find_one({"_id": ObjectId(data["project_id"])})
        if not project:
            raise ValueError("Project not found")
        
        # 准备文档数据
        doc_data = {
            "project_id": ObjectId(data["project_id"]),
            "title": data["title"],
            "content": data["content"],
            "path": data.get("path"),
            "tags": data.get("tags", []),
            "author_id": data.get("author_id"),
            "is_deleted": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # 插入文档
        result = await mongodb.db.project_documentations.insert_one(doc_data)
        doc = await mongodb.db.project_documentations.find_one({"_id": result.inserted_id})
        
        # 创建第一个版本
        version_data = {
            "doc_id": doc["_id"],
            "title": doc["title"],
            "content": doc["content"],
            "edited_by": doc.get("author_id"),
            "version_number": 1,
            "created_at": datetime.utcnow()
        }
        
        await mongodb.db.documentation_versions.insert_one(version_data)
        
        return doc
    
    async def get_documents(self, project_id: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[Dict]:
        """获取文档列表"""
        query = {"is_deleted": False}
        
        if project_id:
            query["project_id"] = ObjectId(project_id)
        
        cursor = mongodb.db.project_documentations.find(query).sort("updated_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def get_document(self, doc_id: str) -> Optional[Dict]:
        """获取单个文档"""
        return await mongodb.db.project_documentations.find_one({
            "_id": ObjectId(doc_id),
            "is_deleted": False
        })
    
    async def update_document(self, doc_id: str, data: Dict, user_id: Optional[str] = None) -> Optional[Dict]:
        """更新文档"""
        doc = await self.get_document(doc_id)
        if not doc:
            return None
        
        update_data = {"updated_at": datetime.utcnow()}
        
        # 更新需要保存历史版本的字段
        content_changed = False
        
        if "title" in data:
            update_data["title"] = data["title"]
            content_changed = True
        
        if "content" in data:
            update_data["content"] = data["content"]
            content_changed = True
        
        # 更新其他字段
        if "path" in data:
            update_data["path"] = data["path"]
        
        if "tags" in data:
            update_data["tags"] = data["tags"]
        
        if user_id:
            update_data["last_modified_by"] = ObjectId(user_id)
        
        # 保存新版本
        if content_changed:
            # 获取当前最大版本号
            latest_version = await mongodb.db.documentation_versions.find_one(
                {"doc_id": ObjectId(doc_id)},
                sort=[("version_number", -1)]
            )
            
            new_version_number = 1
            if latest_version:
                new_version_number = latest_version["version_number"] + 1
            
            # 创建新版本
            version_data = {
                "doc_id": ObjectId(doc_id),
                "title": update_data.get("title", doc["title"]),
                "content": update_data.get("content", doc["content"]),
                "edited_by": update_data.get("last_modified_by", doc.get("author_id")),
                "version_number": new_version_number,
                "change_summary": data.get("change_summary"),
                "created_at": datetime.utcnow()
            }
            
            await mongodb.db.documentation_versions.insert_one(version_data)
        
        # 更新文档
        await mongodb.db.project_documentations.update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": update_data}
        )
        
        return await self.get_document(doc_id)
    
    async def delete_document(self, doc_id: str) -> bool:
        """删除文档（软删除）"""
        result = await mongodb.db.project_documentations.update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": {
                "is_deleted": True,
                "updated_at": datetime.utcnow()
            }}
        )
        
        return result.modified_count > 0
    
    async def get_document_versions(self, doc_id: str, skip: int = 0, limit: int = 20) -> List[Dict]:
        """获取文档版本历史"""
        cursor = mongodb.db.documentation_versions.find(
            {"doc_id": ObjectId(doc_id)}
        ).sort("version_number", -1).skip(skip).limit(limit)
        
        return await cursor.to_list(length=limit)
    
    async def get_document_version(self, doc_id: str, version_number: int) -> Optional[Dict]:
        """获取指定版本的文档"""
        return await mongodb.db.documentation_versions.find_one({
            "doc_id": ObjectId(doc_id),
            "version_number": version_number
        })
    
    async def generate_documentation(self, project_id: str, source_files: List[str], title: str, doc_type: str = "technical") -> Dict:
        """生成文档"""
        # 验证项目是否存在
        project = await mongodb.db.projects.find_one({"_id": ObjectId(project_id)})
        if not project:
            raise ValueError("Project not found")
        
        # 获取该项目下的代码文件内容
        file_contents = []
        for file_path in source_files:
            # 在该项目的所有仓库中查找文件
            repos = await mongodb.db.repositories.find({"project_id": ObjectId(project_id)}).to_list(None)
            repo_ids = [repo["_id"] for repo in repos]
            
            if not repo_ids:
                logger.warning(f"No repositories found for project {project_id}")
                continue
                
            for repo_id in repo_ids:
                file = await mongodb.db.code_files.find_one({
                    "repository_id": repo_id,
                    "file_path": file_path,
                    "is_deleted": False
                })
                
                if file:
                    file_contents.append({
                        "path": file["file_path"],
                        "language": file.get("code_language"),
                        "content": file["content"]
                    })
                    break  # 找到文件后停止遍历其他仓库
        
        # 生成文档内容
        content = self._generate_content(file_contents, doc_type)
        
        # 创建文档
        doc_data = {
            "project_id": ObjectId(project_id),
            "title": title,
            "content": content,
            "path": None,
            "tags": ["auto-generated", doc_type],
            "is_deleted": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await mongodb.db.project_documentations.insert_one(doc_data)
        doc = await mongodb.db.project_documentations.find_one({"_id": result.inserted_id})
        
        # 创建版本
        version_data = {
            "doc_id": doc["_id"],
            "title": doc["title"],
            "content": doc["content"],
            "version_number": 1,
            "change_summary": "Auto-generated documentation",
            "created_at": datetime.utcnow()
        }
        
        await mongodb.db.documentation_versions.insert_one(version_data)
        
        return doc
    
    def _generate_content(self, files: List[Dict], doc_type: str) -> str:
        """生成文档内容
        
        注意：这是一个基础实现，实际项目中可以替换为更智能的文档生成方式
        """
        content = "# Generated Documentation\n\n"
        
        for file in files:
            content += f"## {file['path']}\n\n"
            
            if file.get("language"):
                content += f"**Language**: {file['language']}\n\n"
            
            # 添加代码块
            content += "```\n"
            content += file["content"]
            content += "\n```\n\n"
        
        return content 