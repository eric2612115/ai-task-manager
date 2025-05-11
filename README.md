# 任务管理系统 (Task Management System)

一个智能化任务管理平台，集成敏捷开发工具、Git代码仓库管理和基于RAG技术的智能对话功能，旨在提升开发团队协作效率和知识共享。

## 项目愿景

该系统旨在解决开发团队在项目管理过程中面临的关键挑战：
1. **知识孤岛问题**：通过RAG技术和智能对话，让团队成员快速获取项目知识
2. **协作效率瓶颈**：利用AI辅助提升跨角色协作效率和代码质量
3. **上下文切换开销**：集成任务、代码和文档管理，减少工具切换成本
4. **项目洞察不足**：提供AI驱动的项目健康度分析和优化建议

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

### RAG系统 (检索增强生成)

基于先进的检索增强生成技术，提供智能代码和文档查询功能：

#### 实现目标
- **减少知识获取成本**：新团队成员可快速了解项目代码库
- **提高开发效率**：通过精准上下文辅助解决技术难题
- **促进知识共享**：将隐性知识转化为显性，便于传播
- **提升代码质量**：提供基于代码库的最佳实践建议

#### 特性
- **智能语义搜索**：基于向量数据库的语义搜索
- **多模型支持**：集成OpenAI、Anthropic、Google等多家LLM
- **代码特化处理**：使用CodeBERT优化代码理解能力
- **混合检索策略**：结合语义相似度和关键词匹配
- **内容分块优化**：针对代码和文档的智能分块策略
- **结果可视化**：高亮显示查询与内容的匹配部分

### AI提供商配置管理

用于管理和配置与系统集成的各种AI服务提供商：

#### 实现目标
- **灵活的AI集成**：支持多种AI服务提供商，增强系统适应性
- **安全的凭证管理**：安全存储和管理API密钥等敏感信息
- **用户个性化**：允许用户根据自己的偏好配置不同的AI服务
- **简化开发流程**：通过统一接口简化多种AI服务的接入

#### 特性
- **多提供商支持**：支持OpenAI、Google、Anthropic、Azure OpenAI和AWS Bedrock等
- **安全存储**：所有API密钥和敏感信息进行加密存储
- **动态模型列表**：为每个提供商提供可用模型的动态列表
- **活跃状态管理**：随时启用或禁用特定的AI配置
- **凭证掩码**：在UI和API响应中对敏感信息进行掩码处理

### 多用户对话系统

实时WebSocket通信框架，支持与项目代码库相关的智能对话：

#### 实现目标
- **降低沟通成本**：减少团队内部解释代码和文档的时间
- **保留决策上下文**：对话历史可作为决策依据被保存和引用
- **跨角色协作**：支持开发者、产品经理、测试人员等多角色交流
- **自动化执行**：从对话中直接执行任务修改和文档更新

#### 特性
- **会话管理**：创建、获取、更新和删除对话会话
- **消息处理**：实时消息发送、接收和编辑
- **断线重连机制**：网络中断时自动恢复对话状态
- **心跳检测**：确保连接稳定性
- **多设备同步**：同一用户的多个设备可实时同步消息
- **智能RAG模式**：LLM自动判断何时调用项目知识库
- **对话隐私控制**：支持私有、团队和公开三种对话模式

## 技术栈

- **Web框架**：FastAPI
- **数据库**：MongoDB（使用Motor作为异步驱动）
- **缓存与消息**：Redis
- **异步支持**：asyncio, aiohttp
- **身份验证**：JWT, OAuth
- **加密**：cryptography, bcrypt
- **向量数据库**：ChromaDB
- **嵌入模型**：CodeBERT, SentenceTransformer
- **WebSocket**：Starlette
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

# RAG相关配置
CHROMA_PERSIST_DIR="./chroma_db"
CHROMA_COLLECTION_CODE="code_embeddings"
CHROMA_COLLECTION_DOCS="doc_embeddings"
CODEBERT_MODEL="microsoft/codebert-base"
SENTENCE_TRANSFORMER_MODEL="all-MiniLM-L6-v2"

# AI提供商配置加密
ENCRYPTION_SECRET_KEY="secure-key-for-ai-provider-configs"
ENCRYPTION_SALT="secure-salt-for-key-derivation"

# 默认LLM配置
LLM_PROVIDER="openai"
OPENAI_API_KEY="your-openai-api-key"
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

系统提供RESTful API和WebSocket端点:

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
- 代码浏览：`/api/v1/code/`
- 文档管理：`/api/v1/docs/`

### AI与智能功能
- AI配置管理：`/api/v1/ai/config/providers/`
- 支持的AI提供商：`/api/v1/ai/config/supported-providers/`
- 嵌入管理：`/api/v1/rag/embeddings/`
- 语义搜索：`/api/v1/rag/search`
- RAG查询：`/api/v1/rag/query`
- RAG可视化：`/api/v1/rag/visualization/`
- 对话管理：`/api/v1/conversations/`
- WebSocket对话：`ws://localhost:8000/api/v1/ws/chat`

### 其他功能
- 搜索功能：`/api/v1/search/`
- 标签管理：`/api/v1/tags/`
- 附件管理：`/api/v1/attachments/`
- 事件系统：`/api/v1/events/`

## 使用AI配置系统

### 添加新的API凭证

```
POST /api/v1/ai/config/providers/
{
  "provider_name": "openai",
  "display_name": "开发团队OpenAI密钥",
  "api_key": "sk-your-api-key",
  "models": ["gpt-4o", "gpt-4-turbo"]
}
```

### 获取支持的AI服务提供商

```
GET /api/v1/ai/config/supported-providers/
```

## 使用RAG系统

### 初始化嵌入向量

```
POST /api/v1/rag/embeddings/generate/{repo_id}
{
  "force_regenerate": false
}
```

### 执行语义搜索

```
POST /api/v1/rag/search
{
  "query": "如何使用formatDate函数?",
  "repo_id": "your-repo-id",
  "limit": 5
}
```

### 执行RAG查询

```
POST /api/v1/rag/query
{
  "query": "如何使用formatDate函数?",
  "repo_id": "your-repo-id",
  "include_code": true,
  "include_docs": true
}
```

### 获取RAG可视化数据

```
GET /api/v1/rag/visualization/message/{message_id}
```

## 对话系统使用

### 创建会话

```
POST /api/v1/conversations/
{
  "title": "代码问答",
  "project_id": "project-id",
  "repo_id": "repo-id",
  "settings": {
    "model": "gemini-2.5-flash",
    "temperature": 0.7
  }
}
```

### WebSocket连接

```javascript
// 建立连接
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/chat');

// 发送消息
ws.send(JSON.stringify({
  "type": "message",
  "conversation_id": "conversation-id",
  "content": "如何实现用户认证功能?"
}));

// 接收消息
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};

// 实现断线重连
ws.onclose = () => {
  setTimeout(() => {
    const newWs = new WebSocket(
      `ws://localhost:8000/api/v1/ws/chat?reconnect_token=${reconnectToken}`
    );
  }, 1000);
};
```

## 未来发展计划

- **AI辅助任务创建**：根据对话自动创建和分配任务
- **代码质量分析与建议**：AI驱动的代码审查和优化
- **自动文档生成**：从代码和对话中提取关键信息生成文档
- **团队绩效分析**：基于活动数据的团队效能报告
- **跨项目知识图谱**：构建组织级代码知识网络
- **语音交互**：支持语音输入和输出
- **多语言支持**：自动翻译对话内容

## 贡献

欢迎提交Pull Requests和Issue报告！

## 许可证

MIT许可证
