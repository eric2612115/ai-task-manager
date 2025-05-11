from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT
from pymongo.errors import ServerSelectionTimeoutError
from typing import Optional
import asyncio
import logging
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)

class Database:
    client: Optional["AsyncIOMotorClient"] = None
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
        # 初始化会话集合
        await self.init_conversation_collections()
        # 初始化RAG嵌入状态集合
        await self.init_embedding_collections()
    
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

    async def init_conversation_collections(self):
        """初始化对话会话相关集合和索引"""
        # 会话集合
        conversations_indexes = [
            IndexModel([("user_id", ASCENDING)]),
            IndexModel([("project_id", ASCENDING)]),
            IndexModel([("repo_id", ASCENDING)]),
            IndexModel([("is_pinned", DESCENDING)]),
            IndexModel([("last_message_at", DESCENDING)]),
            IndexModel([("title", TEXT)], name="conversation_text_search")
        ]
        await self.db.conversations.create_indexes(conversations_indexes)
        
        # 消息集合
        messages_indexes = [
            IndexModel([("conversation_id", ASCENDING)]),
            IndexModel([("user_id", ASCENDING)]),
            IndexModel([("role", ASCENDING)]),
            IndexModel([("type", ASCENDING)]),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("created_at", ASCENDING)]),
            IndexModel([("content", TEXT)], name="message_text_search")
        ]
        await self.db.messages.create_indexes(messages_indexes)
        
        # 连接状态集合
        connection_states_indexes = [
            IndexModel([("connection_id", ASCENDING)], unique=True),
            IndexModel([("user_id", ASCENDING)]),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("last_ping", DESCENDING)]),
            IndexModel([("client_info.reconnect_token", ASCENDING)]),
            IndexModel([("active_conversation_id", ASCENDING)])
        ]
        await self.db.connection_states.create_indexes(connection_states_indexes)
    
    async def init_embedding_collections(self):
        """初始化RAG嵌入状态集合"""
        try:
            # 获取现有索引信息
            existing_indexes = await self.db.embedding_status.index_information()
            
            # 确保embedding_history集合存在
            if "embedding_history" not in await self.db.list_collection_names():
                await self.db.create_collection("embedding_history")
                print("创建embedding_history集合用于存储历史记录")
            
            # 为历史记录集合创建索引
            embedding_history_indexes = [
                IndexModel([("repository_id", ASCENDING)]),
                IndexModel([("original_id", ASCENDING)]),
                IndexModel([("archived_at", DESCENDING)])
            ]
            await self.db.embedding_history.create_indexes(embedding_history_indexes)
            
            # 查找现有记录中的重复repository_id，将旧记录存入历史集合
            repo_ids = await self.db.embedding_status.distinct("repository_id")
            has_duplicates = False
            for repo_id in repo_ids:
                records = await self.db.embedding_status.find({"repository_id": repo_id}).sort("last_updated", -1).to_list(None)
                if len(records) > 1:
                    has_duplicates = True
                    # 保留最新的记录，将其他记录移到历史集合
                    latest_record = records[0]
                    for old_record in records[1:]:
                        # 添加归档时间并移除_id字段(让MongoDB自动生成新的)
                        old_id = old_record.pop("_id")
                        old_record["original_id"] = str(old_id)
                        old_record["archived_at"] = datetime.utcnow()
                        await self.db.embedding_history.insert_one(old_record)
                    
                    # 删除旧记录
                    await self.db.embedding_status.delete_many({
                        "repository_id": repo_id,
                        "_id": {"$ne": latest_record["_id"]}
                    })
                    print(f"仓库ID {repo_id} 的旧记录已移至历史集合")
            
            # 定义预期的索引规格
            expected_indexes = {
                "unique_repository_id": {"key": [("repository_id", ASCENDING)], "unique": True},
                "status_index": {"key": [("status", ASCENDING)]},
                "last_updated_index": {"key": [("last_updated", DESCENDING)]}
            }
            
            # 检查是否需要重建索引
            needs_rebuild = False
            
            # 检查是否有重复记录或索引不一致的情况
            if has_duplicates:
                needs_rebuild = True
            elif "_id_" in existing_indexes:  # 确保至少存在默认索引
                for idx_name, idx_spec in expected_indexes.items():
                    # 检查索引是否存在且规格一致
                    if idx_name not in existing_indexes:
                        needs_rebuild = True
                        break
                    
                    # 检查唯一性约束
                    if idx_name == "unique_repository_id" and "unique" in idx_spec:
                        if not existing_indexes.get(idx_name, {}).get("unique", False):
                            needs_rebuild = True
                            break
            else:
                # 如果没有找到索引，需要创建
                needs_rebuild = True
            
            # 仅在必要时重建索引
            if needs_rebuild:
                print("检测到索引需要更新，正在重建索引...")
                
                # 删除现有索引（保留_id索引）
                for idx_name in existing_indexes:
                    if idx_name != "_id_":
                        await self.db.embedding_status.drop_index(idx_name)
                        
                # 创建新索引
                embedding_status_indexes = [
                    IndexModel([("repository_id", ASCENDING)], unique=True, name="unique_repository_id"),
                    IndexModel([("status", ASCENDING)], name="status_index"),
                    IndexModel([("last_updated", DESCENDING)], name="last_updated_index")
                ]
                await self.db.embedding_status.create_indexes(embedding_status_indexes)
                print("成功重建embedding_status集合索引")
            else:
                print("embedding_status集合索引已是最新状态，无需重建")
        except Exception as e:
            print(f"初始化embedding_status集合时出错: {e}")
            # 记录错误但继续执行，不影响应用启动

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
