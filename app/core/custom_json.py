import json
from bson import ObjectId
from datetime import datetime
from typing import Any

class CustomJSONEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理MongoDB的ObjectId和datetime等特殊类型"""
    
    def default(self, obj: Any) -> Any:
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj) 