from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from pymongo import ReturnDocument
from starlette.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
from bson import ObjectId

from app.db.mongodb import mongodb
from app.db.redis import redis_manager
from app.models.board_models import Board, BoardCreate, BoardUpdate, BoardColumn, BoardColumnCreate, BoardColumnUpdate
from app.services.activity_log_service import create_activity_log

router = APIRouter()

# 獲取當前用戶ID (暫時固定返回一個測試用戶ID)
async def get_current_user_id():
    # 實際應用中，應該從JWT令牌或session中獲取經過認證的用戶ID
    # 這里為了測試，返回一個固定的測試用戶ID
    return "507f1f77bcf86cd799439011"  # 模擬用戶ID

@router.post("/projects/{project_id}/boards/", response_model=Board, status_code=HTTP_201_CREATED)
async def create_board(
    project_id: str = Path(...),
    board_data: BoardCreate = Body(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    在指定專案下創建新看板。
    """
    try:
        # 確認專案存在
        project = await mongodb.db.projects.find_one({"_id": ObjectId(project_id)})
        if not project:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Project not found")
        
        now = datetime.utcnow()
        
        # 處理看板列，給每個列生成 ObjectId
        columns = []
        for col in board_data.columns:
            columns.append({
                "_id": ObjectId(),
                "name": col.name,
                "order": col.order,
                "status_mapping": col.status_mapping
            })
        
        # 構建看板文檔
        board = {
            "project_id": ObjectId(project_id),
            "name": board_data.name,
            "type": board_data.type,
            "columns": columns,
            "created_at": now,
            "updated_at": now
        }
        
        # 插入看板
        result = await mongodb.db.boards.insert_one(board)
        if not result.inserted_id:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create board"
            )
        
        # 獲取插入後的完整看板文檔
        created_board = await mongodb.db.boards.find_one({"_id": result.inserted_id})
        
        # 記錄活動日誌
        await create_activity_log(
            user_id=current_user_id,
            action_type="board_created",
            target_type="board",
            target_id=str(result.inserted_id),
            project_id=project_id,
            details={
                "name": board_data.name,
                "type": board_data.type,
                "columns_count": len(columns)
            }
        )
        
        # 發布看板創建事件
        await redis_manager.publish_event(
            channel=f"project:{project_id}:events",
            event_type="board.created",
            data={
                "board_id": str(result.inserted_id),
                "name": board_data.name,
                "type": board_data.type
            }
        )
        
        return created_board
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating board: {str(e)}"
        )

@router.get("/projects/{project_id}/boards/", response_model=List[Board])
async def get_project_boards(
    project_id: str = Path(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    獲取指定專案下的所有看板列表。
    """
    try:
        # 確認專案存在
        project = await mongodb.db.projects.find_one({"_id": ObjectId(project_id)})
        if not project:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Project not found")
        
        # 查詢看板
        boards_cursor = mongodb.db.boards.find({"project_id": ObjectId(project_id)})
        boards = await boards_cursor.to_list(length=None)
        
        return boards
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching project boards: {str(e)}"
        )

@router.get("/{board_id}", response_model=Board)
async def get_board(
    board_id: str = Path(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    獲取單個看板詳情。
    """
    try:
        board = await mongodb.db.boards.find_one({"_id": ObjectId(board_id)})
        if not board:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Board not found")
        
        return board
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching board: {str(e)}"
        )

@router.put("/{board_id}", response_model=Board)
async def update_board(
    board_id: str = Path(...),
    board_data: BoardUpdate = Body(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    更新看板信息（名稱、類型、列定義）。
    """
    try:
        # 查找看板
        board = await mongodb.db.boards.find_one({"_id": ObjectId(board_id)})
        if not board:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Board not found")
        
        # 收集變更信息，用於活動日誌
        changes = {}
        update_data = {}
        
        # 檢查並更新名稱和類型
        if board_data.name is not None and board_data.name != board["name"]:
            update_data["name"] = board_data.name
            changes["name"] = {"old": board["name"], "new": board_data.name}
        
        if board_data.type is not None and board_data.type != board["type"]:
            update_data["type"] = board_data.type
            changes["type"] = {"old": board["type"], "new": board_data.type}
        
        # 更新列定義 (如果提供)
        columns_changed = False
        if board_data.columns is not None:
            new_columns = []
            existing_columns = {str(col["_id"]): col for col in board["columns"]}
            column_changes = {"added": [], "updated": [], "removed": []}
            
            # 追踪哪些列被更新使用了
            processed_column_ids = set()
            
            # 處理更新後的列表
            for col_data in board_data.columns:
                if col_data.id:  # 更新現有列
                    if col_data.id in processed_column_ids:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Duplicate column ID: {col_data.id}"
                        )
                    processed_column_ids.add(col_data.id)
                    
                    if col_data.id not in existing_columns:
                        raise HTTPException(
                            status_code=404,
                            detail=f"Column with ID {col_data.id} not found"
                        )
                        
                    # 獲取現有列
                    existing_col = existing_columns[col_data.id]
                    
                    # 創建更新後的列
                    updated_col = existing_col.copy()
                    col_change = {}
                    
                    # 更新列名稱
                    if col_data.name is not None and col_data.name != existing_col["name"]:
                        updated_col["name"] = col_data.name
                        col_change["name"] = {"old": existing_col["name"], "new": col_data.name}
                    
                    # 更新列順序
                    if col_data.order is not None and col_data.order != existing_col["order"]:
                        updated_col["order"] = col_data.order
                        col_change["order"] = {"old": existing_col["order"], "new": col_data.order}
                    
                    # 更新狀態映射
                    if col_data.status_mapping is not None and set(col_data.status_mapping) != set(existing_col["status_mapping"]):
                        updated_col["status_mapping"] = col_data.status_mapping
                        col_change["status_mapping"] = {
                            "old": existing_col["status_mapping"],
                            "new": col_data.status_mapping
                        }
                    
                    # 加入更新後的列
                    new_columns.append(updated_col)
                    
                    # 如果有變更，記錄變更
                    if col_change:
                        column_changes["updated"].append({
                            "id": col_data.id,
                            "name": updated_col["name"],
                            "changes": col_change
                        })
                        columns_changed = True
                else:  # 新增列
                    # 創建新列
                    new_col = {
                        "_id": ObjectId(),
                        "name": col_data.name,
                        "order": col_data.order,
                        "status_mapping": col_data.status_mapping or []
                    }
                    new_columns.append(new_col)
                    
                    # 記錄新增列
                    column_changes["added"].append({
                        "id": str(new_col["_id"]),
                        "name": new_col["name"]
                    })
                    columns_changed = True
            
            # 找出被刪除的列
            for col_id, col in existing_columns.items():
                if col_id not in processed_column_ids:
                    column_changes["removed"].append({
                        "id": col_id,
                        "name": col["name"]
                    })
                    columns_changed = True
            
            # 如果有列被刪除，需要處理相關任務
            if column_changes["removed"]:
                # 獲取被刪除的列ID列表
                removed_column_ids = [ObjectId(col["id"]) for col in column_changes["removed"]]
                
                # 將這些列中的任務更新為無列和無順序
                # 移除事务，直接执行数据库操作
                # 更新任务
                await mongodb.db.tasks.update_many(
                    {"board_column_id": {"$in": removed_column_ids}},
                    {"$set": {"board_column_id": None, "order_in_column": None}}
                )
                
                # 更新看板
                if new_columns:
                    update_data["columns"] = new_columns
                if update_data:
                    update_data["updated_at"] = datetime.utcnow()
                    
                await mongodb.db.boards.update_one(
                    {"_id": ObjectId(board_id)},
                    {"$set": update_data}
                )
            else:
                # 如果沒有列被刪除，直接更新看板
                if new_columns:
                    update_data["columns"] = new_columns
            
            # 記錄列變更
            if columns_changed:
                changes["columns"] = column_changes
        
        # 如果沒有變更，直接返回現有看板
        if not update_data and not columns_changed:
            return board
        
        # 如果有變更但未在事務中處理，執行更新
        if update_data and "columns" not in update_data or not columns_changed:
            update_data["updated_at"] = datetime.utcnow()
            
            # 執行更新
            await mongodb.db.boards.update_one(
                {"_id": ObjectId(board_id)},
                {"$set": update_data}
            )
        
        # 獲取更新後的看板
        updated_board = await mongodb.db.boards.find_one({"_id": ObjectId(board_id)})
        
        # 記錄活動日誌
        await create_activity_log(
            user_id=current_user_id,
            action_type="board_updated",
            target_type="board",
            target_id=board_id,
            project_id=str(board["project_id"]),
            details=changes
        )
        
        # 如果列定義有變更，記錄特定活動
        if columns_changed:
            await create_activity_log(
                user_id=current_user_id,
                action_type="board_columns_updated",
                target_type="board",
                target_id=board_id,
                project_id=str(board["project_id"]),
                details={"columns": changes.get("columns", {})}
            )
        
        # 發布看板更新事件
        await redis_manager.publish_event(
            channel=f"project:{str(board['project_id'])}:events",
            event_type="board.updated",
            data={
                "board_id": board_id,
                "updated_fields": list(changes.keys())
            }
        )
        
        return updated_board
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating board: {str(e)}"
        )

@router.delete("/{board_id}")
async def delete_board(
    board_id: str = Path(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    刪除看板，並處理該看板下任務的歸屬和狀態。
    """
    try:
        # 查找看板
        board = await mongodb.db.boards.find_one({"_id": ObjectId(board_id)})
        if not board:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Board not found")
        
        project_id = str(board["project_id"])
        board_name = board["name"]
        
        # 獲取看板下所有列的ID
        column_ids = [col["_id"] for col in board.get("columns", [])]
        
        # 使用事務刪除看板並更新關聯的任務
        async with await mongodb.client.start_session() as session:
            async with session.start_transaction():
                # 將所有屬於該看板列的任務的 board_column_id 和 order_in_column 設為 null
                if column_ids:
                    await mongodb.db.tasks.update_many(
                        {"board_column_id": {"$in": column_ids}},
                        {"$set": {"board_column_id": None, "order_in_column": None}},
                        session=session
                    )
                
                # 刪除看板
                await mongodb.db.boards.delete_one({"_id": ObjectId(board_id)}, session=session)
        
        # 記錄活動日誌
        await create_activity_log(
            user_id=current_user_id,
            action_type="board_deleted",
            target_type="board",
            target_id=board_id,
            project_id=project_id,
            details={"name": board_name}
        )
        
        # 發布看板刪除事件
        await redis_manager.publish_event(
            channel=f"project:{project_id}:events",
            event_type="board.deleted",
            data={
                "board_id": board_id,
                "name": board_name
            }
        )
        
        return {"message": "Board deleted successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting board: {str(e)}"
        )
