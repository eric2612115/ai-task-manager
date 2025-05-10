# 任務管理系統 API 服務

這是一個基於 FastAPI、MongoDB 和 Redis 構建的任務管理系統後端 API 服務。

## 功能特性

- **專案管理**: 創建和管理多個專案
- **任務管理**: 詳細的任務跟踪，包括狀態、優先級、指派人等
- **衝刺管理**: 創建衝刺並將任務分配到衝刺
- **看板視圖**: 通過看板列和順序來管理任務
- **評論系統**: 在任務上添加和管理評論
- **附件支持**: 為任務和評論添加附件
- **標籤系統**: 為任務添加標籤以便分類和過濾
- **任務關係**: 建立任務之間的關係（阻擋、關聯、父子等）
- **工作流程**: 基於專案配置的任務狀態轉換規則
- **活動日誌**: 詳細記錄系統中的變更
- **通知系統**: 基於事件的應用內通知
- **全文搜索**: 搜索不同實體類型的內容
- **實時更新**: 通過 Server-Sent Events (SSE) 推送實時更新

## 技術棧

- **Python 3.13**: 核心編程語言
- **FastAPI**: Web 框架
- **Uvicorn**: ASGI 服務器
- **MongoDB**: 使用 Motor 非同步驅動訪問的文檔數據庫
- **Redis**: 用於 Pub/Sub 的消息代理
- **Pydantic**: 數據驗證和設置管理
- **Server-Sent Events (SSE)**: 實時事件推送

## 安裝與運行

### 兼容性說明

本項目建議使用 Python 3.10-3.12 版本。Python 3.13 目前部分依賴庫可能存在兼容性問題。

### 前提條件

- Python 3.13+
- MongoDB 8.0+
- Redis

### 步驟

1. 克隆倉庫:
   ```
   git clone <repository-url>
   cd task-manager-server
   ```

2. 創建虛擬環境並安裝依賴:
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows 上使用 .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. 配置環境變量 (可選):
   創建 `.env` 文件:
   ```
   MONGODB_URL=mongodb://localhost:27017
   MONGODB_DB_NAME=task_manager_db
   REDIS_URL=redis://localhost:6379/0
   UPLOAD_DIR=./uploads
   ```

4. 運行服務:
   ```
   uvicorn main:app --reload
   ```
   或使用提供的腳本:
   ```
   chmod +x run.sh
   ./run.sh
   ```

5. 訪問 API 文檔:
   - Swagger UI: http://localhost:8000/api/v1/docs
   - ReDoc: http://localhost:8000/api/v1/redoc

### 疑難排解

如果您在安裝依賴或啟動應用時遇到問題，可以嘗試以下方法：

1. **驗證環境設置**：
   ```
   # 激活虛擬環境
   source .venv/bin/activate
   
   # 運行測試腳本檢查依賴
   python test_setup.py
   ```

2. **依賴安裝問題**：
   - 如果某些包無法編譯，嘗試更新 pip：`pip install --upgrade pip`
   - 嘗試安裝預編譯的二進制包：`pip install --only-binary=:all: -r requirements.txt`

3. **uvicorn 命令找不到**：
   - 確保虛擬環境已激活
   - 使用 Python 模塊方式運行：`python -m uvicorn main:app --reload`

4. **MongoDB 或 Redis 連接問題**：
   - 確保服務已啟動
   - 檢查連接字符串和認證設置
   - 檢查網絡/防火牆設置

## API 端點概覽

- `/api/v1/projects/`: 專案管理
- `/api/v1/tasks/`: 任務管理
- `/api/v1/comments/`: 評論管理
- `/api/v1/sprints/`: 衝刺管理
- `/api/v1/boards/`: 看板管理
- `/api/v1/tags/`: 標籤管理
- `/api/v1/attachments/`: 附件管理
- `/api/v1/relationships/`: 任務關係管理
- `/api/v1/search/`: 全文搜索
- `/api/v1/events/`: SSE 實時事件
- `/api/v1/notifications/`: 通知管理
- `/api/v1/activity_logs/`: 活動日誌

## 數據模型

系統包含以下主要數據集合:

- `projects`: 專案定義和設置
- `users`: 用戶基本信息
- `tasks`: 任務及其詳細信息
- `comments`: 任務評論
- `sprints`: 衝刺定義和狀態
- `boards`: 看板和列定義
- `attachments`: 上傳文件的元信息
- `activity_logs`: 系統變更記錄
- `notifications`: 用戶通知
- `relationships`: 任務間的關係
- `tags`: 標籤及其使用統計

## 開發

### 項目結構

```
task_manager_server/
├── app/
│   ├── api/
│   │   └── api_v1/
│   │       ├── endpoints/        # API 端點
│   │       └── api.py            # API 路由註冊
│   ├── core/                     # 核心配置
│   ├── db/                       # 數據庫連接
│   ├── models/                   # Pydantic 模型
│   ├── services/                 # 業務服務
│   └── utils/                    # 工具函數
├── uploads/                      # 文件上傳目錄
├── .env                          # 環境變量
├── main.py                       # 應用入口
├── requirements.txt              # 依賴清單
└── run.sh                        # 運行腳本
```
