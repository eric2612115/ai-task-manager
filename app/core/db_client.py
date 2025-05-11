import motor.motor_asyncio
from app.core.config import settings

# MongoDB client singleton
_client = None

async def get_db_client():
    """
    Returns a MongoDB client instance.
    Uses a singleton pattern to avoid creating multiple connections.
    """
    global _client
    
    if _client is None:
        # Initialize MongoDB connection
        _client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URI)
        
    # Return the database instance
    return _client[settings.MONGODB_DATABASE]

# Helper functions for specific collections can be added here
async def get_ai_configs_collection():
    """Returns the AI provider configurations collection"""
    db = await get_db_client()
    return db.ai_provider_configs 