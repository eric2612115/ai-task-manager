import os
from typing import List, Dict, Optional, Union, Any
from datetime import datetime
from bson import ObjectId
import logging

from app.db.mongodb import mongodb

logger = logging.getLogger(__name__)

class CodeService:
    async def get_file_tree(self, repo_id: str, include_deleted: bool = False) -> List[Dict]:
        """获取仓库文件树结构"""
        query = {"repository_id": ObjectId(repo_id)}
        
        if not include_deleted:
            query["is_deleted"] = False
        
        files = await mongodb.db.code_files.find(
            query,
            {"file_path": 1, "file_name": 1, "code_language": 1, "size_bytes": 1, "is_deleted": 1}
        ).to_list(length=10000)
        
        # 构建树结构
        tree = []
        paths = {}
        
        for file in files:
            file_path = file["file_path"]
            path_parts = file_path.split("/")
            file_name = path_parts[-1]
            
            current_path = ""
            current_tree = tree
            
            # 处理目录结构
            for i, part in enumerate(path_parts[:-1]):
                current_path = f"{current_path}/{part}" if current_path else part
                
                if current_path not in paths:
                    # 创建新目录节点
                    new_dir = {
                        "name": part,
                        "path": current_path,
                        "type": "directory",
                        "children": []
                    }
                    current_tree.append(new_dir)
                    paths[current_path] = new_dir
                    current_tree = new_dir["children"]
                else:
                    # 使用现有目录节点
                    current_tree = paths[current_path]["children"]
            
            # 添加文件节点
            file_node = {
                "id": str(file["_id"]),
                "name": file_name,
                "path": file_path,
                "type": "file",
                "language": file.get("code_language"),
                "size": file.get("size_bytes", 0),
                "is_deleted": file.get("is_deleted", False)
            }
            
            current_tree.append(file_node)
        
        return self._sort_tree(tree)
    
    def _sort_tree(self, tree: List[Dict]) -> List[Dict]:
        """递归排序树结构"""
        # 目录在前，文件在后
        dirs = [item for item in tree if item["type"] == "directory"]
        files = [item for item in tree if item["type"] == "file"]
        
        # 按名称排序
        dirs.sort(key=lambda x: x["name"].lower())
        files.sort(key=lambda x: x["name"].lower())
        
        # 递归排序子目录
        for dir_item in dirs:
            if "children" in dir_item:
                dir_item["children"] = self._sort_tree(dir_item["children"])
        
        return dirs + files
    
    async def get_file(self, file_id: str) -> Optional[Dict]:
        """获取文件内容"""
        file = await mongodb.db.code_files.find_one({"_id": ObjectId(file_id)})
        
        if not file:
            return None
        
        return file
    
    async def get_file_by_path(self, repo_id: str, file_path: str) -> Optional[Dict]:
        """根据路径获取文件"""
        return await mongodb.db.code_files.find_one({
            "repository_id": ObjectId(repo_id),
            "file_path": file_path,
            "is_deleted": False
        })
    
    async def get_file_versions(self, file_id: str, skip: int = 0, limit: int = 10) -> List[Dict]:
        """获取文件版本历史"""
        versions = await mongodb.db.code_file_versions.find(
            {"file_id": ObjectId(file_id)}
        ).sort("committed_at", -1).skip(skip).limit(limit).to_list(length=limit)
        
        return versions
    
    async def search_code(self, repo_id: str, query: str, file_extensions: Optional[List[str]] = None, limit: int = 50) -> List[Dict]:
        """搜索代码内容"""
        search_query = {
            "repository_id": ObjectId(repo_id),
            "is_deleted": False,
            "$text": {"$search": query}
        }
        
        # 按文件扩展名过滤
        if file_extensions and len(file_extensions) > 0:
            extension_filters = []
            for ext in file_extensions:
                extension_filters.append({"file_path": {"$regex": f"{ext}$"}})
            
            if extension_filters:
                search_query["$or"] = extension_filters
        
        # 执行搜索
        results = await mongodb.db.code_files.find(
            search_query,
            {
                "file_path": 1,
                "file_name": 1,
                "code_language": 1,
                "content": 1,
                "score": {"$meta": "textScore"}
            }
        ).sort([("score", {"$meta": "textScore"})]).limit(limit).to_list(length=limit)
        
        # 处理搜索结果，包括匹配上下文
        processed_results = []
        
        for result in results:
            # 查找匹配行及其上下文
            match_context = self._extract_context(result["content"], query, context_lines=2)
            
            processed_results.append({
                "id": str(result["_id"]),
                "file_path": result["file_path"],
                "file_name": result["file_name"],
                "language": result.get("code_language"),
                "matches": match_context,
                "score": result.get("score", 0)
            })
        
        return processed_results
    
    def _extract_context(self, content: str, query: str, context_lines: int = 2) -> List[Dict]:
        """提取查询匹配的上下文行"""
        if not content or not query:
            return []
        
        matches = []
        lines = content.split("\n")
        
        # 转换为小写进行不区分大小写的匹配
        query_lower = query.lower()
        
        for i, line in enumerate(lines):
            if query_lower in line.lower():
                # 计算上下文行范围
                start_line = max(0, i - context_lines)
                end_line = min(len(lines) - 1, i + context_lines)
                
                # 提取上下文
                context = []
                for j in range(start_line, end_line + 1):
                    context.append({
                        "line_number": j + 1,  # 1-indexed
                        "content": lines[j],
                        "is_match": j == i
                    })
                
                matches.append({
                    "start_line": start_line + 1,  # 1-indexed
                    "end_line": end_line + 1,
                    "match_line": i + 1,
                    "context": context
                })
        
        return matches 