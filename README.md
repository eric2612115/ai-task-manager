# 任务管理系统 (Task Management System)

基于FastAPI的任务管理系统后端，提供项目、任务、看板、冲刺等敏捷开发工具功能，同时支持GitHub和GitLab代码仓库的集成与管理。

## 系统概述

这是一个强大的任务管理系统后端，结合了两大核心功能：
1. **敏捷项目管理**：全功能敏捷开发工具，支持任务跟踪、看板、冲刺规划等
2. **Git代码仓库管理**：支持GitHub和GitLab集成，代码同步与浏览

该系统适用于需要将代码管理与任务管理紧密结合的开发团队，提供API端点供前端应用调用。

## 核心功能

### 敏捷项目管理
- **项目管理**：创建、配置及管理多个项目
- **任务跟踪**：创建、分配、更新和监控任务
- **看板功能**：拖放式任务管理界面
- **冲刺规划**：规划和跟踪开发冲刺
- **用户管理**：用户账户、权限和团队协作
- **评论系统**：在任务上添加讨论和评论
- **通知系统**：关键事件的实时通知
- **附件支持**：向任务添加文件附件
- **标签管理**：组织和分类任务
- **活动日志**：记录系统中的所有活动

### Git代码仓库管理
- **Git凭证管理**：支持GitHub和GitLab平台
- **代码仓库集成**：自动发现和同步仓库
- **代码浏览**：浏览仓库文件和内容
- **文档管理**：基于源代码生成和管理文档

## 技术栈

- **Web框架**：FastAPI
- **数据库**：MongoDB（使用Motor作为异步驱动）
- **缓存与消息**：Redis
- **异步支持**：asyncio, aiohttp
- **身份验证**：JWT, OAuth
- **加密**：cryptography, bcrypt
- **文档**：Markdown, OpenAPI

## 安装与配置

1. 克隆代码库
```bash
git clone <repository-url>
cd task_manager_server
```

2. 设置虚拟环境
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或在Windows上:
# .venv\Scripts\activate
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 配置环境变量
```bash
# 在.env文件中配置
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=task_manager_db
REDIS_URL=redis://localhost:6379
ENCRYPTION_KEY=your-secure-encryption-key
```

5. 启动服务器
```bash
uvicorn main:app --reload
```

6. 访问API文档
```
http://localhost:8000/api/v1/docs
```

## API概览

系统提供RESTful API端点，分为以下几类：

### 项目与任务管理
- 项目 CRUD：`/api/v1/projects/`
- 任务 CRUD：`/api/v1/tasks/`
- 冲刺管理：`/api/v1/sprints/`
- 看板管理：`/api/v1/boards/`
- 评论系统：`/api/v1/comments/`

### 用户与团队
- 用户管理：`/api/v1/users/`
- 通知系统：`/api/v1/notifications/`
- 活动日志：`/api/v1/activity_logs/`

### Git仓库管理
- 凭证管理：`/api/v1/git/credentials/`
- 仓库管理：`/api/v1/git/repos/`
  - 支持按项目(project_id)组织管理仓库
  - 可通过project_id参数过滤特定项目的仓库
- 代码浏览：`/api/v1/code/`
- 文档管理：`/api/v1/docs/`

### 其他功能
- 搜索功能：`/api/v1/search/`
- 标签管理：`/api/v1/tags/`
- 附件管理：`/api/v1/attachments/`
- 事件系统：`/api/v1/events/`

## 安全与性能

- 所有Git令牌使用Fernet加密存储
- API使用JWT进行身份验证和授权
- 异步架构确保高性能和可扩展性
- MongoDB和Redis为数据存储和缓存提供支持

## 开发计划

- AI辅助任务分析与文档生成
- 代码质量分析集成
- 更多Git平台支持（如Bitbucket）
- 高级报表和数据可视化
- 移动应用API扩展

## 贡献

欢迎提交Pull Requests和Issue报告！

## 许可证

[指定许可证类型]

## RAG 系統 (檢索增強生成)

本項目集成了強大的RAG（檢索增強生成）系統，支持對代碼庫和文檔進行語義搜索和智能問答。

### 特點

