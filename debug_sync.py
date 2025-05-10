import logging
import asyncio
from bson import ObjectId
from app.db.mongodb import mongodb
from app.services.git_sync_service import GitSyncService

# 配置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='debug.log'
)

# 添加控制台输出
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

logger = logging.getLogger(__name__)

async def debug_sync():
    try:
        # 连接数据库
        await mongodb.connect_to_mongodb()
        logger.info("Connected to MongoDB")
        
        # 实例化同步服务
        service = GitSyncService()
        
        # 获取仓库ID
        repo_id = "681fc1caeb996ff186c68c3d"
        
        # 获取仓库信息
        repo = await mongodb.db.repositories.find_one({"_id": ObjectId(repo_id)})
        logger.info(f"Repository: {repo}")
        
        # 获取凭证信息
        if repo:
            credential = await mongodb.db.git_credentials.find_one({"_id": repo["credential_id"]})
            logger.info(f"Credential: {str(credential)[:100]}...")
        
        # 执行同步
        logger.info(f"Starting sync for repository {repo_id}")
        try:
            result = await service.sync_repository(repo_id, "full")
            logger.info(f"Sync result: {result}")
        except Exception as e:
            logger.exception(f"Sync failed with error: {str(e)}")
        
    except Exception as e:
        logger.exception(f"Debug failed with error: {str(e)}")
    finally:
        if mongodb.client:
            await mongodb.client.close()
            logger.info("MongoDB connection closed")

if __name__ == "__main__":
    asyncio.run(debug_sync()) 