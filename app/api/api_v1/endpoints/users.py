from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.status import HTTP_404_NOT_FOUND, HTTP_201_CREATED, HTTP_200_OK, HTTP_400_BAD_REQUEST
from bson import ObjectId
from pydantic import BaseModel, EmailStr

from app.db.mongodb import mongodb
from app.models.base_models import User

# 用户输入模型
class UserCreate(BaseModel):
    username: str
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None

class UserUpdate(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None

router = APIRouter()

@router.get("/", response_model=List[User])
async def get_users(
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    獲取所有用戶列表，用於前端指派任務時的下拉選單等。
    """
    query = {}
    
    if search:
        # 使用正則表達式進行模糊搜尋
        query["$or"] = [
            {"username": {"$regex": search, "$options": "i"}},
            {"full_name": {"$regex": search, "$options": "i"}}
        ]
    
    users_cursor = mongodb.db.users.find(query).skip(skip).limit(limit)
    users = await users_cursor.to_list(length=limit)
    
    return users

@router.get("/{user_id}", response_model=User)
async def get_user(user_id: str):
    """
    獲取單個用戶詳情
    """
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid user ID")
        
    user = await mongodb.db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")
    
    return user

@router.post("/", response_model=User, status_code=HTTP_201_CREATED)
async def create_user(user: UserCreate):
    """
    創建新用戶
    """
    # 检查用户名是否已存在
    existing_user = await mongodb.db.users.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # 如果提供了email，检查email是否已存在
    if user.email:
        existing_email = await mongodb.db.users.find_one({"email": user.email})
        if existing_email:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
    
    # 准备用户文档
    user_data = user.model_dump()
    
    # 插入数据库
    result = await mongodb.db.users.insert_one(user_data)
    
    # 获取创建的用户
    created_user = await mongodb.db.users.find_one({"_id": result.inserted_id})
    
    return created_user

@router.put("/{user_id}", response_model=User)
async def update_user(user_id: str, user: UserUpdate):
    """
    更新用户信息
    """
    # 检查用户是否存在
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid user ID")
    
    existing_user = await mongodb.db.users.find_one({"_id": ObjectId(user_id)})
    if not existing_user:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")
    
    # 准备更新数据，仅包含非空字段
    update_data = {k: v for k, v in user.model_dump().items() if v is not None}
    
    if not update_data:
        # 如果没有提供任何要更新的字段，直接返回现有用户
        return existing_user
    
    # 检查用户名唯一性（如果提供且排除当前用户）
    if "username" in update_data and update_data["username"] != existing_user["username"]:
        username_exists = await mongodb.db.users.find_one({
            "username": update_data["username"],
            "_id": {"$ne": ObjectId(user_id)}
        })
        if username_exists:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Username already taken by another user"
            )
    
    # 检查邮箱唯一性（如果提供且排除当前用户）
    if "email" in update_data and update_data["email"] != existing_user.get("email"):
        email_exists = await mongodb.db.users.find_one({
            "email": update_data["email"],
            "_id": {"$ne": ObjectId(user_id)}
        })
        if email_exists:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Email already taken by another user"
            )
    
    # 更新用户
    await mongodb.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_data}
    )
    
    # 返回更新后的用户
    updated_user = await mongodb.db.users.find_one({"_id": ObjectId(user_id)})
    
    return updated_user

@router.delete("/{user_id}", status_code=HTTP_200_OK)
async def delete_user(user_id: str):
    """
    删除用户
    """
    # 检查用户是否存在
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid user ID")
    
    user = await mongodb.db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")
    
    # 删除用户
    result = await mongodb.db.users.delete_one({"_id": ObjectId(user_id)})
    
    # 检查删除结果
    if result.deleted_count == 0:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Failed to delete user")
    
    return {"message": "User deleted successfully"}
