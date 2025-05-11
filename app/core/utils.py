from bson import ObjectId
from datetime import datetime
from typing import Any, Dict, List, Union

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