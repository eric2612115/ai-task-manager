from fastapi import APIRouter

from app.api.api_v1.endpoints import users, projects, tasks, comments, sprints, boards, attachments, search, tags, events, activity_logs, relationships, notifications, git, code, docs, rag, websockets, conversations
from app.ai_configs.routers import router as ai_configs_router

api_router = APIRouter()

# 用戶相關路由
api_router.include_router(users.router, prefix="/users", tags=["users"])
# 專案相關路由
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
# 任務相關路由
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
# 評論相關路由
api_router.include_router(comments.router, prefix="/comments", tags=["comments"])
# 衝刺相關路由
api_router.include_router(sprints.router, prefix="/sprints", tags=["sprints"])
# 看板相關路由
api_router.include_router(boards.router, prefix="/boards", tags=["boards"])
# 附件相關路由
api_router.include_router(attachments.router, prefix="/attachments", tags=["attachments"])
# 搜尋相關路由
api_router.include_router(search.router, prefix="/search", tags=["search"])
# 標籤相關路由
api_router.include_router(tags.router, prefix="/tags", tags=["tags"])
# 事件相關路由（SSE）
api_router.include_router(events.router, prefix="/events", tags=["events"])
# 活動日誌相關路由
api_router.include_router(activity_logs.router, prefix="/activity_logs", tags=["activity_logs"])
# 關係相關路由
api_router.include_router(relationships.router, prefix="/relationships", tags=["relationships"])
# 通知相關路由
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])

# 添加Git仓库管理路由
api_router.include_router(git.router, prefix="/git", tags=["git"])

# 添加代码文件路由
api_router.include_router(code.router, prefix="/code", tags=["code"])

# 添加文档路由
api_router.include_router(docs.router, prefix="/project-docs", tags=["docs"])

# 添加RAG系统路由
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])

# 添加WebSocket路由
api_router.include_router(websockets.router, prefix="/ws", tags=["websockets"])

# 添加对话会话路由
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])

# 添加AI配置路由
api_router.include_router(ai_configs_router)
