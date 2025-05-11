import asyncio
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from bson import ObjectId

from app.db.mongodb import mongodb
from app.db.redis import redis_manager
from app.models.conversation_models import (
    Conversation,
    Message,
    MessageRole,
    MessageStatus,
    MessageType
)
from app.core.utils import serialize_mongodb_doc
from app.services.websocket_manager import connection_manager

logger = logging.getLogger(__name__)

class ConversationService:
    """对话会话服务"""
    
    async def create_conversation(self, user_id: str, title: str, project_id: Optional[str] = None, 
                                repo_id: Optional[str] = None, settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        创建新会话
        
        Args:
            user_id: 用户ID
            title: 会话标题
            project_id: 关联项目ID
            repo_id: 关联代码仓库ID
            settings: 会话设置
            
        Returns:
            新创建的会话
        """
        try:
            # 创建会话记录
            conversation_data = {
                "user_id": ObjectId(user_id),
                "title": title,
                "created_at": datetime.utcnow(),
                "last_message_at": datetime.utcnow(),
                "message_count": 0
            }
            
            if project_id:
                conversation_data["project_id"] = ObjectId(project_id)
                
            if repo_id:
                conversation_data["repo_id"] = ObjectId(repo_id)
            
            if settings:
                conversation_data["settings"] = settings
            
            result = await mongodb.db.conversations.insert_one(conversation_data)
            conversation_id = str(result.inserted_id)
            
            # 读取创建的会话
            conversation = await self.get_conversation(conversation_id)
            
            # 发布会话创建事件
            await redis_manager.publish_event(
                channel=f"user:{user_id}:conversations",
                event_type="conversation.created",
                data={"conversation_id": conversation_id}
            )
            
            return conversation
        
        except Exception as e:
            logger.error(f"Error creating conversation: {str(e)}")
            raise
    
    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话详情
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            会话详情，如果不存在则返回None
        """
        try:
            conversation = await mongodb.db.conversations.find_one({"_id": ObjectId(conversation_id)})
            
            if conversation:
                return serialize_mongodb_doc(conversation)
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting conversation {conversation_id}: {str(e)}")
            raise
    
    async def update_conversation(self, conversation_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        更新会话
        
        Args:
            conversation_id: 会话ID
            update_data: 要更新的字段
            
        Returns:
            更新后的会话
        """
        try:
            # 移除不能直接更新的字段
            safe_update = update_data.copy()
            for field in ["_id", "user_id", "created_at"]:
                safe_update.pop(field, None)
            
            # 设置更新时间
            safe_update["updated_at"] = datetime.utcnow()
            
            result = await mongodb.db.conversations.update_one(
                {"_id": ObjectId(conversation_id)},
                {"$set": safe_update}
            )
            
            if result.modified_count == 0:
                logger.warning(f"No changes applied to conversation {conversation_id}")
            
            # 获取更新后的会话
            updated_conversation = await self.get_conversation(conversation_id)
            
            if updated_conversation:
                # 广播会话更新事件
                user_id = str(updated_conversation.get("user_id"))
                await redis_manager.publish_event(
                    channel=f"user:{user_id}:conversations",
                    event_type="conversation.updated",
                    data={
                        "conversation_id": conversation_id, 
                        "updated_fields": list(safe_update.keys())
                    }
                )
                
                # 通知WebSocket订阅者
                await connection_manager.broadcast_to_conversation(
                    {
                        "type": "conversation_updated",
                        "data": {
                            "conversation_id": conversation_id,
                            "updated_fields": list(safe_update.keys())
                        }
                    },
                    conversation_id
                )
            
            return updated_conversation
        
        except Exception as e:
            logger.error(f"Error updating conversation {conversation_id}: {str(e)}")
            raise
    
    async def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        """
        删除会话
        
        Args:
            conversation_id: 会话ID
            user_id: 请求删除的用户ID
            
        Returns:
            删除是否成功
        """
        try:
            # 获取会话检查权限
            conversation = await mongodb.db.conversations.find_one({
                "_id": ObjectId(conversation_id),
                "user_id": ObjectId(user_id)
            })
            
            if not conversation:
                logger.warning(f"User {user_id} attempted to delete conversation {conversation_id} without permission")
                return False
            
            # 删除会话
            delete_result = await mongodb.db.conversations.delete_one({"_id": ObjectId(conversation_id)})
            
            if delete_result.deleted_count == 0:
                logger.warning(f"Failed to delete conversation {conversation_id}")
                return False
            
            # 删除会话中的所有消息
            await mongodb.db.messages.delete_many({"conversation_id": ObjectId(conversation_id)})
            
            # 发布会话删除事件
            await redis_manager.publish_event(
                channel=f"user:{user_id}:conversations",
                event_type="conversation.deleted",
                data={"conversation_id": conversation_id}
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Error deleting conversation {conversation_id}: {str(e)}")
            raise
    
    async def get_user_conversations(self, user_id: str, skip: int = 0, limit: int = 20, 
                                   project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取用户的会话列表
        
        Args:
            user_id: 用户ID
            skip: 分页偏移
            limit: 分页限制
            project_id: 如果提供，则过滤特定项目的会话
            
        Returns:
            会话列表和总数
        """
        try:
            # 构建查询条件
            query = {"user_id": ObjectId(user_id)}
            
            if project_id:
                query["project_id"] = ObjectId(project_id)
            
            # 计算总数
            total_count = await mongodb.db.conversations.count_documents(query)
            
            # 查询会话
            cursor = mongodb.db.conversations.find(query)
            
            # 排序: 置顶的排在前面，然后按最后活跃时间倒序
            cursor = cursor.sort([("is_pinned", -1), ("last_message_at", -1)])
            
            # 应用分页
            cursor = cursor.skip(skip).limit(limit)
            
            # 获取结果
            conversations = []
            async for doc in cursor:
                conversations.append(serialize_mongodb_doc(doc))
            
            return {
                "data": conversations,
                "total": total_count,
                "skip": skip,
                "limit": limit
            }
        
        except Exception as e:
            logger.error(f"Error getting conversations for user {user_id}: {str(e)}")
            raise
    
    async def create_message(self, conversation_id: str, user_id: str, content: str,
                         role: MessageRole, message_type: MessageType = MessageType.TEXT,
                         references: List[Dict[str, Any]] = None, status: MessageStatus = MessageStatus.COMPLETED,
                         metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        创建消息
        
        Args:
            conversation_id: 会话ID
            user_id: 用户ID
            content: 消息内容
            role: 消息角色
            message_type: 消息类型
            references: RAG引用列表
            status: 消息状态
            metadata: 消息元数据
            
        Returns:
            创建的消息
        """
        try:
            # 检查会话是否存在
            conversation = await mongodb.db.conversations.find_one({"_id": ObjectId(conversation_id)})
            if not conversation:
                logger.error(f"Conversation {conversation_id} not found")
                raise ValueError(f"Conversation {conversation_id} not found")
            
            # 创建消息记录
            message_data = {
                "conversation_id": ObjectId(conversation_id),
                "user_id": ObjectId(user_id),
                "role": role,
                "content": content,
                "type": message_type,
                "status": status,
                "created_at": datetime.utcnow(),
                "references": references or [],
                "metadata": metadata or {}
            }
            
            result = await mongodb.db.messages.insert_one(message_data)
            message_id = str(result.inserted_id)
            
            # 更新会话的最后活跃时间和消息计数
            await mongodb.db.conversations.update_one(
                {"_id": ObjectId(conversation_id)},
                {
                    "$set": {"last_message_at": datetime.utcnow()},
                    "$inc": {"message_count": 1}
                }
            )
            
            # 获取创建的消息
            message = await self.get_message(message_id)
            
            # 通知WebSocket订阅者
            await connection_manager.broadcast_to_conversation(
                {
                    "type": "new_message",
                    "data": message
                },
                conversation_id
            )
            
            # 发布消息创建事件
            await redis_manager.publish_event(
                channel=f"conversation:{conversation_id}:messages",
                event_type="message.created",
                data={"message_id": message_id}
            )
            
            return message
        
        except Exception as e:
            logger.error(f"Error creating message: {str(e)}")
            raise
    
    async def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        获取消息详情
        
        Args:
            message_id: 消息ID
            
        Returns:
            消息详情，如果不存在则返回None
        """
        try:
            message = await mongodb.db.messages.find_one({"_id": ObjectId(message_id)})
            
            if message:
                return serialize_mongodb_doc(message)
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting message {message_id}: {str(e)}")
            raise
    
    async def update_message(self, message_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        更新消息
        
        Args:
            message_id: 消息ID
            update_data: 要更新的字段
            
        Returns:
            更新后的消息
        """
        try:
            # 移除不能直接更新的字段
            safe_update = update_data.copy()
            for field in ["_id", "conversation_id", "user_id", "created_at"]:
                safe_update.pop(field, None)
            
            # 标记编辑
            if "content" in safe_update:
                # 先获取原消息
                original_message = await mongodb.db.messages.find_one({"_id": ObjectId(message_id)})
                if original_message and not original_message.get("edited"):
                    safe_update["edited"] = True
                    safe_update["edited_at"] = datetime.utcnow()
                    safe_update["original_content"] = original_message.get("content")
            
            # 设置更新时间
            safe_update["updated_at"] = datetime.utcnow()
            
            result = await mongodb.db.messages.update_one(
                {"_id": ObjectId(message_id)},
                {"$set": safe_update}
            )
            
            if result.modified_count == 0:
                logger.warning(f"No changes applied to message {message_id}")
            
            # 获取更新后的消息
            updated_message = await self.get_message(message_id)
            
            if updated_message:
                conversation_id = str(updated_message.get("conversation_id"))
                
                # 通知WebSocket订阅者
                await connection_manager.broadcast_to_conversation(
                    {
                        "type": "message_updated",
                        "data": updated_message
                    },
                    conversation_id
                )
                
                # 发布消息更新事件
                await redis_manager.publish_event(
                    channel=f"conversation:{conversation_id}:messages",
                    event_type="message.updated",
                    data={"message_id": message_id, "updated_fields": list(safe_update.keys())}
                )
            
            return updated_message
        
        except Exception as e:
            logger.error(f"Error updating message {message_id}: {str(e)}")
            raise
    
    async def delete_message(self, message_id: str) -> bool:
        """
        删除消息
        
        Args:
            message_id: 消息ID
            
        Returns:
            删除是否成功
        """
        try:
            # 获取消息
            message = await mongodb.db.messages.find_one({"_id": ObjectId(message_id)})
            if not message:
                logger.warning(f"Message {message_id} not found for deletion")
                return False
            
            conversation_id = str(message.get("conversation_id"))
            
            # 删除消息
            delete_result = await mongodb.db.messages.delete_one({"_id": ObjectId(message_id)})
            
            if delete_result.deleted_count == 0:
                logger.warning(f"Failed to delete message {message_id}")
                return False
            
            # 更新会话消息计数
            await mongodb.db.conversations.update_one(
                {"_id": ObjectId(conversation_id)},
                {"$inc": {"message_count": -1}}
            )
            
            # 通知WebSocket订阅者
            await connection_manager.broadcast_to_conversation(
                {
                    "type": "message_deleted",
                    "data": {
                        "message_id": message_id,
                        "conversation_id": conversation_id
                    }
                },
                conversation_id
            )
            
            # 发布消息删除事件
            await redis_manager.publish_event(
                channel=f"conversation:{conversation_id}:messages",
                event_type="message.deleted",
                data={"message_id": message_id}
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Error deleting message {message_id}: {str(e)}")
            raise
    
    async def get_conversation_messages(self, conversation_id: str, skip: int = 0, 
                                       limit: int = 50, sort_order: str = "desc") -> Dict[str, Any]:
        """
        获取会话的消息列表
        
        Args:
            conversation_id: 会话ID
            skip: 分页偏移
            limit: 分页限制
            sort_order: 排序方向，asc（旧->新）或desc（新->旧）
            
        Returns:
            消息列表和总数
        """
        try:
            # 构建查询条件
            query = {"conversation_id": ObjectId(conversation_id)}
            
            # 计算总数
            total_count = await mongodb.db.messages.count_documents(query)
            
            # 确定排序方向
            sort_direction = -1 if sort_order.lower() == "desc" else 1
            
            # 查询消息
            cursor = mongodb.db.messages.find(query)
            cursor = cursor.sort([("created_at", sort_direction)])
            
            # 应用分页
            cursor = cursor.skip(skip).limit(limit)
            
            # 获取结果
            messages = []
            async for doc in cursor:
                messages.append(serialize_mongodb_doc(doc))
            
            # 如果是时间倒序，返回时再反转回来为正常对话顺序
            if sort_order.lower() == "desc":
                messages.reverse()
            
            return {
                "data": messages,
                "total": total_count,
                "skip": skip,
                "limit": limit
            }
        
        except Exception as e:
            logger.error(f"Error getting messages for conversation {conversation_id}: {str(e)}")
            raise

# 全局会话服务实例
conversation_service = ConversationService() 