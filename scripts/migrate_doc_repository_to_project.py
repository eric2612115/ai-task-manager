#!/usr/bin/env python
"""
遷移文檔關聯：從repository_id遷移到project_id
"""
import asyncio
import logging
import sys
from typing import List, Dict
from datetime import datetime

# 將項目根目錄添加到路徑中，以便導入應用模塊
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.mongodb import mongodb, get_database
from bson import ObjectId

# 設置日誌記錄
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("doc-migration")

async def migrate_documents():
    """將文檔從repository_id遷移到project_id"""
    # 確保數據庫連接
    await get_database()
    
    # 獲取所有有repository_id但沒有project_id的文檔
    docs_to_migrate = await mongodb.db.project_documentations.find({
        "repository_id": {"$exists": True}, 
        "project_id": {"$exists": False}
    }).to_list(None)
    
    logger.info(f"Found {len(docs_to_migrate)} documents to migrate")
    
    migrated_count = 0
    failed_count = 0
    
    for doc in docs_to_migrate:
        try:
            # 根據repository_id查找倉庫
            repo = await mongodb.db.repositories.find_one({"_id": doc["repository_id"]})
            
            if not repo:
                logger.warning(f"Repository {doc['repository_id']} not found for document {doc['_id']}")
                continue
                
            # 檢查倉庫是否有project_id
            if "project_id" not in repo:
                logger.warning(f"Repository {doc['repository_id']} has no project_id")
                continue
                
            # 更新文檔，添加project_id
            result = await mongodb.db.project_documentations.update_one(
                {"_id": doc["_id"]},
                {
                    "$set": {
                        "project_id": repo["project_id"],
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                migrated_count += 1
                logger.info(f"Migrated document {doc['_id']}: repository_id={doc['repository_id']} -> project_id={repo['project_id']}")
            else:
                failed_count += 1
                logger.error(f"Failed to migrate document {doc['_id']}")
                
        except Exception as e:
            failed_count += 1
            logger.error(f"Error migrating document {doc['_id']}: {str(e)}")
    
    logger.info(f"Migration completed: {migrated_count} documents migrated, {failed_count} failed")
    
    # 如果有需要，可以在這裡添加代碼來處理無法遷移的文檔
    # 例如，為它們分配一個默認的項目ID，或者將它們標記為需要人工處理

async def main():
    """主函數"""
    logger.info("Starting document migration from repository_id to project_id")
    await migrate_documents()
    logger.info("Migration process completed")

if __name__ == "__main__":
    asyncio.run(main()) 