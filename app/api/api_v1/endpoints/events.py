import json
import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
from starlette.responses import StreamingResponse
from bson import ObjectId

from app.db.mongodb import mongodb
from app.db.redis import redis_manager

router = APIRouter()

# 獲取當前用戶ID (暫時固定返回一個測試用戶ID)
async def get_current_user_id():
    # 實際應用中，應該從JWT令牌或session中獲取經過認證的用戶ID
    # 這里為了測試，返回一個固定的測試用戶ID
    return "507f1f77bcf86cd799439011"  # 模擬用戶ID

def format_sse_event(event_type: str, data: dict, id: Optional[str] = None, retry: int = 5000) -> str:
    """
    格式化 Server-Sent Events (SSE) 消息
    """
    message = [f"event: {event_type}"]
    
    if id:
        message.append(f"id: {id}")
        
    message.append(f"retry: {retry}")
    message.append(f"data: {json.dumps(data)}")
    message.append("\n")
    
    return "\n".join(message)

async def sse_callback(channel_name: str, message: str, queue: asyncio.Queue):
    """
    Redis 訂閱回調函數，向 SSE 隊列添加消息
    """
    try:
        data = json.loads(message)
        await queue.put((data.get("event"), data.get("data"), data.get("id"), data.get("retry", 5000)))
    except Exception as e:
        print(f"Error processing Redis message: {e}")

@router.get("/{user_id}")
async def events_stream(
    request: Request,
    user_id: str = Path(...),
    project_id: Optional[str] = None,
    task_id: Optional[str] = None
):
    """
    建立與服務器的 Server-Sent Events 連接，接收綁定到 {user_id} 的數據實時更新。
    可選參數:
    - project_id: 限制接收特定專案的更新
    - task_id: 限制接收特定任務的更新
    """
    try:
        # 驗證用戶ID是否有效
        if not ObjectId.is_valid(user_id):
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
            
        # 檢查用戶是否存在
        user = await mongodb.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")
        
        # 初始化訂閱的頻道列表
        channels = [
            f"user:{user_id}:notifications"  # 用戶通知頻道
        ]
        
        if project_id:
            # 驗證專案ID是否有效
            if not ObjectId.is_valid(project_id):
                raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid project ID format")
                
            # 檢查專案是否存在
            project = await mongodb.db.projects.find_one({"_id": ObjectId(project_id)})
            if not project:
                raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Project not found")
                
            # 檢查用戶是否有權訪問該專案（在實際應用中需要更嚴格的檢查）
            
            # 訂閱專案頻道
            channels.append(f"project:{project_id}:events")
        
        if task_id:
            # 驗證任務ID是否有效
            if not ObjectId.is_valid(task_id):
                raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid task ID format")
                
            # 檢查任務是否存在
            task = await mongodb.db.tasks.find_one({"_id": ObjectId(task_id)})
            if not task:
                raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Task not found")
                
            # 訂閱任務頻道
            channels.append(f"task:{task_id}:updates")
        
        # 如果沒有指定專案或任務，訂閱全局事件頻道
        if not project_id and not task_id:
            channels.append("global:events")
        
        # 創建消息隊列
        queue = asyncio.Queue()
        
        # 啟動對 Redis 頻道的訂閱
        redis_subscription_task = asyncio.create_task(
            subscribe_to_redis_channels(channels, queue)
        )
        
        # 發送一個初始連接成功事件
        await queue.put(("connected", {"status": "connected", "channels": channels}, None, None))
        
        # 返回 SSE 流
        return StreamingResponse(
            sse_stream(request, queue, redis_subscription_task),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error setting up event stream: {str(e)}"
        )

async def subscribe_to_redis_channels(channels: List[str], queue: asyncio.Queue):
    """
    訂閱 Redis 頻道，將收到的消息發送到隊列
    """
    redis_conn = await redis_manager.get_redis_connection()
    pubsub = redis_conn.pubsub()
    
    # 訂閱所有指定的頻道
    await pubsub.subscribe(*channels)
    
    try:
        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    await queue.put((
                        data.get("event"),
                        data.get("data"),
                        data.get("id"),
                        data.get("retry", 5000)
                    ))
                except Exception as e:
                    print(f"Error processing Redis message: {e}")
    finally:
        # 取消訂閱
        await pubsub.unsubscribe(*channels)

async def sse_stream(request: Request, queue: asyncio.Queue, redis_subscription_task):
    """
    生成 SSE 事件流
    """
    try:
        # 發送初始連接信息
        yield "retry: 5000\n\n"
        
        while True:
            if await request.is_disconnected():
                break
                
            try:
                # 從隊列獲取消息，帶超時
                event_type, data, id, retry = await asyncio.wait_for(queue.get(), timeout=1.0)
                
                # 格式化為 SSE 消息並發送
                sse_message = format_sse_event(event_type, data, id, retry or 5000)
                yield sse_message
                
                # 標記任務完成
                queue.task_done()
                
            except asyncio.TimeoutError:
                # 超時，發送心跳 (保持連接)
                yield ": heartbeat\n\n"
                
            except Exception as e:
                print(f"Error in SSE stream: {e}")
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
    finally:
        # 確保取消訂閱任務
        if not redis_subscription_task.done():
            redis_subscription_task.cancel()
            try:
                await redis_subscription_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"Error cancelling Redis subscription: {e}")
