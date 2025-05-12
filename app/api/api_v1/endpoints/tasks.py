from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, File, UploadFile, Form
from pymongo import ReturnDocument
from starlette.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST, HTTP_409_CONFLICT, HTTP_500_INTERNAL_SERVER_ERROR
from bson import ObjectId
import os
import json
import asyncio

from app.db.mongodb import mongodb
from app.db.redis import redis_manager
from app.models.task_models import Task, TaskCreate, TaskUpdate, TaskMove
from app.models.other_models import ActivityLogEntry
from app.services.activity_log_service import create_activity_log, ACTIVITY_TYPES, TARGET_TYPES
from app.services.task_embedding_service import task_embedding_service
from app.services.notification_service import create_notification, NOTIFICATION_TYPES
from app.core.custom_json import CustomJSONEncoder
from app.api.api_v1.endpoints.relationships import validate_task_relationships, WORKING_STATUSES

router = APIRouter()

# 獲取當前用戶ID (暫時固定返回一個測試用戶ID)
async def get_current_user_id():
    # 實際應用中，應該從JWT令牌或session中獲取經過認證的用戶ID
    # 這里為了測試，返回一個固定的測試用戶ID
    return "507f1f77bcf86cd799439011"  # 模擬用戶ID

@router.post("/projects/{project_id}/tasks/", response_model=Task, status_code=HTTP_201_CREATED)
async def create_task(
    project_id: str = Path(...),
    task_data: TaskCreate = Body(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    在指定專案下創建新任務。
    """
    try:
        # 確認專案存在
        project = await mongodb.db.projects.find_one({"_id": ObjectId(project_id)})
        if not project:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Project not found")
        
        # 驗證引用的ID是否存在且關聯正確
        if task_data.assignee_id:
            user = await mongodb.db.users.find_one({"_id": ObjectId(task_data.assignee_id)})
            if not user:
                raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Assignee user not found")
        
        if task_data.sprint_id:
            sprint = await mongodb.db.sprints.find_one({
                "_id": ObjectId(task_data.sprint_id),
                "project_id": ObjectId(project_id)
            })
            if not sprint:
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST, 
                    detail="Sprint not found or not associated with the specified project"
                )
        
        if task_data.board_column_id:
            # 查詢包含此列的看板
            board = await mongodb.db.boards.find_one({
                "project_id": ObjectId(project_id),
                "columns._id": ObjectId(task_data.board_column_id)
            })
            if not board:
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST, 
                    detail="Board column not found or not associated with the specified project"
                )
        
        # 驗證狀態是否有效
        status_valid = False
        
        # 檢查看板列的狀態映射
        if task_data.board_column_id and 'board' in locals():
            for col in board.get("columns", []):
                if str(col["_id"]) == task_data.board_column_id and task_data.status in col.get("status_mapping", []):
                    status_valid = True
                    break
        
        # 如果不是通過看板列驗證的，檢查專案工作流程是否允許此起始狀態
        if not status_valid:
            # 查看專案的工作流程定義，檢查是否有以此狀態為起點的轉換
            workflow = project.get("settings", {}).get("task_status_workflow", [])
            for transition in workflow:
                if transition.get("from_status") == task_data.status:
                    status_valid = True
                    break
            
            # 如果沒有工作流程定義，那麼任何狀態都是有效的
            if not workflow:
                status_valid = True
        
        if not status_valid:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Invalid status '{task_data.status}' for this task"
            )
        
        now = datetime.utcnow()
        
        # 計算order_in_column（如果提供了board_column_id但未提供order_in_column）
        order_in_column = task_data.order_in_column
        if task_data.board_column_id and order_in_column is None:
            # 查找該列中最後一個任務的順序號
            last_task = await mongodb.db.tasks.find_one(
                {"board_column_id": ObjectId(task_data.board_column_id)},
                sort=[("order_in_column", -1)]
            )
            if last_task and "order_in_column" in last_task:
                order_in_column = last_task["order_in_column"] + 1.0
            else:
                order_in_column = 1.0  # 列中第一個任務
        
        # 處理標籤
        for tag_name in task_data.tags:
            # 查找標籤是否存在
            tag = await mongodb.db.tags.find_one({"name": tag_name})
            if tag:
                # 增加usage_count
                await mongodb.db.tags.update_one(
                    {"_id": tag["_id"]},
                    {"$inc": {"usage_count": 1}, "$set": {"updated_at": now}}
                )
            else:
                # 創建新標籤
                await mongodb.db.tags.insert_one({
                    "name": tag_name,
                    "usage_count": 1,
                    "created_at": now,
                    "updated_at": now
                })
        
        # 構建任務文檔
        task = {
            "project_id": ObjectId(project_id),
            "summary": task_data.summary,
            "description": task_data.description,
            "status": task_data.status,
            "priority": task_data.priority,
            "task_type": task_data.task_type,
            "assignee_id": ObjectId(task_data.assignee_id) if task_data.assignee_id else None,
            "reporter_id": ObjectId(current_user_id),
            "due_date": task_data.due_date,
            "sprint_id": ObjectId(task_data.sprint_id) if task_data.sprint_id else None,
            "board_column_id": ObjectId(task_data.board_column_id) if task_data.board_column_id else None,
            "order_in_column": order_in_column,
            "mermaid_syntax": task_data.mermaid_syntax,
            "tags": task_data.tags,
            "attachments": [],
            "created_at": now,
            "updated_at": now,
            "__v": 1  # 初始版本號
        }
        
        # 插入任務
        result = await mongodb.db.tasks.insert_one(task)
        if not result.inserted_id:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create task"
            )
        
        # 獲取插入後的完整任務文檔
        created_task = await mongodb.db.tasks.find_one({"_id": result.inserted_id})
        
        # 記錄活動日誌
        await create_activity_log(
            user_id=current_user_id,
            action_type="task_created",
            target_type="task",
            target_id=str(result.inserted_id),
            project_id=project_id,
            details={
                "summary": task_data.summary,
                "status": task_data.status
            }
        )
        
        # 異步生成任務嵌入向量
        asyncio.create_task(task_embedding_service.generate_task_embedding(
            task_id=str(result.inserted_id),
            summary=task_data.summary,
            description=task_data.description
        ))
        
        # 如果任務被指派了，創建通知
        if task_data.assignee_id:
            await mongodb.db.notifications.insert_one({
                "recipient_id": ObjectId(task_data.assignee_id),
                "sender_id": ObjectId(current_user_id),
                "type": "task_assigned_to_me",
                "message": f"你被指派了新任務：{task_data.summary}",
                "target_type": "task",
                "target_id": result.inserted_id,
                "is_read": False,
                "created_at": now
            })
            
            # 為被指派者發布實時事件
            await redis_manager.publish_event(
                channel=f"user:{task_data.assignee_id}:notifications",
                event_type="notification.created",
                data={
                    "type": "task_assigned_to_me",
                    "task_id": str(result.inserted_id),
                    "task_summary": task_data.summary
                }
            )
        
        # 發布事件到Redis
        await redis_manager.publish_event(
            channel=f"project:{project_id}:events",
            event_type="task.created",
            data={
                "task_id": str(result.inserted_id),
                "summary": task_data.summary,
                "status": task_data.status
            }
        )
        
        return created_task
        
    except Exception as e:
        if "task" in locals() and "tags" in task:
            # 如果發生錯誤，回滾標籤計數
            for tag_name in task["tags"]:
                await mongodb.db.tags.update_one(
                    {"name": tag_name},
                    {"$inc": {"usage_count": -1}}
                )
        
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating task: {str(e)}"
        )

@router.get("/projects/{project_id}/tasks/", response_model=List[Task])
async def get_project_tasks(
    project_id: str = Path(...),
    status: Optional[str] = None,
    assignee_id: Optional[str] = None,
    sprint_id: Optional[str] = None,
    board_id: Optional[str] = None,
    tag: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    current_user_id: str = Depends(get_current_user_id)
):
    """
    獲取指定專案下的任務列表，支援過濾、排序、分頁。
    """
    try:
        # 構建查詢條件
        query = {"project_id": ObjectId(project_id)}
        
        # 應用過濾條件
        if status:
            query["status"] = status
        
        if assignee_id:
            query["assignee_id"] = ObjectId(assignee_id)
        
        if sprint_id:
            query["sprint_id"] = ObjectId(sprint_id)
        
        if tag:
            query["tags"] = tag
            
        # 如果指定了board_id，需要獲取該看板下所有列的ID
        if board_id:
            board = await mongodb.db.boards.find_one({"_id": ObjectId(board_id)})
            if not board:
                raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Board not found")
            
            column_ids = [col["_id"] for col in board.get("columns", [])]
            if column_ids:
                query["board_column_id"] = {"$in": column_ids}
            else:
                # 如果看板沒有列，返回空列表
                return []
        
        # 決定排序方式
        sort_direction = -1 if sort_order.lower() == "desc" else 1
        sort_options = [(sort_by, sort_direction)]
        
        # 如果是按看板列和順序排序，添加附加的排序條件
        if sort_by == "order_in_column" and board_id:
            # 找出看板列的順序
            columns_order = {}
            for i, col in enumerate(board.get("columns", [])):
                columns_order[col["_id"]] = i
            
            # 自定義聚合管道以支持複雜排序
            pipeline = [
                {"$match": query},
                {"$addFields": {
                    "column_order": {
                        "$indexOfArray": [list(columns_order.keys()), "$board_column_id"]
                    }
                }},
                {"$sort": {"column_order": 1, "order_in_column": 1}},
                {"$skip": skip},
                {"$limit": limit}
            ]
            
            tasks_cursor = mongodb.db.tasks.aggregate(pipeline)
            tasks = [task async for task in tasks_cursor]
        else:
            # 普通查詢
            tasks_cursor = mongodb.db.tasks.find(query).sort(sort_options).skip(skip).limit(limit)
            tasks = await tasks_cursor.to_list(length=limit)
        
        return tasks
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching tasks: {str(e)}"
        )

@router.get("/{task_id}", response_model=Task)
async def get_task(
    task_id: str = Path(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    獲取單個任務詳情。
    """
    try:
        task = await mongodb.db.tasks.find_one({"_id": ObjectId(task_id)})
        if not task:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Task not found")
        
        return task
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching task: {str(e)}"
        )

@router.put("/{task_id}", response_model=Task)
async def update_task(
    task_id: str = Path(...),
    task_data: TaskUpdate = Body(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    更新任務信息，包括狀態、指派人、截止日期、標籤等，使用樂觀鎖定。
    """
    try:
        # 獲取當前任務
        task = await mongodb.db.tasks.find_one({"_id": ObjectId(task_id)})
        if not task:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Task not found")
        
        # 樂觀鎖定: 檢查版本號 (如果前端提供了版本號)
        task_version = getattr(task_data, "__v", None)
        if task_version is not None and task["__v"] != task_version:
            raise HTTPException(
                status_code=HTTP_409_CONFLICT,
                detail="Task has been modified by another user. Please refresh and try again."
            )
        
        # 獲取任務所屬專案
        project = await mongodb.db.projects.find_one({"_id": task["project_id"]})
        if not project:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Project not found")
        
        # 收集變更信息，用於活動日誌
        changes = {}
        update_data = {}
        
        # 狀態變更驗證
        if task_data.status is not None and task_data.status != task["status"]:
            # 檢查狀態轉換是否符合工作流程規則
            workflow = project.get("settings", {}).get("task_status_workflow", [])
            
            # 如果有定義工作流程，則必須遵循
            if workflow:
                status_transition_valid = any(
                    trans.get("from_status") == task["status"] and trans.get("to_status") == task_data.status
                    for trans in workflow
                )
                
                if not status_transition_valid:
                    raise HTTPException(
                        status_code=HTTP_400_BAD_REQUEST,
                        detail=f"Status transition from '{task['status']}' to '{task_data.status}' is not allowed by workflow rules"
                    )
            
            # 检查任务关系约束
            if task_data.status in WORKING_STATUSES:
                validation_result = await validate_task_relationships(task_id, task_data.status)
                if not validation_result["valid"]:
                    blocking_task_names = [task["summary"] for task in validation_result["blocking_tasks"]]
                    raise HTTPException(
                        status_code=HTTP_400_BAD_REQUEST,
                        detail=f"任务无法开始工作，因为它被以下任务阻塞: {', '.join(blocking_task_names)}"
                    )
            
            update_data["status"] = task_data.status
            changes["status"] = {"old": task["status"], "new": task_data.status}
        
        # 更新指派人
        if task_data.assignee_id is not None and str(task.get("assignee_id", "")) != task_data.assignee_id:
            if task_data.assignee_id:
                # 驗證新指派人存在
                user = await mongodb.db.users.find_one({"_id": ObjectId(task_data.assignee_id)})
                if not user:
                    raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Assignee user not found")
                
                update_data["assignee_id"] = ObjectId(task_data.assignee_id)
            else:
                update_data["assignee_id"] = None
                
            changes["assignee_id"] = {
                "old": str(task.get("assignee_id")) if task.get("assignee_id") else None,
                "new": task_data.assignee_id
            }
        
        # 更新衝刺
        if task_data.sprint_id is not None and str(task.get("sprint_id", "")) != task_data.sprint_id:
            if task_data.sprint_id:
                # 驗證新衝刺存在且屬於同一專案
                sprint = await mongodb.db.sprints.find_one({
                    "_id": ObjectId(task_data.sprint_id),
                    "project_id": task["project_id"]
                })
                if not sprint:
                    raise HTTPException(
                        status_code=HTTP_400_BAD_REQUEST,
                        detail="Sprint not found or not associated with the task's project"
                    )
                
                update_data["sprint_id"] = ObjectId(task_data.sprint_id)
            else:
                update_data["sprint_id"] = None
                
            changes["sprint_id"] = {
                "old": str(task.get("sprint_id")) if task.get("sprint_id") else None,
                "new": task_data.sprint_id
            }
        
        # 處理標籤更新
        if task_data.tags is not None:
            old_tags = set(task.get("tags", []))
            new_tags = set(task_data.tags)
            
            added_tags = new_tags - old_tags
            removed_tags = old_tags - new_tags
            
            # 更新標籤使用計數
            now = datetime.utcnow()
            
            # 增加新標籤的計數
            for tag_name in added_tags:
                # 查找標籤是否存在
                tag = await mongodb.db.tags.find_one({"name": tag_name})
                if tag:
                    # 增加usage_count
                    await mongodb.db.tags.update_one(
                        {"_id": tag["_id"]},
                        {"$inc": {"usage_count": 1}, "$set": {"updated_at": now}}
                    )
                else:
                    # 創建新標籤
                    await mongodb.db.tags.insert_one({
                        "name": tag_name,
                        "usage_count": 1,
                        "created_at": now,
                        "updated_at": now
                    })
            
            # 減少移除標籤的計數
            for tag_name in removed_tags:
                await mongodb.db.tags.update_one(
                    {"name": tag_name},
                    {"$inc": {"usage_count": -1}, "$set": {"updated_at": now}}
                )
            
            update_data["tags"] = list(new_tags)
            changes["tags"] = {"added": list(added_tags), "removed": list(removed_tags)}
        
        # 檢查並更新其他字段
        if task_data.summary is not None and task_data.summary != task["summary"]:
            update_data["summary"] = task_data.summary
            changes["summary"] = {"old": task["summary"], "new": task_data.summary}
        
        if task_data.description is not None and task_data.description != task.get("description"):
            update_data["description"] = task_data.description
            changes["description"] = {"old": task.get("description"), "new": task_data.description}
        
        if task_data.priority is not None and task_data.priority != task.get("priority"):
            update_data["priority"] = task_data.priority
            changes["priority"] = {"old": task.get("priority"), "new": task_data.priority}
        
        if task_data.task_type is not None and task_data.task_type != task.get("task_type"):
            update_data["task_type"] = task_data.task_type
            changes["task_type"] = {"old": task.get("task_type"), "new": task_data.task_type}
        
        if task_data.due_date is not None and task_data.due_date != task.get("due_date"):
            update_data["due_date"] = task_data.due_date
            changes["due_date"] = {
                "old": task.get("due_date").strftime("%Y-%m-%dT%H:%M:%S.%fZ") if task.get("due_date") else None,
                "new": task_data.due_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            }
        
        if task_data.mermaid_syntax is not None and task_data.mermaid_syntax != task.get("mermaid_syntax"):
            update_data["mermaid_syntax"] = task_data.mermaid_syntax
            changes["mermaid_syntax"] = {"old": task.get("mermaid_syntax"), "new": task_data.mermaid_syntax}
        
        # 如果沒有變更，直接返回現有任務
        if not update_data:
            return task
        
        # 更新時間戳和版本號
        now = datetime.utcnow()
        update_data["updated_at"] = now
        
        # 執行原子更新操作
        if task_version is not None:
            # 有版本号时，使用版本号作为条件
            updated_task = await mongodb.db.tasks.find_one_and_update(
                {"_id": ObjectId(task_id), "__v": task_version},
                {
                    "$set": update_data,
                    "$inc": {"__v": 1}  # 遞增版本號
                },
                return_document=ReturnDocument.AFTER
            )
        else:
            # 没有版本号时，仅使用ID作为条件
            updated_task = await mongodb.db.tasks.find_one_and_update(
                {"_id": ObjectId(task_id)},
                {
                    "$set": update_data,
                    "$inc": {"__v": 1}  # 仍然递增版本号
                },
                return_document=ReturnDocument.AFTER
            )
        
        # 如果沒有找到任務（版本號不匹配），拋出異常
        if not updated_task:
            raise HTTPException(
                status_code=HTTP_409_CONFLICT,
                detail="Task has been modified by another user. Please refresh and try again."
            )
        
        # 記錄活動日誌
        await create_activity_log(
            user_id=current_user_id,
            action_type="task_updated",
            target_type="task",
            target_id=task_id,
            project_id=str(task["project_id"]),
            details=changes
        )
        
        # 如果摘要或描述发生了变化，重新生成嵌入向量
        if "summary" in changes or "description" in changes:
            asyncio.create_task(task_embedding_service.generate_task_embedding(
                task_id=task_id,
                summary=updated_task["summary"],
                description=updated_task.get("description", "")
            ))
        
        # 處理特定更新類型的活動日誌和通知
        # 如果狀態改變，記錄狀態變更活動和通知
        if "status" in changes:
            await create_activity_log(
                user_id=current_user_id,
                action_type=ACTIVITY_TYPES["TASK_STATUS_CHANGED"],
                target_type=TARGET_TYPES["TASK"],
                target_id=task_id,
                project_id=str(task["project_id"]),
                details={"status": changes["status"]}
            )
            
            # 通知任務的報告人
            if str(task["reporter_id"]) != current_user_id:
                now = datetime.utcnow()
                await create_notification(
                    recipient_id=str(task["reporter_id"]),
                    notification_type=NOTIFICATION_TYPES["TASK_STATUS_CHANGED"],
                    target_type="task",
                    target_id=task_id,
                    sender_id=current_user_id,
                    template_vars={
                        "task_summary": task["summary"],
                        "old_status": changes["status"]["old"],
                        "new_status": changes["status"]["new"]
                    }
                )
                
                # 發布實時通知
                await redis_manager.publish_event(
                    channel=f"user:{str(task['reporter_id'])}:notifications",
                    event_type="notification.created",
                    data={
                        "type": NOTIFICATION_TYPES["TASK_STATUS_CHANGED"],
                        "task_id": task_id,
                        "task_summary": task["summary"],
                        "old_status": changes["status"]["old"],
                        "new_status": changes["status"]["new"]
                    }
                )
        
        # 如果指派人改變，記錄指派活動和通知新的指派人
        if "assignee_id" in changes and changes["assignee_id"]["new"]:
            await create_activity_log(
                user_id=current_user_id,
                action_type="user_assigned",
                target_type="task",
                target_id=task_id,
                project_id=str(task["project_id"]),
                details={"assignee_id": changes["assignee_id"]}
            )
            
            # 通知新的指派人
            await mongodb.db.notifications.insert_one({
                "recipient_id": ObjectId(changes["assignee_id"]["new"]),
                "sender_id": ObjectId(current_user_id),
                "type": "task_assigned_to_me",
                "message": f"你被指派了任務：{task['summary']}",
                "target_type": "task",
                "target_id": ObjectId(task_id),
                "is_read": False,
                "created_at": now
            })
            
            # 發布實時通知
            await redis_manager.publish_event(
                channel=f"user:{changes['assignee_id']['new']}:notifications",
                event_type="notification.created",
                data={
                    "type": "task_assigned_to_me",
                    "task_id": task_id,
                    "task_summary": task["summary"]
                }
            )
        
        # 發布任務更新事件
        await redis_manager.publish_event(
            channel=f"project:{str(task['project_id'])}:events",
            event_type="task.updated",
            data={
                "task_id": task_id,
                "updated_fields": list(changes.keys())
            }
        )
        
        await redis_manager.publish_event(
            channel=f"task:{task_id}:updates",
            event_type="task.updated",
            data={
                "task_id": task_id,
                "changes": changes
            }
        )
        
        return updated_task
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating task: {str(e)}"
        )

@router.put("/{task_id}/move", response_model=Task)
async def move_task(
    task_id: str = Path(...),
    move_data: TaskMove = Body(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    移動任務在看板上的位置（改變欄位和順序），並可能同時改變狀態，實現精確順序與併發處理。
    """
    try:
        # 獲取當前任務
        task = await mongodb.db.tasks.find_one({"_id": ObjectId(task_id)})
        if not task:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Task not found")
        
        # 樂觀鎖定: 檢查版本號 (如果前端提供了版本號)
        task_version = getattr(move_data, "__v", None)
        if task_version is not None and task["__v"] != task_version:
            raise HTTPException(
                status_code=HTTP_409_CONFLICT,
                detail="Task has been modified by another user. Please refresh and try again."
            )
        
        # 查詢目標列所屬的看板
        board = await mongodb.db.boards.find_one({"columns._id": ObjectId(move_data.target_column_id)})
        if not board:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Target board column not found")
        
        # 確保目標列屬於任務所屬專案
        if board["project_id"] != task["project_id"]:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST, 
                detail="Target board column does not belong to the task's project"
            )
        
        # 找到目標列
        target_column = None
        for col in board["columns"]:
            if col["_id"] == ObjectId(move_data.target_column_id):
                target_column = col
                break
        
        if not target_column:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Target board column not found")
        
        # 確定新的狀態（使用目標列的第一個狀態映射或保持原狀）
        new_status = target_column.get("status_mapping", [])[0] if target_column.get("status_mapping") else task["status"]
        
        # 如果狀態變更，驗證是否符合工作流程規則
        if new_status != task["status"]:
            # 獲取任務所屬專案
            project = await mongodb.db.projects.find_one({"_id": task["project_id"]})
            if not project:
                raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Project not found")
            
            # 檢查狀態轉換是否符合工作流程規則
            workflow = project.get("settings", {}).get("task_status_workflow", [])
            
            # 如果有定義工作流程，則必須遵循
            if workflow:
                status_transition_valid = any(
                    trans.get("from_status") == task["status"] and trans.get("to_status") == new_status
                    for trans in workflow
                )
                
                if not status_transition_valid:
                    raise HTTPException(
                        status_code=HTTP_400_BAD_REQUEST,
                        detail=f"Status transition from '{task['status']}' to '{new_status}' is not allowed by workflow rules"
                    )
                    
            # 检查任务关系约束
            if new_status in WORKING_STATUSES:
                validation_result = await validate_task_relationships(task_id, new_status)
                if not validation_result["valid"]:
                    blocking_task_names = [task["summary"] for task in validation_result["blocking_tasks"]]
                    raise HTTPException(
                        status_code=HTTP_400_BAD_REQUEST,
                        detail=f"任务无法移动至进行中状态，因为它被以下任务阻塞: {', '.join(blocking_task_names)}"
                    )
        
        # 收集變更信息，用於活動日誌
        changes = {}
        
        # 記錄欄位變更
        if str(task.get("board_column_id", "")) != move_data.target_column_id:
            changes["board_column_id"] = {
                "old": str(task.get("board_column_id")) if task.get("board_column_id") else None,
                "new": move_data.target_column_id
            }
        
        # 記錄順序變更
        if task.get("order_in_column") != move_data.position:
            changes["order_in_column"] = {
                "old": task.get("order_in_column"),
                "new": move_data.position
            }
        
        # 記錄狀態變更
        if task["status"] != new_status:
            changes["status"] = {
                "old": task["status"],
                "new": new_status
            }
        
        # 準備更新數據
        update_data = {
            "board_column_id": ObjectId(move_data.target_column_id),
            "order_in_column": move_data.position,
            "status": new_status,
            "updated_at": datetime.utcnow()
        }
        
        # 執行原子更新操作
        if task_version is not None:
            # 有版本号时，使用版本号作为条件
            updated_task = await mongodb.db.tasks.find_one_and_update(
                {"_id": ObjectId(task_id), "__v": task_version},
                {
                    "$set": update_data,
                    "$inc": {"__v": 1}  # 遞增版本號
                },
                return_document=ReturnDocument.AFTER
            )
        else:
            # 没有版本号时，仅使用ID作为条件
            updated_task = await mongodb.db.tasks.find_one_and_update(
                {"_id": ObjectId(task_id)},
                {
                    "$set": update_data,
                    "$inc": {"__v": 1}  # 仍然递增版本号
                },
                return_document=ReturnDocument.AFTER
            )
        
        # 如果沒有找到任務（版本號不匹配），拋出異常
        if not updated_task:
            raise HTTPException(
                status_code=HTTP_409_CONFLICT,
                detail="Task has been modified by another user. Please refresh and try again."
            )
        
        # 記錄活動日誌
        await create_activity_log(
            user_id=current_user_id,
            action_type="task_moved",
            target_type="task",
            target_id=task_id,
            project_id=str(task["project_id"]),
            details={
                "board_id": str(board["_id"]),
                "from_column": str(task.get("board_column_id", "")) if task.get("board_column_id") else None,
                "to_column": move_data.target_column_id,
                "new_position": move_data.position
            }
        )
        
        # 如果狀態改變，記錄狀態變更活動和通知
        if "status" in changes:
            await create_activity_log(
                user_id=current_user_id,
                action_type=ACTIVITY_TYPES["TASK_STATUS_CHANGED"],
                target_type=TARGET_TYPES["TASK"],
                target_id=task_id,
                project_id=str(task["project_id"]),
                details={"status": changes["status"]}
            )
            
            # 通知任務的報告人
            if str(task["reporter_id"]) != current_user_id:
                now = datetime.utcnow()
                await create_notification(
                    recipient_id=str(task["reporter_id"]),
                    notification_type=NOTIFICATION_TYPES["TASK_STATUS_CHANGED"],
                    target_type="task",
                    target_id=task_id,
                    sender_id=current_user_id,
                    template_vars={
                        "task_summary": task["summary"],
                        "old_status": changes["status"]["old"],
                        "new_status": changes["status"]["new"]
                    }
                )
                
                # 發布實時通知
                await redis_manager.publish_event(
                    channel=f"user:{str(task['reporter_id'])}:notifications",
                    event_type="notification.created",
                    data={
                        "type": NOTIFICATION_TYPES["TASK_STATUS_CHANGED"],
                        "task_id": task_id,
                        "task_summary": task["summary"],
                        "old_status": changes["status"]["old"],
                        "new_status": changes["status"]["new"]
                    }
                )
        
        # 發布任務移動事件
        await redis_manager.publish_event(
            channel=f"project:{str(task['project_id'])}:events",
            event_type="task.moved",
            data={
                "task_id": task_id,
                "board_id": str(board["_id"]),
                "target_column_id": move_data.target_column_id,
                "position": move_data.position,
                "status": new_status
            }
        )
        
        return updated_task
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error moving task: {str(e)}"
        )

@router.delete("/{task_id}")
async def delete_task(
    task_id: str = Path(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    刪除任務及其所有關聯評論、附件和關係。
    """
    try:
        # 獲取任務信息
        task = await mongodb.db.tasks.find_one({"_id": ObjectId(task_id)})
        if not task:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Task not found")
        
        project_id = str(task["project_id"])
        task_summary = task.get("summary", "")
        
        # 移除事务，直接执行删除操作
        # 删除任务
        await mongodb.db.tasks.delete_one({"_id": ObjectId(task_id)})
        
        # 删除任务的评论
        await mongodb.db.comments.delete_many({"task_id": ObjectId(task_id)})
        
        # 删除任务的关系
        await mongodb.db.relationships.delete_many({
            "$or": [
                {"source_task_id": ObjectId(task_id)},
                {"target_task_id": ObjectId(task_id)}
            ]
        })
        
        # 获取任务的附件ID
        task_attachment_ids = []
        async for attachment in mongodb.db.attachments.find({"attached_to_task": ObjectId(task_id)}, {"_id": 1}):
            task_attachment_ids.append(attachment["_id"])
        
        # 获取任务评论的ID
        comment_ids = []
        async for comment in mongodb.db.comments.find({"task_id": ObjectId(task_id)}, {"_id": 1}):
            comment_ids.append(comment["_id"])
        
        # 获取评论的附件ID
        comment_attachment_ids = []
        for comment_id in comment_ids:
            async for attachment in mongodb.db.attachments.find({"attached_to_comment": comment_id}, {"_id": 1}):
                comment_attachment_ids.append(attachment["_id"])
        
        # 合并所有附件ID
        all_attachment_ids = task_attachment_ids + comment_attachment_ids
        
        # 在删除附件记录之前，获取它们的文件路径以便稍后删除文件
        attachment_paths = []
        for attachment_id in all_attachment_ids:
            attachment = await mongodb.db.attachments.find_one({"_id": attachment_id}, {"storage_path": 1})
            if attachment and "storage_path" in attachment:
                attachment_paths.append(attachment["storage_path"])
        
        # 删除附件记录
        if all_attachment_ids:
            await mongodb.db.attachments.delete_many({"_id": {"$in": all_attachment_ids}})
        
        # 处理标签使用计数
        for tag_name in task.get("tags", []):
            await mongodb.db.tags.update_one(
                {"name": tag_name},
                {"$inc": {"usage_count": -1}}
            )
        
        # 删除任务相关的通知
        await mongodb.db.notifications.delete_many({"target_type": "task", "target_id": ObjectId(task_id)})
        
        # 删除附件文件
        for file_path in attachment_paths:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Error removing file {file_path}: {e}")
        
        # 记录活动日志
        await create_activity_log(
            user_id=current_user_id,
            action_type="task_deleted",
            target_type="task",
            target_id=task_id,
            project_id=project_id,
            details={"summary": task_summary}
        )
        
        # 发布任务删除事件
        await redis_manager.publish_event(
            channel=f"project:{project_id}:events",
            event_type="task.deleted",
            data={"task_id": task_id}
        )
        
        return {"message": "Task deleted successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting task: {str(e)}"
        )

@router.get("/{task_id}/activity_log/", response_model=List[ActivityLogEntry])
async def get_task_activity_log(
    task_id: str = Path(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    獲取單個任務的活動日誌。
    """
    try:
        # 檢查任務是否存在
        task = await mongodb.db.tasks.find_one(
            {"_id": ObjectId(task_id)},
            {"_id": 1, "project_id": 1}
        )
        if not task:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Task not found")
        
        # 查詢活動日誌
        logs_cursor = mongodb.db.activity_logs.find(
            {"target_type": "task", "target_id": ObjectId(task_id)}
        ).sort([("timestamp", -1)]).skip(skip).limit(limit)
        
        logs = await logs_cursor.to_list(length=limit)
        
        return logs
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching task activity log: {str(e)}"
        )

@router.post("/projects/{project_id}/generate-embeddings")
async def generate_project_tasks_embeddings(
    project_id: str = Path(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    为项目中的所有任务生成嵌入向量。
    """
    try:
        # 确认项目存在
        project = await mongodb.db.projects.find_one({"_id": ObjectId(project_id)})
        if not project:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Project not found")
        
        # 异步生成嵌入
        results = await task_embedding_service.generate_all_tasks_embeddings(project_id=project_id)
        
        return {
            "success": True,
            "project_id": project_id,
            "results": results
        }
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating task embeddings: {str(e)}"
        )

@router.post("/generate-embeddings")
async def generate_all_tasks_embeddings(
    current_user_id: str = Depends(get_current_user_id)
):
    """
    为所有任务生成嵌入向量。
    """
    try:
        # 异步生成嵌入
        results = await task_embedding_service.generate_all_tasks_embeddings()
        
        return {
            "success": True,
            "results": results
        }
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating task embeddings: {str(e)}"
        )
