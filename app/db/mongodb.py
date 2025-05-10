from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT
from pymongo.errors import ServerSelectionTimeoutError
from typing import Optional
import asyncio
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

class Database:
    client: Optional[AsyncIOMotorClient] = None
    db = None
    
    async def connect_to_mongodb(self):
        """建立與MongoDB的連接"""
        logger.info("Connecting to MongoDB...")
        try:
            self.client = AsyncIOMotorClient(settings.MONGODB_URL)
            self.db = self.client[settings.MONGODB_DB_NAME]
            
            # 嘗試與MongoDB通信以確保連接成功
            await self.client.admin.command('ping')
            print("Successfully connected to MongoDB")
            
            # 初始化集合和索引
            await self.init_collections()
            
            logger.info("Connected to MongoDB successfully")
        except ServerSelectionTimeoutError:
            print("Could not connect to MongoDB")
            raise
    
    async def close_mongodb_connection(self):
        """關閉MongoDB連接"""
        if self.client is not None:
            logger.info("Closing MongoDB connection...")
            self.client.close()
            print("MongoDB connection closed")
    
    async def init_collections(self):
        """初始化所有集合和索引"""
        # 初始化用戶集合
        await self.init_users_collection()
        # 初始化專案集合
        await self.init_projects_collection()
        # 初始化任務集合
        await self.init_tasks_collection()
        # 初始化評論集合
        await self.init_comments_collection()
        # 初始化衝刺集合
        await self.init_sprints_collection()
        # 初始化看板集合
        await self.init_boards_collection()
        # 初始化附件集合
        await self.init_attachments_collection()
        # 初始化活動日誌集合
        await self.init_activity_logs_collection()
        # 初始化通知集合
        await self.init_notifications_collection()
        # 初始化關係集合
        await self.init_relationships_collection()
        # 初始化標籤集合
        await self.init_tags_collection()
        # 初始化Git相关集合
        await self.init_git_collections()
        # 初始化代码文件集合
        await self.init_code_collections()
        # 初始化文档集合
        await self.init_doc_collections()
    
    async def init_users_collection(self):
        """初始化用戶集合和索引"""
        users_indexes = [
            IndexModel([("username", ASCENDING)], unique=True),
            IndexModel([("email", ASCENDING)], unique=True, sparse=True)
        ]
        
        await self.db.users.create_indexes(users_indexes)
    
    async def init_projects_collection(self):
        """初始化專案集合和索引"""
        projects_indexes = [
            IndexModel([("name", ASCENDING)]),
            IndexModel([("members", ASCENDING)]),
            IndexModel([("name", TEXT), ("description", TEXT)], name="text_search_index")
        ]
        
        await self.db.projects.create_indexes(projects_indexes)
    
    async def init_tasks_collection(self):
        """初始化任務集合和索引"""
        tasks_indexes = [
            IndexModel([("project_id", ASCENDING)]),
            IndexModel([("sprint_id", ASCENDING)]),
            IndexModel([("assignee_id", ASCENDING)]),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("board_column_id", ASCENDING), ("order_in_column", ASCENDING)]),
            IndexModel([("tags", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
            IndexModel([("updated_at", DESCENDING)]),
            IndexModel([("summary", TEXT), ("description", TEXT)], name="text_search_index")
        ]
        
        await self.db.tasks.create_indexes(tasks_indexes)
    
    async def init_comments_collection(self):
        """初始化評論集合和索引"""
        comments_indexes = [
            IndexModel([("task_id", ASCENDING)]),
            IndexModel([("author_id", ASCENDING)]),
            IndexModel([("created_at", ASCENDING)]),
            IndexModel([("content", TEXT)], name="text_search_index")
        ]
        
        await self.db.comments.create_indexes(comments_indexes)
    
    async def init_sprints_collection(self):
        """初始化衝刺集合和索引"""
        sprints_indexes = [
            IndexModel([("project_id", ASCENDING)]),
            IndexModel([("state", ASCENDING)]),
            IndexModel([("name", TEXT)], name="text_search_index")
        ]
        
        await self.db.sprints.create_indexes(sprints_indexes)
    
    async def init_boards_collection(self):
        """初始化看板集合和索引"""
        boards_indexes = [
            IndexModel([("project_id", ASCENDING)]),
            IndexModel([("name", TEXT)], name="text_search_index")
        ]
        
        await self.db.boards.create_indexes(boards_indexes)
    
    async def init_attachments_collection(self):
        """初始化附件集合和索引"""
        attachments_indexes = [
            IndexModel([("uploaded_by", ASCENDING)]),
            IndexModel([("uploaded_at", DESCENDING)]),
            IndexModel([("attached_to_task", ASCENDING)]),
            IndexModel([("attached_to_comment", ASCENDING)])
        ]
        
        await self.db.attachments.create_indexes(attachments_indexes)
    
    async def init_activity_logs_collection(self):
        """初始化活動日誌集合和索引"""
        activity_logs_indexes = [
            IndexModel([("project_id", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("user_id", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("target_type", ASCENDING), ("target_id", ASCENDING), ("timestamp", DESCENDING)])
        ]
        
        await self.db.activity_logs.create_indexes(activity_logs_indexes)
    
    async def init_notifications_collection(self):
        """初始化通知集合和索引"""
        notifications_indexes = [
            IndexModel([("recipient_id", ASCENDING), ("is_read", ASCENDING), ("created_at", DESCENDING)])
        ]
        
        await self.db.notifications.create_indexes(notifications_indexes)
    
    async def init_relationships_collection(self):
        """初始化關係集合和索引"""
        relationships_indexes = [
            IndexModel([("project_id", ASCENDING)]),
            IndexModel([("source_task_id", ASCENDING)]),
            IndexModel([("target_task_id", ASCENDING)]),
            IndexModel([
                ("source_task_id", ASCENDING), 
                ("target_task_id", ASCENDING), 
                ("type", ASCENDING)
            ], unique=True)
        ]
        
        await self.db.relationships.create_indexes(relationships_indexes)
    
    async def init_tags_collection(self):
        """初始化標籤集合和索引"""
        tags_indexes = [
            IndexModel([("name", ASCENDING)], unique=True),
            IndexModel([("usage_count", DESCENDING)])
        ]
        
        await self.db.tags.create_indexes(tags_indexes)

    async def init_git_collections(self):
        """初始化Git相关集合和索引"""
        # Git凭证索引
        git_credentials_indexes = [
            IndexModel([("name", ASCENDING)]),
            IndexModel([("platform", ASCENDING)]),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("last_validated", DESCENDING)])
        ]
        
        await self.db.git_credentials.create_indexes(git_credentials_indexes)
        
        # 仓库索引
        repositories_indexes = [
            IndexModel([("credential_id", ASCENDING)]),
            IndexModel([("platform", ASCENDING)]),
            IndexModel([("full_name", ASCENDING), ("platform", ASCENDING)], unique=True),
            IndexModel([("sync_status", ASCENDING)]),
            IndexModel([("last_synced_at", DESCENDING)])
        ]
        
        await self.db.repositories.create_indexes(repositories_indexes)
        
        # 同步历史索引
        sync_history_indexes = [
            IndexModel([("repository_id", ASCENDING)]),
            IndexModel([("started_at", DESCENDING)]),
            IndexModel([("status", ASCENDING)])
        ]
        
        await self.db.sync_history.create_indexes(sync_history_indexes)
    
    async def init_code_collections(self):
        """初始化代码文件集合和索引"""
        code_files_indexes = [
            IndexModel([("repository_id", ASCENDING)]),
            IndexModel([("repository_id", ASCENDING), ("file_path", ASCENDING)], unique=True),
            IndexModel([("code_language", ASCENDING)]),
            IndexModel([("is_deleted", ASCENDING)]),
            IndexModel([("content", TEXT)], name="content_text_search")
        ]
        await self.db.code_files.create_indexes(code_files_indexes)
        
        code_file_versions_indexes = [
            IndexModel([("file_id", ASCENDING)]),
            IndexModel([("commit_sha", ASCENDING)]),
            IndexModel([("committed_at", DESCENDING)])
        ]
        await self.db.code_file_versions.create_indexes(code_file_versions_indexes)
    
    async def init_doc_collections(self):
        """初始化文档集合和索引"""
        docs_indexes = [
            IndexModel([("repository_id", ASCENDING)]),
            IndexModel([("title", ASCENDING)]),
            IndexModel([("tags", ASCENDING)]),
            IndexModel([("is_deleted", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
            IndexModel([("updated_at", DESCENDING)]),
            IndexModel([("title", TEXT), ("content", TEXT)], name="doc_text_search")
        ]
        await self.db.project_documentations.create_indexes(docs_indexes)
        
        doc_versions_indexes = [
            IndexModel([("doc_id", ASCENDING)]),
            IndexModel([("version_number", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)])
        ]
        await self.db.documentation_versions.create_indexes(doc_versions_indexes)

    async def _create_indexes(self):
        """创建数据库索引"""
        try:
            # git_credentials 索引
            await self.db.git_credentials.create_index([("name", 1)], unique=True)
            await self.db.git_credentials.create_index([("status", 1)])
            await self.db.git_credentials.create_index([("platform", 1)])
            
            # repositories 索引
            await self.db.repositories.create_index([("full_name", 1), ("platform", 1)], unique=True)
            await self.db.repositories.create_index([("credential_id", 1)])
            await self.db.repositories.create_index([("sync_status", 1)])
            
            # code_files 索引
            await self.db.code_files.create_index([("repository_id", 1), ("file_path", 1)], unique=True)
            await self.db.code_files.create_index([("repository_id", 1), ("is_deleted", 1)])
            
            # sync_history 索引
            await self.db.sync_history.create_index([("repository_id", 1), ("started_at", -1)])
            
            logger.info("MongoDB indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating MongoDB indexes: {e}")
            # 不抛出异常，允许应用继续启动

# 創建單例數據庫連接
mongodb = Database()
