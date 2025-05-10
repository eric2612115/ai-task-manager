from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pymongo import ReturnDocument
from starlette.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR, HTTP_400_BAD_REQUEST
from bson import ObjectId

from app.db.mongodb import mongodb
from app.db.redis import redis_manager
from app.models.project_models import Project, ProjectCreate, ProjectUpdate
from app.services.activity_log_service import create_activity_log

router = APIRouter()

# 獲取當前用戶ID (暫時固定返回一個測試用戶ID)
async def get_current_user_id():
    # 實際應用中，應該從JWT令牌或session中獲取經過認證的用戶ID
    # 這里為了測試，返回一個固定的測試用戶ID
    return "507f1f77bcf86cd799439011"  # 模擬用戶ID

@router.post("/", response_model=Project, status_code=HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate = Body(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    創建新專案，並根據方法論（Kanban或Scrum）自動創建相應的默認看板和工作流程
    """
    now = datetime.utcnow()
    
    # 如果沒有提供工作流設置，創建默認工作流
    if not project_data.settings or not project_data.settings.task_status_workflow:
        default_workflow = [
            {"from_status": "Open", "to_status": "In Progress"},
            {"from_status": "In Progress", "to_status": "Resolved"},
            {"from_status": "Resolved", "to_status": "Closed"},
            {"from_status": "Closed", "to_status": "Open"},  # 允許重新打開
            {"from_status": "In Progress", "to_status": "Open"},  # 允許退回
            {"from_status": "Resolved", "to_status": "In Progress"}  # 允許重新處理
        ]
        
        default_statuses = [
            {"value": "Open", "label": "Open", "color": "#4287f5"},  # 蓝色
            {"value": "In Progress", "label": "In Progress", "color": "#f5a742"},  # 橙色
            {"value": "Resolved", "label": "Resolved", "color": "#42f572"},  # 绿色
            {"value": "Closed", "label": "Closed", "color": "#8c8c8c"}  # 灰色
        ]
        
        if not project_data.settings:
            from app.models.base_models import ProjectSettings, TaskStatus, StatusTransition
            
            # 將字典轉換為適當的模型
            status_transitions = [StatusTransition(**st) for st in default_workflow]
            task_statuses = [TaskStatus(**ts) for ts in default_statuses]
            
            project_data.settings = ProjectSettings(
                task_status_workflow=status_transitions,
                task_statuses=task_statuses,
                methodology=project_data.methodology  # 设置方法论
            )
        else:
            from app.models.base_models import TaskStatus, StatusTransition
            
            # 將字典轉換為適當的模型
            status_transitions = [StatusTransition(**st) for st in default_workflow]
            task_statuses = [TaskStatus(**ts) for ts in default_statuses]
            
            project_data.settings.task_status_workflow = status_transitions
            
            # 只有在用戶沒有提供自定義狀態時才設置默認狀態
            if not project_data.settings.task_statuses:
                project_data.settings.task_statuses = task_statuses
            
            # 确保设置方法论字段
            if not project_data.settings.methodology:
                project_data.settings.methodology = project_data.methodology
    
    # 構建新專案文檔
    project = {
        "name": project_data.name,
        "description": project_data.description,
        "methodology": project_data.methodology,  # 添加方法论字段
        "created_at": now,
        "updated_at": now,
        "members": [ObjectId(current_user_id)],  # 添加創建者為成員
        "settings": project_data.settings.model_dump() if project_data.settings else {}
    }
    
    # 插入新專案
    result = await mongodb.db.projects.insert_one(project)
    if not result.inserted_id:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project"
        )
    
    project_id = result.inserted_id
    
    # 根据方法论创建默认看板
    if project_data.methodology == "Kanban":
        # 创建看板式默认看板
        default_board = {
            "project_id": project_id,
            "name": "看板视图",
            "type": "Kanban",
            "columns": [
                {
                    "_id": ObjectId(),
                    "name": "Open",
                    "order": 1,
                    "status_mapping": ["Open"]
                },
                {
                    "_id": ObjectId(),
                    "name": "In Progress",
                    "order": 2,
                    "status_mapping": ["In Progress"]
                },
                {
                    "_id": ObjectId(),
                    "name": "Resolved",
                    "order": 3,
                    "status_mapping": ["Resolved"]
                },
                {
                    "_id": ObjectId(),
                    "name": "Closed",
                    "order": 4,
                    "status_mapping": ["Closed"]
                }
            ],
            "created_at": now,
            "updated_at": now
        }
        
        board_type = "Kanban"
        board_name = "看板视图"
    else:  # Scrum 方法论
        # 创建Scrum默认看板（产品待办列表）
        default_board = {
            "project_id": project_id,
            "name": "产品待办列表",
            "type": "Scrum",
            "columns": [
                {
                    "_id": ObjectId(),
                    "name": "待定",
                    "order": 1,
                    "status_mapping": ["Open"]
                },
                {
                    "_id": ObjectId(),
                    "name": "就绪",
                    "order": 2,
                    "status_mapping": ["Open"]
                },
                {
                    "_id": ObjectId(),
                    "name": "进行中",
                    "order": 3,
                    "status_mapping": ["In Progress"]
                },
                {
                    "_id": ObjectId(),
                    "name": "已完成",
                    "order": 4,
                    "status_mapping": ["Resolved", "Closed"]
                }
            ],
            "created_at": now,
            "updated_at": now
        }
        
        board_type = "Scrum"
        board_name = "产品待办列表"
    
    # 插入默認看板
    board_result = await mongodb.db.boards.insert_one(default_board)
    
    # 记录创建看板的活动日志
    await create_activity_log(
        user_id=current_user_id,
        action_type="board_created",
        target_type="board",
        target_id=str(board_result.inserted_id),
        project_id=str(project_id),
        details={
            "name": board_name,
            "type": board_type,
            "columns_count": len(default_board["columns"])
        }
    )
    
    # 如果是Scrum方法论，还需创建一个冲刺（Sprint）看板
    if project_data.methodology == "Scrum":
        sprint_board = {
            "project_id": project_id,
            "name": "冲刺看板",
            "type": "Sprint",
            "columns": [
                {
                    "_id": ObjectId(),
                    "name": "待开始",
                    "order": 1,
                    "status_mapping": ["Open"]
                },
                {
                    "_id": ObjectId(),
                    "name": "进行中",
                    "order": 2,
                    "status_mapping": ["In Progress"]
                },
                {
                    "_id": ObjectId(),
                    "name": "待验证",
                    "order": 3,
                    "status_mapping": ["Resolved"]
                },
                {
                    "_id": ObjectId(),
                    "name": "已完成",
                    "order": 4,
                    "status_mapping": ["Closed"]
                }
            ],
            "created_at": now,
            "updated_at": now
        }
        
        sprint_board_result = await mongodb.db.boards.insert_one(sprint_board)
        
        # 记录创建冲刺看板的活动日志
        await create_activity_log(
            user_id=current_user_id,
            action_type="board_created",
            target_type="board",
            target_id=str(sprint_board_result.inserted_id),
            project_id=str(project_id),
            details={
                "name": "冲刺看板",
                "type": "Sprint",
                "columns_count": 4
            }
        )
        
        # 发布冲刺看板创建事件
        await redis_manager.publish_event(
            channel=f"project:{str(project_id)}:events",
            event_type="board.created",
            data={
                "board_id": str(sprint_board_result.inserted_id),
                "name": "冲刺看板",
                "type": "Sprint",
                "is_default": True
            }
        )
    
    # 獲取插入後的完整專案文檔
    created_project = await mongodb.db.projects.find_one({"_id": project_id})
    
    # 記錄活動日誌
    await create_activity_log(
        user_id=current_user_id,
        action_type="project_created",
        target_type="project",
        target_id=str(project_id),
        project_id=str(project_id),
        details={
            "name": project_data.name,
            "methodology": project_data.methodology
        }
    )
    
    # 發布事件到Redis
    await redis_manager.publish_event(
        channel=f"global:events",
        event_type="project.created",
        data={
            "project_id": str(project_id),
            "name": project_data.name,
            "methodology": project_data.methodology,
            "has_default_board": True
        }
    )
    
    # 發布看板創建事件
    await redis_manager.publish_event(
        channel=f"project:{str(project_id)}:events",
        event_type="board.created",
        data={
            "board_id": str(board_result.inserted_id),
            "name": board_name,
            "type": board_type,
            "is_default": True
        }
    )
    
    return created_project

@router.get("/", response_model=List[Project])
async def get_projects(
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    獲取所有專案列表
    """
    query = {}
    
    # 在實際應用中，應根據用戶權限過濾專案
    # 這里僅做示範，返回用戶參與的所有專案
    # query["members"] = ObjectId(current_user_id)
    
    if search:
        # 使用文本搜尋（需要在MongoDB中配置文本索引）
        query["$text"] = {"$search": search}
    
    # 獲取專案列表
    projects_cursor = mongodb.db.projects.find(query).skip(skip).limit(limit)
    projects = await projects_cursor.to_list(length=limit)
    
    return projects

@router.get("/{project_id}", response_model=Project)
async def get_project(
    project_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    獲取單個專案詳情
    """
    try:
        project = await mongodb.db.projects.find_one({"_id": ObjectId(project_id)})
    except Exception:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Invalid project ID format")
    
    if not project:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Project not found")
    
    # 在實際應用中，應檢查用戶是否有權限訪問此專案
    # if ObjectId(current_user_id) not in project.get("members", []):
    #     raise HTTPException(status_code=403, detail="You don't have access to this project")
    
    return project

@router.put("/{project_id}", response_model=Project)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate = Body(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    更新專案資訊，包括方法論（如需要更改）
    """
    try:
        project_obj_id = ObjectId(project_id)
    except:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid project ID format")
    
    # 獲取當前專案
    project = await mongodb.db.projects.find_one({"_id": project_obj_id})
    if not project:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Project not found")
    
    # 檢查當前用戶是否有權限更新該專案
    # 實際應用中，應該檢查用戶是否是專案成員或管理員
    # if str(current_user_id) not in [str(member) for member in project.get("members", [])]:
    #     raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="You don't have permission to update this project")
    
    update_data = {}
    
    # 更新基本字段
    if project_data.name is not None:
        update_data["name"] = project_data.name
    
    if project_data.description is not None:
        update_data["description"] = project_data.description
    
    # 更新方法论字段
    if project_data.methodology is not None:
        update_data["methodology"] = project_data.methodology
        
        # 如果更新了方法论，也要更新设置中的方法论字段
        if "settings" not in update_data:
            update_data["settings"] = project.get("settings", {})
        update_data["settings"]["methodology"] = project_data.methodology
    
    # 更新設置
    if project_data.settings is not None:
        # 如果只更新了部分设置，需要保留原有的设置
        current_settings = project.get("settings", {})
        
        # 处理任务状态工作流程
        if project_data.settings.task_status_workflow:
            new_workflow = [item.model_dump() for item in project_data.settings.task_status_workflow]
            current_settings["task_status_workflow"] = new_workflow
        
        # 处理任务状态
        if project_data.settings.task_statuses:
            new_statuses = [item.model_dump() for item in project_data.settings.task_statuses]
            current_settings["task_statuses"] = new_statuses
        
        # 如果更新了方法论，确保设置中也更新了方法论
        if project_data.methodology is not None:
            current_settings["methodology"] = project_data.methodology
        elif "methodology" in project_data.settings.model_dump():
            current_settings["methodology"] = project_data.settings.methodology
            # 同时更新项目的顶级方法论字段
            update_data["methodology"] = project_data.settings.methodology
        
        update_data["settings"] = current_settings
    
    # 如果沒有需要更新的字段，直接返回當前專案
    if not update_data:
        return project
    
    # 更新更新時間
    update_data["updated_at"] = datetime.utcnow()
    
    # 執行更新
    update_result = await mongodb.db.projects.update_one(
        {"_id": project_obj_id},
        {"$set": update_data}
    )
    
    if update_result.modified_count == 0:
        # 可能因為嘗試設置相同的值，導致沒有實際更新
        pass
    
    # 獲取更新後的專案
    updated_project = await mongodb.db.projects.find_one({"_id": project_obj_id})
    
    # 記錄活動日誌
    changes = []
    if project_data.name is not None and project_data.name != project.get("name"):
        changes.append(f"name: '{project.get('name')}' -> '{project_data.name}'")
    
    if project_data.description is not None and project_data.description != project.get("description"):
        changes.append(f"description: changed")
    
    if project_data.methodology is not None and project_data.methodology != project.get("methodology"):
        changes.append(f"methodology: '{project.get('methodology')}' -> '{project_data.methodology}'")
    
    # 記錄設置變更
    if project_data.settings is not None:
        changes.append("settings: updated")
    
    if changes:
        await create_activity_log(
            user_id=current_user_id,
            action_type="project_updated",
            target_type="project",
            target_id=project_id,
            project_id=project_id,
            details={"changes": ", ".join(changes)}
        )
    
    # 發布事件到Redis
    await redis_manager.publish_event(
        channel=f"project:{project_id}:events",
        event_type="project.updated",
        data={
            "project_id": project_id,
            "name": updated_project.get("name"),
            "changes": changes
        }
    )
    
    return updated_project

@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    刪除專案及其所有相關數據 (任務, 評論, 衝刺, 看板, 關係, 附件元信息和實際檔案, 活動日誌, 通知)
    """
    try:
        # 確認專案存在
        project = await mongodb.db.projects.find_one({"_id": ObjectId(project_id)})
        if not project:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Project not found")
        
        # 在實際應用中，應檢查用戶是否有權限刪除此專案
        
        # 移除事务，直接执行删除操作
        # 获取项目相关的所有任务ID
        project_task_ids = []
        async for task in mongodb.db.tasks.find({"project_id": ObjectId(project_id)}, {"_id": 1}):
            project_task_ids.append(task["_id"])
        
        # 创建项目ID的查询条件
        project_task_ids_query = {"project_id": ObjectId(project_id)}
        
        # 删除项目的所有任务
        await mongodb.db.tasks.delete_many(project_task_ids_query)
        
        # 删除项目的所有冲刺
        await mongodb.db.sprints.delete_many({"project_id": ObjectId(project_id)})
        
        # 删除项目的所有看板
        await mongodb.db.boards.delete_many({"project_id": ObjectId(project_id)})
        
        # 获取与任务相关的评论ID和附件ID之前，确保有任务ID列表
        if project_task_ids:
            # 删除项目的所有关系
            await mongodb.db.relationships.delete_many({
                "$or": [
                    {"source_task_id": {"$in": project_task_ids}},
                    {"target_task_id": {"$in": project_task_ids}}
                ]
            })
            
            # 删除项目的所有任务评论
            comment_ids = []
            async for comment in mongodb.db.comments.find({"task_id": {"$in": project_task_ids}}, {"_id": 1}):
                comment_ids.append(comment["_id"])
            
            if comment_ids:
                await mongodb.db.comments.delete_many({"_id": {"$in": comment_ids}})
            
            # 获取所有与项目关联的附件ID列表
            project_attachment_ids = []
            
            # 任务的附件
            for task_id in project_task_ids:
                async for attachment in mongodb.db.attachments.find({"attached_to_task": task_id}, {"_id": 1}):
                    project_attachment_ids.append(attachment["_id"])
            
            # 评论的附件
            for comment_id in comment_ids:
                async for attachment in mongodb.db.attachments.find({"attached_to_comment": comment_id}, {"_id": 1}):
                    project_attachment_ids.append(attachment["_id"])
            
            # 删除所有附件元信息
            if project_attachment_ids:
                await mongodb.db.attachments.delete_many({"_id": {"$in": project_attachment_ids}})
            
            # 删除项目相关的通知
            await mongodb.db.notifications.delete_many({
                "$or": [
                    {"target_type": "project", "target_id": ObjectId(project_id)},
                    {"target_type": "task", "target_id": {"$in": project_task_ids}}
                ]
            })
        
        # 删除项目的活动日志
        await mongodb.db.activity_logs.delete_many({"project_id": ObjectId(project_id)})
        
        # 最后删除项目本身
        await mongodb.db.projects.delete_one({"_id": ObjectId(project_id)})
        
        # 记录活动日志
        await create_activity_log(
            user_id=current_user_id,
            action_type="project_deleted",
            target_type="project",
            target_id=project_id,
            project_id=None,  # 项目已删除
            details={"name": project.get("name", "")}
        )
        
        # 发布事件到Redis
        await redis_manager.publish_event(
            channel="global:events",
            event_type="project.deleted",
            data={"project_id": project_id}
        )
        
        # 删除外部存储系统中的实际文件
        # 这里实现实际文件的删除逻辑
        # 通常会使用异步任务处理这部分
        
        return {"message": "Project deleted successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting project: {str(e)}"
        )
