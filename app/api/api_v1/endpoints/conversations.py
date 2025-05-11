import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST

from app.services.conversation_service import conversation_service
from app.models.conversation_models import (
    CreateConversationRequest,
    UpdateConversationRequest,
    MessageRequest,
    EditMessageRequest,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# 获取当前用户ID (暂时固定返回一个测试用户ID)
async def get_current_user_id():
    # 实际应用中，应该从JWT令牌或session中获取经过认证的用户ID
    # 这里为了测试，返回一个固定的测试用户ID
    return "507f1f77bcf86cd799439011"  # 模拟用户ID

@router.post("/", response_model=Dict[str, Any])
async def create_conversation(
    request: CreateConversationRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    """创建新的对话会话"""
    try:
        conversation = await conversation_service.create_conversation(
            user_id=current_user_id,
            title=request.title,
            project_id=request.project_id,
            repo_id=request.repo_id,
            settings=request.settings
        )
        
        return {
            "success": True,
            "data": conversation
        }
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Failed to create conversation: {str(e)}"
        )

@router.get("/", response_model=Dict[str, Any])
async def get_conversations(
    skip: int = 0,
    limit: int = 20,
    project_id: Optional[str] = None,
    current_user_id: str = Depends(get_current_user_id)
):
    """获取用户的对话会话列表"""
    try:
        result = await conversation_service.get_user_conversations(
            user_id=current_user_id,
            skip=skip,
            limit=limit,
            project_id=project_id
        )
        
        return {
            "success": True,
            "data": result.get("data", []),
            "total": result.get("total", 0),
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Error getting conversations: {str(e)}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Failed to get conversations: {str(e)}"
        )

@router.get("/{conversation_id}", response_model=Dict[str, Any])
async def get_conversation(
    conversation_id: str = Path(..., description="会话ID"),
    current_user_id: str = Depends(get_current_user_id)
):
    """获取指定对话会话的详情"""
    try:
        conversation = await conversation_service.get_conversation(conversation_id)
        
        if not conversation:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        # 检查权限（实际应用中应更严格）
        if str(conversation.get("user_id")) != current_user_id:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Not authorized to access this conversation"
            )
        
        return {
            "success": True,
            "data": conversation
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation {conversation_id}: {str(e)}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Failed to get conversation: {str(e)}"
        )

@router.put("/{conversation_id}", response_model=Dict[str, Any])
async def update_conversation(
    conversation_id: str = Path(..., description="会话ID"),
    request: UpdateConversationRequest = Body(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """更新对话会话信息"""
    try:
        # 检查会话是否存在
        conversation = await conversation_service.get_conversation(conversation_id)
        
        if not conversation:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        # 检查权限（实际应用中应更严格）
        if str(conversation.get("user_id")) != current_user_id:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Not authorized to update this conversation"
            )
        
        # 准备更新数据
        update_data = request.dict(exclude_unset=True)
        
        # 更新会话
        updated_conversation = await conversation_service.update_conversation(
            conversation_id=conversation_id,
            update_data=update_data
        )
        
        return {
            "success": True,
            "data": updated_conversation
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating conversation {conversation_id}: {str(e)}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Failed to update conversation: {str(e)}"
        )

@router.delete("/{conversation_id}", response_model=Dict[str, Any])
async def delete_conversation(
    conversation_id: str = Path(..., description="会话ID"),
    current_user_id: str = Depends(get_current_user_id)
):
    """删除对话会话"""
    try:
        # 删除会话
        result = await conversation_service.delete_conversation(
            conversation_id=conversation_id,
            user_id=current_user_id
        )
        
        if not result:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found or you don't have permission to delete it"
            )
        
        return {
            "success": True,
            "message": f"Conversation {conversation_id} deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation {conversation_id}: {str(e)}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete conversation: {str(e)}"
        )

