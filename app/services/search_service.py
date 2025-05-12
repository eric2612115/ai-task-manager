from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId

from app.db.mongodb import mongodb
from app.models.other_models import SearchResult

class SearchService:
    def __init__(self):
        self.search_handlers = {
            'project': self.search_projects,
            'task': self.search_tasks,
            'comment': self.search_comments,
            'sprint': self.search_sprints,
            'board': self.search_boards,
            'tag': self.search_tags
        }
    
    async def search(self, query: str, target_types: List[str], project_id: Optional[str] = None, skip: int = 0, limit: int = 50) -> List[SearchResult]:
        """统一的搜索入口"""
        results = []
        for target_type in target_types:
            if handler := self.search_handlers.get(target_type):
                type_results = await handler(query, project_id, skip, limit)
                results.extend(type_results)
        
        # 按相关度排序
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    async def search_projects(self, q: str, project_id: Optional[str], skip: int, limit: int) -> List[SearchResult]:
        """搜索项目"""
        search_query = {
            "$or": [
                {"$text": {"$search": q}},
                {"name": {"$regex": q, "$options": "i"}},
                {"description": {"$regex": q, "$options": "i"}}
            ]
        }
        
        if project_id:
            search_query["_id"] = ObjectId(project_id)
        
        pipeline = [
            {"$match": search_query},
            {"$project": {
                "score": {"$meta": "textScore"},
                "name": 1,
                "description": 1,
                "methodology": 1,
                "created_at": 1,
                "updated_at": 1
            }},
            {"$sort": {"score": -1}},
            {"$skip": skip},
            {"$limit": limit}
        ]
        
        cursor = mongodb.db.projects.aggregate(pipeline)
        results = []
        
        async for doc in cursor:
            highlight = doc.get("name", "")
            if len(highlight) > 100:
                highlight = highlight[:97] + "..."
            
            results.append(SearchResult(
                type="project",
                id=str(doc["_id"]),
                score=doc["score"],
                highlight=highlight,
                data={
                    "name": doc.get("name"),
                    "description": doc.get("description"),
                    "methodology": doc.get("methodology")
                },
                navigation={
                    "detail": f"/projects/{doc['_id']}",
                    "tasks": f"/projects/{doc['_id']}/tasks",
                    "boards": f"/projects/{doc['_id']}/boards",
                    "sprints": f"/projects/{doc['_id']}/sprints"
                },
                metadata={
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at")
                }
            ))
        
        return results

    async def search_tasks(self, q: str, project_id: Optional[str], skip: int, limit: int) -> List[SearchResult]:
        """搜索任务"""
        search_query = {
            "$or": [
                {"summary": {"$regex": q, "$options": "i"}},
                {"description": {"$regex": q, "$options": "i"}},
                {"status": {"$regex": q, "$options": "i"}},
                {"mermaid_syntax": {"$regex": q, "$options": "i"}}
            ]
        }
        
        # 对于标签，我们需要特殊处理
        # 如果标签是数组，我们需要检查数组中的每个元素
        tag_query = {"tags": {"$regex": q, "$options": "i"}}
        search_query["$or"].append(tag_query)
        
        print(f"Service search_tasks - query: {q}, project_id: {project_id}")
        print(f"Service search_tasks - search_query: {search_query}")
        
        if project_id:
            search_query["project_id"] = ObjectId(project_id)
        
        # 执行查询
        cursor = mongodb.db.tasks.find(
            search_query,
            {
                "summary": 1,
                "description": 1,
                "status": 1,
                "priority": 1,
                "project_id": 1,
                "sprint_id": 1,
                "board_column_id": 1,
                "tags": 1,
                "assignee_id": 1,
                "reporter_id": 1,
                "created_at": 1,
                "updated_at": 1
            }
        ).sort([("updated_at", -1)]).skip(skip).limit(limit)
        
        results = []
        
        count = 0
        async for doc in cursor:
            count += 1
            highlight = doc.get("summary", "")
            if len(highlight) > 100:
                highlight = highlight[:97] + "..."
            
            # 计算简单的相关性分数
            # 如果查询词出现在摘要中，给予较高的分数
            score = 0.5  # 基础分数
            if q.lower() in doc.get("summary", "").lower():
                score += 0.3
            if doc.get("tags") and any(q.lower() in tag.lower() for tag in doc.get("tags", [])):
                score += 0.2
            
            # 获取项目信息
            project = await mongodb.db.projects.find_one(
                {"_id": doc["project_id"]},
                {"name": 1}
            )
            
            # 获取指派人信息
            assignee = None
            if doc.get("assignee_id"):
                assignee = await mongodb.db.users.find_one(
                    {"_id": doc["assignee_id"]},
                    {"username": 1, "full_name": 1}
                )
            
            results.append(SearchResult(
                type="task",
                id=str(doc["_id"]),
                score=score,
                highlight=highlight,
                data={
                    "summary": doc.get("summary"),
                    "status": doc.get("status"),
                    "priority": doc.get("priority"),
                    "project_id": str(doc["project_id"]),
                    "project_name": project.get("name") if project else None,
                    "sprint_id": str(doc["sprint_id"]) if doc.get("sprint_id") else None,
                    "board_column_id": str(doc["board_column_id"]) if doc.get("board_column_id") else None,
                    "tags": doc.get("tags", []),
                    "assignee": {
                        "id": str(assignee["_id"]),
                        "username": assignee.get("username"),
                        "full_name": assignee.get("full_name")
                    } if assignee else None
                },
                navigation={
                    "detail": f"/projects/{doc['project_id']}/tasks/{doc['_id']}",
                    "project": f"/projects/{doc['project_id']}",
                    "sprint": f"/projects/{doc['project_id']}/sprints/{doc['sprint_id']}" if doc.get("sprint_id") else None,
                    "board": f"/projects/{doc['project_id']}/boards" if doc.get("board_column_id") else None
                },
                metadata={
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at")
                }
            ))
        
        print(f"Service search_tasks - Found {count} tasks matching query: {q}")
        return results

    async def search_comments(self, q: str, project_id: Optional[str], skip: int, limit: int) -> List[SearchResult]:
        """搜索评论"""
        search_query = {
            "$or": [
                {"$text": {"$search": q}},
                {"content": {"$regex": q, "$options": "i"}}
            ]
        }
        
        if project_id:
            task_ids = [
                task["_id"] async for task in mongodb.db.tasks.find(
                    {"project_id": ObjectId(project_id)},
                    {"_id": 1}
                )
            ]
            if task_ids:
                search_query["task_id"] = {"$in": task_ids}
            else:
                return []
        
        pipeline = [
            {"$match": search_query},
            {"$project": {
                "score": {"$meta": "textScore"},
                "content": 1,
                "task_id": 1,
                "author_id": 1,
                "created_at": 1,
                "updated_at": 1
            }},
            {"$sort": {"score": -1}},
            {"$skip": skip},
            {"$limit": limit}
        ]
        
        cursor = mongodb.db.comments.aggregate(pipeline)
        results = []
        
        async for doc in cursor:
            # 获取任务信息
            task = await mongodb.db.tasks.find_one(
                {"_id": doc["task_id"]},
                {"summary": 1, "project_id": 1}
            )
            
            if not task:
                continue
            
            # 获取作者信息
            author = await mongodb.db.users.find_one(
                {"_id": doc["author_id"]},
                {"username": 1, "full_name": 1}
            )
            
            # 提取纯文本内容作为高亮
            import re
            content_text = re.sub(r'<[^>]+>', '', doc.get("content", ""))
            highlight = content_text[:100] + "..." if len(content_text) > 100 else content_text
            
            results.append(SearchResult(
                type="comment",
                id=str(doc["_id"]),
                score=doc["score"],
                highlight=highlight,
                data={
                    "content": doc.get("content"),
                    "task_id": str(doc["task_id"]),
                    "task_summary": task.get("summary"),
                    "project_id": str(task["project_id"]),
                    "author": {
                        "id": str(author["_id"]),
                        "username": author.get("username"),
                        "full_name": author.get("full_name")
                    } if author else None
                },
                navigation={
                    "detail": f"/projects/{task['project_id']}/tasks/{doc['task_id']}#comment-{doc['_id']}",
                    "task": f"/projects/{task['project_id']}/tasks/{doc['task_id']}",
                    "project": f"/projects/{task['project_id']}"
                },
                metadata={
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at")
                }
            ))
        
        return results

    async def search_sprints(self, q: str, project_id: Optional[str], skip: int, limit: int) -> List[SearchResult]:
        """搜索冲刺"""
        search_query = {
            "$or": [
                {"$text": {"$search": q}},
                {"name": {"$regex": q, "$options": "i"}},
                {"state": {"$regex": q, "$options": "i"}}
            ]
        }
        
        if project_id:
            search_query["project_id"] = ObjectId(project_id)
        
        pipeline = [
            {"$match": search_query},
            {"$project": {
                "score": {"$meta": "textScore"},
                "name": 1,
                "state": 1,
                "project_id": 1,
                "start_date": 1,
                "end_date": 1,
                "created_at": 1,
                "updated_at": 1
            }},
            {"$sort": {"score": -1}},
            {"$skip": skip},
            {"$limit": limit}
        ]
        
        cursor = mongodb.db.sprints.aggregate(pipeline)
        results = []
        
        async for doc in cursor:
            results.append(SearchResult(
                type="sprint",
                id=str(doc["_id"]),
                score=doc["score"],
                highlight=doc.get("name", ""),
                data={
                    "name": doc.get("name"),
                    "state": doc.get("state"),
                    "project_id": str(doc["project_id"]),
                    "start_date": doc.get("start_date"),
                    "end_date": doc.get("end_date")
                },
                navigation={
                    "detail": f"/projects/{doc['project_id']}/sprints/{doc['_id']}",
                    "project": f"/projects/{doc['project_id']}",
                    "tasks": f"/projects/{doc['project_id']}/sprints/{doc['_id']}/tasks"
                },
                metadata={
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at")
                }
            ))
        
        return results

    async def search_boards(self, q: str, project_id: Optional[str], skip: int, limit: int) -> List[SearchResult]:
        """搜索看板"""
        search_query = {
            "$or": [
                {"$text": {"$search": q}},
                {"name": {"$regex": q, "$options": "i"}},
                {"type": {"$regex": q, "$options": "i"}}
            ]
        }
        
        if project_id:
            search_query["project_id"] = ObjectId(project_id)
        
        pipeline = [
            {"$match": search_query},
            {"$project": {
                "score": {"$meta": "textScore"},
                "name": 1,
                "type": 1,
                "project_id": 1,
                "created_at": 1,
                "updated_at": 1
            }},
            {"$sort": {"score": -1}},
            {"$skip": skip},
            {"$limit": limit}
        ]
        
        cursor = mongodb.db.boards.aggregate(pipeline)
        results = []
        
        async for doc in cursor:
            results.append(SearchResult(
                type="board",
                id=str(doc["_id"]),
                score=doc["score"],
                highlight=doc.get("name", ""),
                data={
                    "name": doc.get("name"),
                    "type": doc.get("type"),
                    "project_id": str(doc["project_id"])
                },
                navigation={
                    "detail": f"/projects/{doc['project_id']}/boards/{doc['_id']}",
                    "project": f"/projects/{doc['project_id']}"
                },
                metadata={
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at")
                }
            ))
        
        return results

    async def search_tags(self, q: str, project_id: Optional[str], skip: int, limit: int) -> List[SearchResult]:
        """搜索标签"""
        search_query = {"name": {"$regex": f"^{q}", "$options": "i"}}
        
        cursor = mongodb.db.tags.find(search_query).sort([("usage_count", -1)]).skip(skip).limit(limit)
        results = []
        
        async for doc in cursor:
            score = min(doc.get("usage_count", 0) / 100.0, 1.0)
            
            results.append(SearchResult(
                type="tag",
                id=str(doc["_id"]),
                score=score,
                highlight=doc.get("name", ""),
                data={
                    "name": doc.get("name"),
                    "usage_count": doc.get("usage_count", 0)
                },
                navigation={
                    "detail": f"/tags/{doc['_id']}",
                    "tasks": f"/tags/{doc['_id']}/tasks"
                },
                metadata={
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at")
                }
            ))
        
        return results 