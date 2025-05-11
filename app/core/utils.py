from bson import ObjectId
from datetime import datetime
from typing import Any, Dict, List, Union
from fastapi import HTTPException, Depends, Header, Query
import os
from typing import Optional

def serialize_mongodb_doc(doc: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    pass mongo_db_id to serialize_mongodb_doc to convert ObjectId to string
    """
    if doc is None:
        return None
    
    if isinstance(doc, list):
        return [serialize_mongodb_doc(item) for item in doc]
    
    if not isinstance(doc, dict):
        return doc
    
    result = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            result[k] = str(v)
        elif isinstance(v, datetime):
            result[k] = v.isoformat()
        elif isinstance(v, dict):
            result[k] = serialize_mongodb_doc(v)
        elif isinstance(v, list):
            result[k] = serialize_mongodb_doc(v)
        else:
            result[k] = v
    
    return result 

# 在开发/测试环境中可以使用这个常量作为默认用户ID
TEST_USER_ID = "507f1f77bcf86cd799439011"

async def get_current_user_id(
    authorization: Optional[str] = Header(None),
    test_mode: Optional[bool] = Query(None)
) -> str:
    """
    This is a placeholder authentication function.
    In a real environment, it would verify the token and extract user_id from it.
    For development and testing, it returns a test user ID.
    """
    # In development or test mode, return a test user ID
    if test_mode or os.getenv("ENVIRONMENT", "development") != "production":
        return TEST_USER_ID
    
    # In production, we would verify the token
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    try:
        # Here you would validate the token and extract the user ID
        # This is just a placeholder - replace with actual JWT verification
        if authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "")
            # In a real app: user_id = jwt.decode(token, SECRET_KEY)["sub"]
            user_id = TEST_USER_ID
            return user_id
        else:
            raise HTTPException(status_code=401, detail="Invalid authorization header format")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

# Additional utility functions can be added here 