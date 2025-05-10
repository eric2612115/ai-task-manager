import asyncio
import logging
from bson import ObjectId
from cryptography.fernet import Fernet, InvalidToken
from app.db.mongodb import mongodb
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 设置新的加密器
cipher = Fernet(settings.ENCRYPTION_KEY.encode())

async def reset_credentials():
    """重置所有凭证的令牌"""
    try:
        # 连接到数据库
        await mongodb.connect_to_mongodb()
        logger.info("Connected to MongoDB")
        
        # 获取所有凭证
        credentials = await mongodb.db.git_credentials.find().to_list(length=100)
        logger.info(f"Found {len(credentials)} credentials")
        
        # 设置一个默认的测试令牌
        default_token = "ghp_testdefaulttoken123456"
        encrypted_token = cipher.encrypt(default_token.encode()).decode()
        
        # 更新所有凭证
        for cred in credentials:
            try:
                logger.info(f"Updating credential {cred['_id']}: {cred.get('name', 'unknown')}")
                
                # 更新为新的加密令牌
                result = await mongodb.db.git_credentials.update_one(
                    {"_id": cred["_id"]},
                    {"$set": {
                        "token": encrypted_token,
                        "status": "invalid"  # 标记为无效，需要用户重新设置
                    }}
                )
                
                if result.modified_count > 0:
                    logger.info(f"Successfully updated credential {cred['_id']}")
                else:
                    logger.warning(f"Failed to update credential {cred['_id']}")
                
            except Exception as e:
                logger.error(f"Error updating credential {cred['_id']}: {str(e)}")
        
        logger.info("Credential reset completed")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
    finally:
        if mongodb.client:
            await mongodb.client.close()
            logger.info("MongoDB connection closed")

if __name__ == "__main__":
    asyncio.run(reset_credentials()) 