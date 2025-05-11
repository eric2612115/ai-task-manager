import json
import logging
import asyncio
from typing import Optional, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED
import secrets
import time

from app.services.websocket_manager import connection_manager
from app.services.conversation_service import conversation_service
from app.models.conversation_models import MessageRole, MessageType, MessageStatus

router = APIRouter()
logger = logging.getLogger(__name__)

# 获取当前用户ID (暂时固定返回一个测试用户ID)
async def get_current_user_id():
    # 实际应用中，应该从JWT令牌或session中获取经过认证的用户ID
    # 这里为了测试，返回一个固定的测试用户ID
    return "507f1f77bcf86cd799439011"  # 模拟用户ID

@router.websocket("/chat")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = None,
    conversation_id: Optional[str] = None,
    reconnect_token: Optional[str] = None
):
    """
    WebSocket聊天端点
    
    Args:
        websocket: WebSocket连接
        token: 用户认证令牌(未来实现)
        conversation_id: 要加入的会话ID
        reconnect_token: 重连令牌，用于恢复断线会话
    """
    # 获取用户ID（实际应用中应从token验证）
    user_id = await get_current_user_id()
    
    # 生成客户端信息
    client_info = {
        "user_agent": websocket.headers.get("user-agent", ""),
        "ip": websocket.client.host,
        "reconnect_token": reconnect_token or secrets.token_urlsafe(16),
        "connection_time": time.time()
    }
    
    # 连接ID，用于标识WebSocket连接
    connection_id = None
    
    try:
        if reconnect_token:
            # 尝试恢复连接
            old_connection_id = await connection_manager.restore_connection(
                websocket, user_id, reconnect_token, client_info
            )
            
            if old_connection_id:
                logger.info(f"Reconnected user {user_id} with token {reconnect_token}")
                # 获取新连接ID
                for conn_id, conn_state in connection_manager.connection_states.items():
                    if conn_state.get("user_id") == user_id and conn_state.get("client_info", {}).get("reconnect_token") == reconnect_token:
                        connection_id = conn_id
                        break
            else:
                # 重连失败，创建新连接
                connection_id = await connection_manager.connect(websocket, user_id, client_info)
        else:
            # 直接建立新连接
            connection_id = await connection_manager.connect(websocket, user_id, client_info)
        
        # 发送连接成功消息
        await websocket.send_json({
            "type": "connected",
            "data": {
                "connection_id": connection_id,
                "user_id": user_id,
                "reconnect_token": client_info["reconnect_token"]
            }
        })
        
        # 如果指定了会话ID，订阅该会话
        if conversation_id:
            subscription_result = await connection_manager.subscribe_to_conversation(connection_id, conversation_id)
            if subscription_result:
                await websocket.send_json({
                    "type": "subscribed",
                    "data": {
                        "conversation_id": conversation_id
                    }
                })
            else:
                await websocket.send_json({
                    "type": "error",
                    "data": {
                        "message": "Failed to subscribe to conversation"
                    }
                })
        
        # 消息监听循环
        while True:
            # 接收客户端消息
            message = await websocket.receive_text()
            
            try:
                # 解析消息
                data = json.loads(message)
                msg_type = data.get("type")
                
                # 更新心跳
                await connection_manager.update_heartbeat(connection_id)
                
                # 处理不同类型的消息
                if msg_type == "ping":
                    # 心跳消息
                    await websocket.send_json({"type": "pong", "timestamp": time.time()})
                    
                elif msg_type == "subscribe":
                    # 订阅会话
                    conv_id = data.get("conversation_id")
                    if conv_id:
                        success = await connection_manager.subscribe_to_conversation(connection_id, conv_id)
                        await websocket.send_json({
                            "type": "subscribed" if success else "error",
                            "data": {
                                "conversation_id": conv_id,
                                "success": success,
                                "message": None if success else "Failed to subscribe"
                            }
                        })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "data": {"message": "Missing conversation_id"}
                        })
                    
                elif msg_type == "message":
                    # 新消息
                    conv_id = data.get("conversation_id")
                    content = data.get("content")
                    metadata = data.get("metadata", {})
                    
                    if not conv_id or not content:
                        await websocket.send_json({
                            "type": "error",
                            "data": {"message": "Missing conversation_id or content"}
                        })
                        continue
                    
                    # 创建用户消息
                    user_message = await conversation_service.create_message(
                        conversation_id=conv_id,
                        user_id=user_id,
                        content=content,
                        role=MessageRole.USER,
                        message_type=MessageType.TEXT,
                        metadata=metadata
                    )
                    
                    # 此处会在后续实现AI响应生成部分
                    # 这里先创建一个占位消息，表示AI正在处理
                    await conversation_service.create_message(
                        conversation_id=conv_id,
                        user_id=user_id,  # 使用用户ID作为系统消息的发送者
                        content="正在思考中...",
                        role=MessageRole.ASSISTANT,
                        message_type=MessageType.TEXT,
                        status=MessageStatus.PROCESSING,
                        metadata={"is_thinking": True}
                    )
                    
                elif msg_type == "typing":
                    # 用户正在输入
                    conv_id = data.get("conversation_id")
                    if conv_id:
                        # 通知其他人用户正在输入
                        await connection_manager.broadcast_to_conversation(
                            {
                                "type": "typing",
                                "data": {
                                    "user_id": user_id,
                                    "conversation_id": conv_id,
                                    "timestamp": time.time()
                                }
                            },
                            conv_id,
                            exclude=connection_id
                        )
                
                elif msg_type == "edit_message":
                    # 编辑消息
                    message_id = data.get("message_id")
                    content = data.get("content")
                    
                    if not message_id or not content:
                        await websocket.send_json({
                            "type": "error",
                            "data": {"message": "Missing message_id or content"}
                        })
                        continue
                    
                    # 更新消息
                    updated_message = await conversation_service.update_message(
                        message_id=message_id,
                        update_data={"content": content}
                    )
                    
                    if updated_message:
                        await websocket.send_json({
                            "type": "message_updated",
                            "data": updated_message
                        })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "data": {"message": "Failed to update message"}
                        })
                
                else:
                    # 未知消息类型
                    logger.warning(f"Unknown message type: {msg_type}")
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": f"Unknown message type: {msg_type}"}
                    })
            
            except json.JSONDecodeError:
                logger.warning("Received invalid JSON")
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "Invalid JSON message"}
                })
                
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": f"Error: {str(e)}"}
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected, connection_id: {connection_id}")
        # 处理断开连接
        if connection_id:
            await connection_manager.disconnect(connection_id)
    
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        # 处理异常
        if connection_id:
            await connection_manager.disconnect(connection_id)

@router.websocket("/chat/{conversation_id}")
async def websocket_conversation_endpoint(
    websocket: WebSocket,
    conversation_id: str,
    token: Optional[str] = None,
    reconnect_token: Optional[str] = None
):
    """
    直接连接到指定会话的WebSocket端点
    
    Args:
        websocket: WebSocket连接
        conversation_id: 会话ID
        token: 用户认证令牌(未来实现)
        reconnect_token: 重连令牌
    """
    await websocket_endpoint(websocket, token, conversation_id, reconnect_token) 