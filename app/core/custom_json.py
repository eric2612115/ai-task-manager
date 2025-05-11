import json
from bson import ObjectId
from datetime import datetime
from typing import Any

class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle MongoDB's ObjectId and datetime types"""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj) 