@router.get("/{conversation_id}/messages", response_model=Dict[str, Any])
async def get_conversation_messages(
    conversation_id: str = Path(..., description="会话ID"),
    skip: int = 0,
    limit: int = 50,
    sort_order: str = "asc",
    current_user_id: str = Depends(get_current_user_id)
):
    """获取会话的消息列表"""
    try:
        # 检查会话是否存在
        conversation = await conversation_service.get_conversation(conversation_id)
        
        if not conversation:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        # 检查权限（实际应用中应更严格）
        if str(conversation.get("user_id")) != current_user_id:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Not authorized to view messages in this conversation"
            )
        
        result = await conversation_service.get_conversation_messages(
            conversation_id=conversation_id,
            skip=skip,
            limit=limit,
            sort_order=sort_order
        )
        
        return {
            "success": True,
            "data": result.get("data", []),
            "total": result.get("total", 0),
            "skip": skip,
            "limit": limit
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting messages for conversation {conversation_id}: {str(e)}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Failed to get conversation messages: {str(e)}"
        )

@router.post("/{conversation_id}/messages", response_model=Dict[str, Any])
async def create_message(
    conversation_id: str = Path(..., description="会话ID"),
    request: MessageRequest = Body(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """向会话发送消息"""
    try:
        # 检查会话是否存在
        conversation = await conversation_service.get_conversation(conversation_id)
        
        if not conversation:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )
        
        # 检查权限（实际应用中应更严格）
        if str(conversation.get("user_id")) != current_user_id:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Not authorized to send messages to this conversation"
            )
        
        # 创建用户消息
        from app.models.conversation_models import MessageRole, MessageType, MessageStatus
        
        message = await conversation_service.create_message(
            conversation_id=conversation_id,
            user_id=current_user_id,
            content=request.content,
            role=MessageRole.USER,
            message_type=request.type,
            metadata=request.metadata
        )
        
        # 这里会在后续章节实现AI响应生成
        # 现在先创建一个占位消息
        ai_message = await conversation_service.create_message(
            conversation_id=conversation_id,
            user_id=current_user_id,  # 使用用户ID作为系统消息的发送者
            content="正在思考中...",
            role=MessageRole.ASSISTANT,
            message_type=MessageType.TEXT,
            status=MessageStatus.PROCESSING,
            metadata={"is_thinking": True}
        )
        
        return {
            "success": True,
            "data": {
                "user_message": message,
                "ai_message_id": str(ai_message.get("_id"))
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating message in conversation {conversation_id}: {str(e)}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Failed to create message: {str(e)}"
        )

@router.put("/messages/{message_id}", response_model=Dict[str, Any])
async def edit_message(
    message_id: str = Path(..., description="消息ID"),
    request: EditMessageRequest = Body(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """编辑消息"""
    try:
        # 获取当前消息
        message = await conversation_service.get_message(message_id)
        
        if not message:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Message {message_id} not found"
            )
        
        # 检查权限（实际应用中应更严格）
        if str(message.get("user_id")) != current_user_id:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Not authorized to edit this message"
            )
        
        # 检查角色和类型（只允许编辑自己的USER角色消息）
        from app.models.conversation_models import MessageRole
        if message.get("role") != MessageRole.USER:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Can only edit user messages"
            )
        
        # 更新消息
        updated_message = await conversation_service.update_message(
            message_id=message_id,
            update_data={
                "content": request.content,
                "metadata": request.metadata
            }
        )
        
        # 这里后面需要实现：当用户编辑消息时，重新生成AI响应
        
        return {
            "success": True,
            "data": updated_message
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error editing message {message_id}: {str(e)}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Failed to edit message: {str(e)}"
        )

@router.delete("/messages/{message_id}", response_model=Dict[str, Any])
async def delete_message(
    message_id: str = Path(..., description="消息ID"),
    current_user_id: str = Depends(get_current_user_id)
):
    """删除消息"""
    try:
        # 获取当前消息
        message = await conversation_service.get_message(message_id)
        
        if not message:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Message {message_id} not found"
            )
        
        # 检查权限（实际应用中应更严格）
        if str(message.get("user_id")) != current_user_id:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Not authorized to delete this message"
            )
        
        # 删除消息
        result = await conversation_service.delete_message(message_id)
        
        if not result:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Failed to delete message {message_id}"
            )
        
        return {
            "success": True,
            "message": f"Message {message_id} deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting message {message_id}: {str(e)}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete message: {str(e)}"
        ) 