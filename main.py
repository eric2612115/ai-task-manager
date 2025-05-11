import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.encoders import jsonable_encoder
import json
import asyncio

from app.core.config import settings
from app.db.mongodb import mongodb
from app.db.redis import redis_manager
from app.api.api_v1.api import api_router
from app.core.custom_json import CustomJSONEncoder
from app.services.websocket_manager import connection_manager

# 全局任务列表
background_tasks = []

# 初始化環境或建立連接
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動時的操作
    global background_tasks
    try:
        # 連接到MongoDB
        print("Connecting to MongoDB...")
        await mongodb.connect_to_mongodb()
        print("MongoDB connection established")
        
        # 確保Redis連接可用
        print("Connecting to Redis...")
        await redis_manager.get_redis_connection()
        print("Redis connection established")
        
        # 启动WebSocket连接监控任务
        print("Starting WebSocket connection monitor...")
        monitor_task = asyncio.create_task(connection_manager.monitor_connections())
        background_tasks.append(monitor_task)
        print("WebSocket connection monitor started")
        
    except Exception as e:
        print(f"Error during startup: {e}")
        # 在真實環境中應考慮希望應用在此失敗時是否應該結束
        # 在開發環境中，我們允許應用繼續嘗試啟動
        print("Attempting to continue despite connection errors...")
    
    yield
    
    # 關閉時的操作
    try:
        # 取消所有后台任务
        print("Cancelling background tasks...")
        for task in background_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        background_tasks = []
            
        # 關閉MongoDB連接
        await mongodb.close_mongodb_connection()
        # 關閉Redis連接
        await redis_manager.close_redis_connection()
    except Exception as e:
        print(f"Error during shutdown: {e}")

# 创建自定义JSONResponse类，使用我们的CustomJSONEncoder
class CustomJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            cls=CustomJSONEncoder,
        ).encode("utf-8")

# 創建FastAPI應用
app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan,
    default_response_class=CustomJSONResponse
)

# 添加CORS中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "Authorization", "X-Total-Count"],
    max_age=86400,  # 预检请求结果缓存24小时
)

# 全局異常處理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"An unexpected error occurred: {str(exc)}"},
    )

# 添加路由
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# 根路由
@app.get("/")
async def root():
    # 檢查數據庫連接狀態
    mongodb_status = "connected"
    redis_status = "connected"
    
    try:
        # 將會執行一個簡單的數據庫操作來檢查連接狀態
        await mongodb.db.command({"ping": 1})
    except Exception as e:
        mongodb_status = f"disconnected: {str(e)}"
    
    try:
        # 檢查Redis連接
        redis_conn = await redis_manager.get_redis_connection()
        await redis_conn.ping()
    except Exception as e:
        redis_status = f"disconnected: {str(e)}"
    
    return {
        "message": "Welcome to the Task Management API",
        "version": "1.0.0",
        "docs": f"{settings.API_V1_PREFIX}/docs",
        "status": {
            "mongodb": mongodb_status,
            "redis": redis_status
        }
    }

# 健康檢查
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    try:
        print(f"Starting Task Management API server on port {os.getenv('PORT', '8000')}")
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT", "8000")),
            reload=settings.DEBUG
        )
    except Exception as e:
        print(f"Error starting server: {e}")
        print("\nTroubleshooting tips:")
        print(" - Make sure MongoDB and Redis are running")
        print(" - Check your Python version (3.10-3.12 recommended)")
        print(" - Run 'python test_setup.py' to verify dependencies")
        print(" - Make sure all dependencies are properly installed")
        import sys
        sys.exit(1)
