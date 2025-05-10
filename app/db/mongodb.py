from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT
from pymongo.errors import ServerSelectionTimeoutError

from app.core.config import settings

class Database:
    client: AsyncIOMotorClient = None
    db = None
    
    async def connect_to_mongodb(self):
        """建立與MongoDB的連接"""
        try:
            self.client = AsyncIOMotorClient(settings.MONGODB_URL)
            self.db = self.client[settings.MONGODB_DB_NAME]
            # 嘗試與MongoDB通信以確保連接成功
            await self.client.admin.command('ping')
            print("Successfully connected to MongoDB")
            
            # 初始化集合和索引
            await self.init_collections()
            
        except ServerSelectionTimeoutError:
            print("Could not connect to MongoDB")
            raise
    
    async def close_mongodb_connection(self):
        """關閉MongoDB連接"""
        if self.client is not None:
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

# 創建單例數據庫連接
mongodb = Database()
