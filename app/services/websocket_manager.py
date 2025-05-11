import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from uuid import uuid4

from app.db.mongodb import mongodb
from app.db.redis import redis_manager

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    WebSocket连接管理器
    处理多用户连接、断线重连和消息广播
    """
    
    def __init__(self):
        # 存储活跃连接: {connection_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        
        # 用户连接映射: {user_id: [connection_id1, connection_id2, ...]}
        self.user_connections: Dict[str, List[str]] = {}
        
        # 会话订阅关系: {conversation_id: {connection_id1, connection_id2, ...}}
        self.conversation_subscribers: Dict[str, Set[str]] = {}
        
        # 连接状态: {connection_id: {"last_ping": timestamp, "user_id": user_id, ...}}
        self.connection_states: Dict[str, Dict[str, Any]] = {}
        
        # 心跳间隔(秒)
        self.heartbeat_interval = 30
        
        # 心跳超时(秒) - 超过此时间没收到心跳则认为连接断开
        self.heartbeat_timeout = 60
        
    async def connect(self, websocket: WebSocket, user_id: str, client_info: Dict[str, Any] = None) -> str:
        """
        注册新的WebSocket连接
        
        Args:
            websocket: WebSocket连接
            user_id: 用户ID
            client_info: 客户端信息(设备、浏览器等)
            
        Returns:
            connection_id: 新建连接的ID
        """
        # 生成唯一连接ID
        connection_id = str(uuid4())
        await websocket.accept()
        
        # 存储连接
        self.active_connections[connection_id] = websocket
        
        # 更新用户连接映射
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(connection_id)
        
        # 记录连接状态
        self.connection_states[connection_id] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow().isoformat(),
            "last_ping": datetime.utcnow().isoformat(),
            "client_info": client_info or {},
            "active_conversation_id": None
        }
        
        # 记录连接信息到数据库(用于断线重连恢复)
        await self._save_connection_state(connection_id)
        
        logger.info(f"New connection: {connection_id} for user {user_id}")
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """
        关闭并移除WebSocket连接
        
        Args:
            connection_id: 连接ID
        """
        if connection_id in self.active_connections:
            # 获取用户ID
            user_id = self.connection_states[connection_id]["user_id"]
            
            # 移除连接状态
            if connection_id in self.connection_states:
                # 先保存最终状态到数据库，用于可能的重连
                await self._save_connection_state(connection_id, is_disconnected=True)
                del self.connection_states[connection_id]
            
            # 从用户连接映射中移除
            if user_id in self.user_connections:
                if connection_id in self.user_connections[user_id]:
                    self.user_connections[user_id].remove(connection_id)
                    
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            # 从会话订阅中移除
            for conversation_id, subscribers in list(self.conversation_subscribers.items()):
                if connection_id in subscribers:
                    subscribers.remove(connection_id)
                    
                    # 如果会话没有订阅者，移除会话订阅记录
                    if not subscribers:
                        del self.conversation_subscribers[conversation_id]
            
            # 移除连接
            del self.active_connections[connection_id]
            
            logger.info(f"Connection closed: {connection_id} for user {user_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], connection_id: str):
        """
        发送消息给特定连接
        
        Args:
            message: 消息内容
            connection_id: 连接ID
        """
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            await websocket.send_json(message)
        else:
            logger.warning(f"Cannot send message to connection {connection_id}: connection not found")
    
    async def broadcast_to_conversation(self, message: Dict[str, Any], conversation_id: str, exclude: Optional[str] = None):
        """
        向会话的所有订阅者广播消息
        
        Args:
            message: 消息内容
            conversation_id: 会话ID
            exclude: 要排除的连接ID
        """
        if conversation_id in self.conversation_subscribers:
            for connection_id in self.conversation_subscribers[conversation_id]:
                if exclude and connection_id == exclude:
                    continue
                await self.send_personal_message(message, connection_id)
    
    async def broadcast_to_user(self, message: Dict[str, Any], user_id: str, exclude: Optional[str] = None):
        """
        向用户的所有连接广播消息
        
        Args:
            message: 消息内容
            user_id: 用户ID 
            exclude: 要排除的连接ID
        """
        if user_id in self.user_connections:
            for connection_id in self.user_connections[user_id]:
                if exclude and connection_id == exclude:
                    continue
                await self.send_personal_message(message, connection_id)
    
    async def subscribe_to_conversation(self, connection_id: str, conversation_id: str):
        """
        将连接订阅到会话
        
        Args:
            connection_id: 连接ID
            conversation_id: 会话ID
        """
        if connection_id not in self.active_connections:
            logger.warning(f"Cannot subscribe connection {connection_id}: connection not found")
            return False
            
        # 更新会话订阅关系
        if conversation_id not in self.conversation_subscribers:
            self.conversation_subscribers[conversation_id] = set()
        self.conversation_subscribers[conversation_id].add(connection_id)
        
        # 更新连接的活动会话
        if connection_id in self.connection_states:
            self.connection_states[connection_id]["active_conversation_id"] = conversation_id
            await self._save_connection_state(connection_id)
            
        # 发布事件通知其他订阅者
        user_id = self.connection_states[connection_id]["user_id"]
        
        # 广播用户加入通知(除了当前用户)
        await self.broadcast_to_conversation(
            {
                "type": "user_join",
                "conversation_id": conversation_id,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            conversation_id,
            exclude=connection_id
        )
        
        return True
    
    def get_conversation_subscribers(self, conversation_id: str) -> List[str]:
        """获取会话的所有订阅者连接ID"""
        if conversation_id in self.conversation_subscribers:
            return list(self.conversation_subscribers[conversation_id])
        return []
    
    def get_user_connections(self, user_id: str) -> List[str]:
        """获取用户的所有连接ID"""
        if user_id in self.user_connections:
            return self.user_connections[user_id]
        return []
    
    async def update_heartbeat(self, connection_id: str):
        """
        更新连接心跳时间戳
        
        Args:
            connection_id: 连接ID
        """
        if connection_id in self.connection_states:
            self.connection_states[connection_id]["last_ping"] = datetime.utcnow().isoformat()
            
            # 定期保存心跳状态到数据库
            now = datetime.utcnow()
            last_save = datetime.fromisoformat(self.connection_states[connection_id].get("last_saved", "2000-01-01T00:00:00"))
            
            # 每5分钟保存一次心跳状态
            if now - last_save > timedelta(minutes=5):
                await self._save_connection_state(connection_id)
                self.connection_states[connection_id]["last_saved"] = now.isoformat()
    
    async def _save_connection_state(self, connection_id: str, is_disconnected: bool = False):
        """
        保存连接状态到数据库
        用于断线重连时恢复状态
        
        Args:
            connection_id: 连接ID
            is_disconnected: 是否已断开连接
        """
        if connection_id in self.connection_states:
            state = self.connection_states[connection_id].copy()
            
            if is_disconnected:
                state["disconnected_at"] = datetime.utcnow().isoformat()
                state["status"] = "disconnected"
            else:
                state["status"] = "connected"
                state["last_saved"] = datetime.utcnow().isoformat()
            
            try:
                await mongodb.db.connection_states.update_one(
                    {"connection_id": connection_id},
                    {"$set": state},
                    upsert=True
                )
            except Exception as e:
                logger.error(f"Failed to save connection state: {e}")
    
    async def restore_connection(self, websocket: WebSocket, user_id: str, token: str, 
                               client_info: Dict[str, Any] = None) -> Optional[str]:
        """
        尝试恢复之前的连接状态
        
        Args:
            websocket: 新的WebSocket连接
            user_id: 用户ID 
            token: 重连令牌
            client_info: 客户端信息
            
        Returns:
            可能的旧连接ID，如果无法恢复则为None
        """
        try:
            # 从数据库查找断开的连接
            cutoff_time = (datetime.utcnow() - timedelta(hours=24)).isoformat()
            old_connection = await mongodb.db.connection_states.find_one({
                "user_id": user_id,
                "status": "disconnected", 
                "disconnected_at": {"$gte": cutoff_time},
                "client_info.reconnect_token": token
            }, sort=[("disconnected_at", -1)])
            
            if not old_connection:
                return None
            
            old_connection_id = old_connection.get("connection_id")
            if not old_connection_id:
                return None
            
            # 创建新连接
            connection_id = await self.connect(websocket, user_id, client_info)
            
            # 恢复会话订阅
            active_conversation_id = old_connection.get("active_conversation_id")
            if active_conversation_id:
                await self.subscribe_to_conversation(connection_id, active_conversation_id)
            
            # 更新旧连接的状态为已恢复
            await mongodb.db.connection_states.update_one(
                {"connection_id": old_connection_id},
                {"$set": {"status": "restored", "restored_connection_id": connection_id}}
            )
            
            logger.info(f"Restored connection {old_connection_id} as {connection_id} for user {user_id}")
            return old_connection_id
        except Exception as e:
            logger.error(f"Error restoring connection: {e}")
            return None
    
    async def monitor_connections(self):
        """
        定期监控连接状态
        检测超时连接并断开
        """
        while True:
            try:
                now = datetime.utcnow()
                timeout_threshold = now - timedelta(seconds=self.heartbeat_timeout)
                
                # 检查所有连接的心跳时间
                for connection_id, state in list(self.connection_states.items()):
                    last_ping = datetime.fromisoformat(state["last_ping"])
                    
                    # 判断连接是否超时
                    if last_ping < timeout_threshold:
                        try:
                            # 向客户端发送ping检查是否真的断开
                            websocket = self.active_connections[connection_id]
                            await websocket.send_json({"type": "ping"})
                        except Exception:
                            # 发送失败，关闭连接
                            logger.info(f"Connection {connection_id} timed out")
                            await self.disconnect(connection_id)
                
                # 发送心跳到所有连接
                for connection_id, websocket in list(self.active_connections.items()):
                    try:
                        await websocket.send_json({"type": "heartbeat", "timestamp": now.isoformat()})
                    except Exception:
                        # 发送失败，关闭连接
                        logger.info(f"Failed to send heartbeat to {connection_id}, disconnecting")
                        await self.disconnect(connection_id)
                
            except Exception as e:
                logger.error(f"Error in connection monitor: {e}")
            
            # 等待下一次检查
            await asyncio.sleep(self.heartbeat_interval)


# 全局连接管理器实例
connection_manager = ConnectionManager() 