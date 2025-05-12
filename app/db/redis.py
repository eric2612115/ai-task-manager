import asyncio
import json
from typing import Any, Dict, Optional, Callable
import redis.asyncio as redis

from app.core.config import settings
from app.core.custom_json import CustomJSONEncoder

class RedisManager:
    _redis = None
    
    @classmethod
    async def get_redis_connection(cls):
        """獲取Redis連接，如果不存在則創建"""
        if cls._redis is None:
            try:
                cls._redis = await redis.from_url(settings.REDIS_URL, decode_responses=True)
                await cls._redis.ping()
                print("Successfully connected to Redis")
            except Exception as e:
                print(f"Failed to connect to Redis: {e}")
                raise
        return cls._redis
    
    @classmethod
    async def close_redis_connection(cls):
        """關閉Redis連接"""
        if cls._redis is not None:
            await cls._redis.close()
            cls._redis = None
            print("Redis connection closed")
    
    @classmethod
    async def publish_event(cls, channel: str, event_type: str, data: Dict[str, Any], id: Optional[str] = None, retry: int = 5000):
        """將事件發布到Redis頻道"""
        redis_conn = await cls.get_redis_connection()
        event_data = {
            "event": event_type,
            "data": data,
            "id": id,
            "retry": retry
        }
        await redis_conn.publish(channel, json.dumps(event_data, cls=CustomJSONEncoder))
    
    @classmethod
    async def subscribe_to_channels(cls, channels: list, callback: Callable):
        """訂閱一個或多個Redis頻道並處理接收到的消息"""
        redis_conn = await cls.get_redis_connection()
        pubsub = redis_conn.pubsub()
        await pubsub.subscribe(*channels)
        
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    await callback(message['channel'], message['data'])
        finally:
            await pubsub.unsubscribe(*channels)

# Create Redis manager instance
redis_manager = RedisManager()