- 使用ChromaDB作為向量數據庫
- 使用CodeBERT處理代碼嵌入
- 使用SentenceTransformer處理文檔嵌入
- 支持多種LLM（OpenAI、Anthropic、Google）
- 高效的代碼和文檔分塊策略
- 多用戶WebSocket實時對話
- RAG結果可視化與高亮顯示

### 對話功能

系統提供基於WebSocket的實時對話功能，支持以下特性：

- 多用戶對話：支持多個用戶同時進行對話
- 會話管理：創建、獲取、更新和刪除對話會話
- 消息管理：發送、接收、編輯和刪除消息
- 斷線重連：自動處理網絡中斷並恢復對話狀態
- 實時更新：消息狀態變化即時推送
- RAG結果可視化：高亮顯示檢索結果與查詢的匹配部分

### RAG可視化

RAG可視化功能讓用戶能夠：

- 查看檢索到的代碼和文檔片段
- 觀察相關性得分和排名
- 高亮顯示查詢與內容的匹配部分
- 直接訪問源文件
- 分析不同類型文件的檢索分佈

### 環境配置

在`.env`文件中添加以下配置:

```
# ChromaDB 配置
CHROMA_PERSIST_DIR="./chroma_db"
CHROMA_COLLECTION_CODE="code_embeddings"
CHROMA_COLLECTION_DOCS="doc_embeddings"

# 模型配置
CODEBERT_MODEL="microsoft/codebert-base"
SENTENCE_TRANSFORMER_MODEL="all-MiniLM-L6-v2"

# LLM 配置
LLM_PROVIDER="openai"  # openai, anthropic, google
OPENAI_API_KEY="your-openai-api-key"
# 或者使用其他LLM提供商
# ANTHROPIC_API_KEY="your-anthropic-api-key"
# GOOGLE_API_KEY="your-google-api-key"
```

### 初始化向量數據庫

ChromaDB 數據庫文件會在首次使用 RAG 功能時自動創建。如果需要手動初始化數據庫，請按照以下步驟操作:

1. 確保已正確設置 `.env` 文件中的 `CHROMA_PERSIST_DIR` 變量
2. 創建數據庫目錄（如果不存在）:
   ```
   mkdir -p ./chroma_db
   ```
3. 使用 API 導入倉庫數據並生成嵌入:
   ```
   POST /api/v1/rag/embeddings/generate/{repo_id}
   {
     "repo_id": "your-repo-id",
     "force_regenerate": true
   }
   ```

注意: 向量數據庫文件 (`chroma_db/`) 不會被包含在 Git 倉庫中，每個環境需要獨立初始化。

### 使用方法

1. 首先為倉庫生成嵌入:
   ```
   POST /api/v1/rag/embeddings/generate/{repo_id}
   {
     "repo_id": "your-repo-id",
     "force_regenerate": false
   }
   ```

2. 檢查嵌入生成狀態:
   ```
   GET /api/v1/rag/embeddings/status/{repo_id}
   ```

3. 執行語義搜索:
   ```
   POST /api/v1/rag/search
   {
     "query": "如何使用formatDate函數?",
     "repo_id": "your-repo-id",
     "limit": 5
   }
   ```

4. 執行RAG查詢(生成回答):
   ```
   POST /api/v1/rag/query
   {
     "query": "如何使用formatDate函數?",
     "repo_id": "your-repo-id",
     "include_code": true,
     "include_docs": true
   }
   ```

5. 獲取RAG可視化數據:
   ```
   GET /api/v1/rag/visualization/message/{message_id}
   ```

6. 自定義高亮顯示:
   ```
   POST /api/v1/rag/visualization/highlight
   {
     "query": "如何使用formatDate函數?",
     "context": "代碼或文檔內容",
     "language": "javascript"
   }
   ```

7. 使用WebSocket連接進行對話:
   ```
   WebSocket: ws://localhost:8000/api/v1/ws/chat
   WebSocket: ws://localhost:8000/api/v1/ws/chat/{conversation_id}
   ```

8. 刪除倉庫嵌入:
   ```
   DELETE /api/v1/rag/embeddings/{repo_id}
   ```

### 已知限制

- 目前RAG查詢需要配置有效的LLM API密鑰
- 不支持的文件類型 (yaml, markdown, html) 將被跳過
- 大型代碼庫的嵌入生成可能需要較長時間
