# 任務管理系統 API 文檔

此文檔詳細說明了任務管理系統的所有 API 端點、輸入、輸出和使用方式。

## 目錄

1. [基礎 URL](#基礎-url)
2. [通用端點](#通用端點)
   - [用戶](#用戶)
   - [搜尋](#搜尋)
   - [事件](#事件)
   - [標籤](#標籤)
3. [專案管理](#專案管理)
4. [任務管理](#任務管理)
5. [評論管理](#評論管理)
6. [衝刺管理](#衝刺管理)
7. [看板管理](#看板管理)
8. [附件管理](#附件管理)
9. [關係管理](#關係管理)
10. [活動日誌](#活動日誌)
11. [通知管理](#通知管理)
12. [Git倉庫管理](#git倉庫管理)
    - [凭证管理](#凭证管理) 
    - [仓库管理](#仓库管理)
    - [同步操作](#同步操作)
13. [代码文件管理](#代码文件管理)
14. [文档管理](#文档管理)
15. [RAG系统](#rag系统)
16. [AI 配置管理](#ai-配置管理)

## 基礎 URL

所有 API 請求都應以以下基礎 URL 開頭：

```
http://localhost:8000/api/v1
```

## 通用端點

### 用戶

#### 獲取所有用戶

```
GET /users/
```

查詢參數：
- `search` (可選): 按用戶名或全名模糊搜尋
- `skip` (可選): 分頁跳過數量，默認為 0
- `limit` (可選): 分頁限制數量，默認為 100，最大為 1000

響應：
```json
[
  {
    "id": "507f1f77bcf86cd799439011",
    "username": "testuser",
    "full_name": "Test User",
    "email": "test@example.com"
  }
]
```

#### 獲取單個用戶

```
GET /users/{user_id}
```

路徑參數：
- `user_id`: 用戶 ID

響應：
```json
{
  "id": "507f1f77bcf86cd799439011",
  "username": "testuser",
  "full_name": "Test User",
  "email": "test@example.com"
}
```

#### 創建用戶

```
POST /users/
```

請求體：
```json
{
  "username": "newuser",
  "full_name": "New User",
  "email": "newuser@example.com"
}
```

響應：
```json
{
  "id": "507f1f77bcf86cd799439012",
  "username": "newuser",
  "full_name": "New User",
  "email": "newuser@example.com"
}
```

#### 更新用戶

```
PUT /users/{user_id}
```

路徑參數：
- `user_id`: 用戶 ID

請求體：
```json
{
  "username": "updateduser",
  "full_name": "Updated User Name",
  "email": "updated@example.com"
}
```

注意：所有字段都是可選的，只有提供的字段才會被更新。

響應：
```json
{
  "id": "507f1f77bcf86cd799439011",
  "username": "updateduser",
  "full_name": "Updated User Name",
  "email": "updated@example.com"
}
```

#### 刪除用戶

```
DELETE /users/{user_id}
```

路徑參數：
- `user_id`: 用戶 ID

響應：
```json
{
  "message": "User deleted successfully"
}
```

### 搜尋

#### 全系統搜尋

```
GET /search/
```

查詢參數：
- `q`: 搜尋關鍵字（必填）
- `project_id` (可選): 限定在特定專案內搜尋
- `target_types` (可選): 限定搜尋的實體類型，例如: task, comment, project
- `skip` (可選): 分頁跳過數量，默認為 0
- `limit` (可選): 分頁限制數量，默認為 50，最大為 200

響應：
```json
[
  {
    "type": "task",
    "id": "60c72b2f9b1a8d001f3a0a1e",
    "score": 0.95,
    "highlight": "修復登入頁面的bug",
    "data": {
      "summary": "修復登入頁面的bug",
      "status": "In Progress",
      "project_id": "60c72b2f9b1a8d001f3a0a1d"
    }
  },
  {
    "type": "comment",
    "id": "60c72b2f9b1a8d001f3a0a1f",
    "score": 0.8,
    "highlight": "我已經檢查了代碼，問題出在...",
    "data": {
      "task_id": "60c72b2f9b1a8d001f3a0a1e",
      "author_id": "507f1f77bcf86cd799439011",
      "task_summary": "修復登入頁面的bug"
    }
  }
]
```

### 事件

#### SSE 事件流

```
GET /events/{user_id}
```

路徑參數：
- `user_id`: 接收事件的用戶 ID

查詢參數：
- `project_id` (可選): 限制接收特定專案的更新
- `task_id` (可選): 限制接收特定任務的更新

響應：
Server-Sent Events (SSE) 流，包括以下事件類型：
- `task.created`
- `task.updated`
- `task.deleted`
- `task.moved`
- `comment.created`
- `comment.updated`
- `comment.deleted`
- `sprint.created`
- `sprint.updated`
- `sprint.deleted`
- `board.created`
- `board.updated`
- `board.deleted`
- `notification.created`
- `attachment.uploaded`
- `attachment.deleted`

### 標籤

#### 獲取標籤列表

```
GET /tags/
```

查詢參數：
- `search` (可選): 按標籤名稱模糊搜尋
- `sort_by` (可選): 排序字段，例如: name, usage_count
- `sort_order` (可選): 排序順序，asc/desc
- `skip` (可選): 分頁跳過數量，默認為 0
- `limit` (可選): 分頁限制數量，默認為 100，最大為 500
- `project_id` (可選): 限定在特定專案內搜尋標籤

響應：
```json
[
  {
    "id": "60c72b2f9b1a8d001f3a0a20",
    "name": "bug",
    "usage_count": 5,
    "created_at": "2023-01-01T12:00:00Z",
    "updated_at": "2023-01-01T12:00:00Z"
  },
  {
    "id": "60c72b2f9b1a8d001f3a0a21",
    "name": "feature",
    "usage_count": 3,
    "created_at": "2023-01-01T12:00:00Z",
    "updated_at": "2023-01-01T12:00:00Z"
  }
]
```

## 專案管理

### 創建專案

```
POST /projects/
```

請求體：
```json
{
  "name": "新專案",
  "description": "這是一個新專案的描述",
  "settings": {
    "task_status_workflow": [
      {
        "from_status": "Open",
        "to_status": "In Progress"
      },
      {
        "from_status": "In Progress",
        "to_status": "Resolved"
      },
      {
        "from_status": "Resolved",
        "to_status": "Closed"
      }
    ],
    "task_statuses": [
      {
        "value": "Open",
        "label": "Open"
      },
      {
        "value": "In Progress",
        "label": "In Progress"
      },
      {
        "value": "Resolved",
        "label": "Resolved"
      },
      {
        "value": "Closed",
        "label": "Closed"
      }
    ]
  }
}
```

> **注意**: 創建專案時會自動創建默認看板 (包含 Open、In Progress、Resolved、Closed 四列) 和默認工作流程。
> 如果您沒有在請求中提供自定義的工作流程設置，系統將使用默認工作流程，允許任務在
> Open、In Progress、Resolved 和 Closed 四種狀態之間轉換。
> 您也可以通過 `task_statuses` 字段自定義任務狀態列表，每個狀態包含 `value` 和 `label` 兩個屬性。
> 您也可以自定義工作流程，如上面示例所示。

響應：
```json
{
  "id": "60c72b2f9b1a8d001f3a0a1d",
  "name": "新專案",
  "description": "這是一個新專案的描述",
  "created_at": "2023-01-01T12:00:00Z",
  "updated_at": "2023-01-01T12:00:00Z",
  "members": ["507f1f77bcf86cd799439011"],
  "settings": {
    "task_status_workflow": [
      {
        "from_status": "Open",
        "to_status": "In Progress"
      },
      {
        "from_status": "In Progress",
        "to_status": "Resolved"
      },
      {
        "from_status": "Resolved",
        "to_status": "Closed"
      }
    ],
    "task_statuses": [
      {
        "value": "Open",
        "label": "Open"
      },
      {
        "value": "In Progress",
        "label": "In Progress"
      },
      {
        "value": "Resolved",
        "label": "Resolved"
      },
      {
        "value": "Closed",
        "label": "Closed"
      }
    ]
  }
}
```

### 獲取專案列表

```
GET /projects/
```

查詢參數：
- `search` (可選): 按專案名稱或描述進行搜尋
- `skip` (可選): 分頁跳過數量，默認為 0
- `limit` (可選): 分頁限制數量，默認為 100，最大為 1000

響應：
```json
[
  {
    "id": "60c72b2f9b1a8d001f3a0a1d",
    "name": "新專案",
    "description": "這是一個新專案的描述",
    "created_at": "2023-01-01T12:00:00Z",
    "updated_at": "2023-01-01T12:00:00Z",
    "members": ["507f1f77bcf86cd799439011"],
    "settings": {
      "task_status_workflow": [
        {
          "from_status": "Open",
          "to_status": "In Progress"
        },
        {
          "from_status": "In Progress",
          "to_status": "Resolved"
        },
        {
          "from_status": "Resolved",
          "to_status": "Closed"
        }
      ],
      "task_statuses": [
        {
          "value": "Open",
          "label": "Open"
        },
        {
          "value": "In Progress",
          "label": "In Progress"
        },
        {
          "value": "Resolved",
          "label": "Resolved"
        },
        {
          "value": "Closed",
          "label": "Closed"
        }
      ]
    }
  }
]
```

### 獲取單個專案

```
GET /projects/{project_id}
```

路徑參數：
- `project_id`: 專案 ID

響應：
```json
{
  "id": "60c72b2f9b1a8d001f3a0a1d",
  "name": "新專案",
  "description": "這是一個新專案的描述",
  "created_at": "2023-01-01T12:00:00Z",
  "updated_at": "2023-01-01T12:00:00Z",
  "members": ["507f1f77bcf86cd799439011"],
  "settings": {
    "task_status_workflow": [
      {
        "from_status": "Open",
        "to_status": "In Progress"
      },
      {
        "from_status": "In Progress",
        "to_status": "Resolved"
      },
      {
        "from_status": "Resolved",
        "to_status": "Closed"
      }
    ],
    "task_statuses": [
      {
        "value": "Open",
        "label": "Open"
      },
      {
        "value": "In Progress",
        "label": "In Progress"
      },
      {
        "value": "Resolved",
        "label": "Resolved"
      },
      {
        "value": "Closed",
        "label": "Closed"
      }
    ]
  }
}
```

### 更新專案

```
PUT /projects/{project_id}
```

路徑參數：
- `project_id`: 專案 ID

請求體：
```json
{
  "name": "更新後的專案名稱",
  "description": "更新後的專案描述",
  "settings": {
    "task_status_workflow": [
      {
        "from_status": "Open",
        "to_status": "In Progress"
      },
      {
        "from_status": "In Progress",
        "to_status": "Testing"
      },
      {
        "from_status": "Testing",
        "to_status": "Resolved"
      },
      {
        "from_status": "Resolved",
        "to_status": "Closed"
      }
    ]
  }
}
```

注意：所有字段都是可選的，只有提供的字段才會被更新。

響應：
```json
{
  "id": "60c72b2f9b1a8d001f3a0a1d",
  "name": "更新後的專案名稱",
  "description": "更新後的專案描述",
  "created_at": "2023-01-01T12:00:00Z",
  "updated_at": "2023-01-02T12:00:00Z",
  "members": ["507f1f77bcf86cd799439011"],
  "settings": {
    "task_status_workflow": [
      {
        "from_status": "Open",
        "to_status": "In Progress"
      },
      {
        "from_status": "In Progress",
        "to_status": "Testing"
      },
      {
        "from_status": "Testing",
        "to_status": "Resolved"
      },
      {
        "from_status": "Resolved",
        "to_status": "Closed"
      }
    ]
  }
}
```

### 刪除專案

```
DELETE /projects/{project_id}
```

路徑參數：
- `project_id`: 專案 ID

響應：
```json
{
  "message": "Project deleted successfully",
  "deleted_project_id": "60c72b2f9b1a8d001f3a0a1d"
}
```

## 任務管理

### 創建任務

```
POST /tasks/projects/{project_id}/tasks/
```

路徑參數：
- `project_id`: 專案 ID

請求體：
```json
{
  "summary": "修復登入頁面的bug",
  "description": "用戶報告當輸入特殊符號時登入頁面會崩潰",
  "status": "Open",
  "priority": "High",
  "task_type": "Bug",
  "assignee_id": "507f1f77bcf86cd799439011",
  "due_date": "2023-02-01T00:00:00Z",
  "sprint_id": "60c72b2f9b1a8d001f3a0a25",
  "board_column_id": "60c72b2f9b1a8d001f3a0a2a",
  "order_in_column": 1.0,
  "mermaid_syntax": null,
  "tags": ["bug", "login"]
}
```

響應：
```json
{
  "id": "60c72b2f9b1a8d001f3a0a1e",
  "project_id": "60c72b2f9b1a8d001f3a0a1d",
  "summary": "修復登入頁面的bug",
  "description": "用戶報告當輸入特殊符號時登入頁面會崩潰",
  "status": "Open",
  "priority": "High",
  "task_type": "Bug",
  "assignee_id": "507f1f77bcf86cd799439011",
  "reporter_id": "507f1f77bcf86cd799439011",
  "due_date": "2023-02-01T00:00:00Z",
  "sprint_id": "60c72b2f9b1a8d001f3a0a25",
  "board_column_id": "60c72b2f9b1a8d001f3a0a2a",
  "order_in_column": 1.0,
  "mermaid_syntax": null,
  "tags": ["bug", "login"],
  "attachments": [],
  "created_at": "2023-01-01T12:00:00Z",
  "updated_at": "2023-01-01T12:00:00Z",
  "__v": 1
}
```

### 獲取專案任務列表

```
GET /tasks/projects/{project_id}/tasks/
```

路徑參數：
- `project_id`: 專案 ID

查詢參數：
- `status` (可選): 過濾特定狀態的任務
- `assignee_id` (可選): 過濾指派給特定用戶的任務
- `sprint_id` (可選): 過濾屬於特定衝刺的任務
- `board_id` (可選): 過濾特定看板上的任務
- `tag` (可選): 過濾含有特定標籤的任務
- `skip` (可選): 分頁跳過數量，默認為 0
- `limit` (可選): 分頁限制數量，默認為 100，最大為 1000
- `sort_by` (可選): 排序字段，默認為 "created_at"
- `sort_order` (可選): 排序順序，默認為 "desc"

響應：
```json
[
  {
    "id": "60c72b2f9b1a8d001f3a0a1e",
    "project_id": "60c72b2f9b1a8d001f3a0a1d",
    "summary": "修復登入頁面的bug",
    "description": "用戶報告當輸入特殊符號時登入頁面會崩潰",
    "status": "Open",
    "priority": "High",
    "task_type": "Bug",
    "assignee_id": "507f1f77bcf86cd799439011",
    "reporter_id": "507f1f77bcf86cd799439011",
    "due_date": "2023-02-01T00:00:00Z",
    "sprint_id": "60c72b2f9b1a8d001f3a0a25",
    "board_column_id": "60c72b2f9b1a8d001f3a0a2a",
    "order_in_column": 1.0,
    "mermaid_syntax": null,
    "tags": ["bug", "login"],
    "attachments": [],
    "created_at": "2023-01-01T12:00:00Z",
    "updated_at": "2023-01-01T12:00:00Z",
    "__v": 1
  }
]
```

### 獲取單個任務

```
GET /tasks/{task_id}
```

路徑參數：
- `task_id`: 任務 ID

響應：
```json
{
  "id": "60c72b2f9b1a8d001f3a0a1e",
  "project_id": "60c72b2f9b1a8d001f3a0a1d",
  "summary": "修復登入頁面的bug",
  "description": "用戶報告當輸入特殊符號時登入頁面會崩潰",
  "status": "Open",
  "priority": "High",
  "task_type": "Bug",
  "assignee_id": "507f1f77bcf86cd799439011",
  "reporter_id": "507f1f77bcf86cd799439011",
  "due_date": "2023-02-01T00:00:00Z",
  "sprint_id": "60c72b2f9b1a8d001f3a0a25",
  "board_column_id": "60c72b2f9b1a8d001f3a0a2a",
  "order_in_column": 1.0,
  "mermaid_syntax": null,
  "tags": ["bug", "login"],
  "attachments": [],
  "created_at": "2023-01-01T12:00:00Z",
  "updated_at": "2023-01-01T12:00:00Z",
  "__v": 1
}
```

### 更新任務

```
PUT /tasks/{task_id}
```

路徑參數：
- `task_id`: 任務 ID

請求體：
```json
{
  "summary": "更新後的任務摘要",
  "description": "更新後的任務描述",
  "status": "In Progress",
  "priority": "High",
  "task_type": "Bug",
  "assignee_id": "507f1f77bcf86cd799439011",
  "due_date": "2023-05-31T23:59:59Z",
  "sprint_id": "507f1f77bcf86cd799439020",
  "tags": ["前端", "緊急"]
}
```

**注意**：
1. 所有字段都是可選的，只有提供的字段才會被更新。
2. 狀態更新必須遵循專案設置中定義的工作流規則。例如，只能從"Open"變更為"In Progress"，而不能直接從"Open"變更為"Closed"。
3. 狀態名稱必須完全匹配專案中定義的狀態值，不能包含額外字符（如"In Progress-column"是無效的）。

響應HTTP狀態碼：
- `200`: 更新成功
- `400`: 如果狀態轉換違反了工作流規則
- `404`: 任務未找到
- `409`: 任務已被其他用戶修改（版本衝突）

響應：
```json
{
  "id": "507f1f77bcf86cd799439013",
  "project_id": "507f1f77bcf86cd799439012",
  "summary": "更新後的任務摘要",
  "description": "更新後的任務描述",
  "status": "In Progress",
  "priority": "High",
  "task_type": "Bug",
  "assignee_id": "507f1f77bcf86cd799439011",
  "reporter_id": "507f1f77bcf86cd799439010",
  "due_date": "2023-05-31T23:59:59Z",
  "sprint_id": "507f1f77bcf86cd799439020",
  "board_column_id": "507f1f77bcf86cd799439030",
  "order_in_column": 1.5,
  "tags": ["前端", "緊急"],
  "attachments": ["507f1f77bcf86cd799439040"],
  "created_at": "2023-05-01T10:00:00Z",
  "updated_at": "2023-05-02T15:30:00Z"
}
```

### 移動任務

```
PUT /tasks/{task_id}/move
```

路徑參數：
- `task_id`: 任務 ID

請求體：
```json
{
  "board_column_id": "60c72b2f9b1a8d001f3a0a2b",
  "order_in_column": 2.5
}
```

響應：
```json
{
  "id": "60c72b2f9b1a8d001f3a0a1e",
  "project_id": "60c72b2f9b1a8d001f3a0a1d",
  "summary": "修復登入頁面的驗證 bug",
  "description": "更新的描述",
  "status": "In Progress",
  "priority": "Critical",
  "task_type": "Bug",
  "assignee_id": "507f1f77bcf86cd799439012",
  "reporter_id": "507f1f77bcf86cd799439011",
  "due_date": "2023-02-15T00:00:00Z",
  "sprint_id": "60c72b2f9b1a8d001f3a0a26",
  "board_column_id": "60c72b2f9b1a8d001f3a0a2b",
  "order_in_column": 2.5,
  "mermaid_syntax": null,
  "tags": ["bug", "login", "validation"],
  "attachments": [],
  "created_at": "2023-01-01T12:00:00Z",
  "updated_at": "2023-01-02T12:30:00Z",
  "__v": 3
}
```

### 刪除任務

```
DELETE /tasks/{task_id}
```

路徑參數：
- `task_id`: 任務 ID

響應：
```json
{
  "message": "Task deleted successfully",
  "deleted_task_id": "60c72b2f9b1a8d001f3a0a1e"
}
```

### 獲取任務活動日誌

```
GET /tasks/{task_id}/activity_log/
```

路徑參數：
- `task_id`: 任務 ID

查詢參數：
- `skip` (可選): 分頁跳過數量，默認為 0
- `limit` (可選): 分頁限制數量，默認為 100，最大為 500

響應：
```json
[
  {
    "id": "60c72b2f9b1a8d001f3a0a30",
    "user_id": "507f1f77bcf86cd799439011",
    "action_type": "task_created",
    "target_type": "task",
    "target_id": "60c72b2f9b1a8d001f3a0a1e",
    "project_id": "60c72b2f9b1a8d001f3a0a1d",
    "details": {
      "summary": "修復登入頁面的bug",
      "status": "Open"
    },
    "created_at": "2023-01-01T12:00:00Z"
  },
  {
    "id": "60c72b2f9b1a8d001f3a0a31",
    "user_id": "507f1f77bcf86cd799439011",
    "action_type": "task_updated",
    "target_type": "task",
    "target_id": "60c72b2f9b1a8d001f3a0a1e",
    "project_id": "60c72b2f9b1a8d001f3a0a1d",
    "details": {
      "changed_fields": ["summary", "description", "status", "priority", "assignee_id", "due_date", "sprint_id", "tags"],
      "old_values": {
        "summary": "修復登入頁面的bug",
        "status": "Open",
        "priority": "High",
        "assignee_id": "507f1f77bcf86cd799439011"
      },
      "new_values": {
        "summary": "修復登入頁面的驗證 bug",
        "status": "In Progress",
        "priority": "Critical",
        "assignee_id": "507f1f77bcf86cd799439012"
      }
    },
    "created_at": "2023-01-02T12:00:00Z"
  }
]
```

## 評論管理

### 創建評論

```
POST /tasks/{task_id}/comments/
```

路徑參數：
- `task_id`: 任務 ID

請求體：
```json
{
  "content": "<p>我認為可以使用 OAuth 進行身份驗證，這樣會更安全。 @johnsmith</p>"
}
```

響應：
```json
{
  "id": "60c72b2f9b1a8d001f3a0a1f",
  "task_id": "60c72b2f9b1a8d001f3a0a1e",
  "author_id": "507f1f77bcf86cd799439011",
  "content": "<p>我認為可以使用 OAuth 進行身份驗證，這樣會更安全。 @johnsmith</p>",
  "attachments": [],
  "created_at": "2023-01-03T12:00:00Z",
  "updated_at": "2023-01-03T12:00:00Z"
}
```

### 獲取任務評論列表

```
GET /tasks/{task_id}/comments/
```

路徑參數：
- `task_id`: 任務 ID

響應：
```json
[
  {
    "id": "60c72b2f9b1a8d001f3a0a1f",
    "task_id": "60c72b2f9b1a8d001f3a0a1e",
    "author_id": "507f1f77bcf86cd799439011",
    "content": "<p>我認為可以使用 OAuth 進行身份驗證，這樣會更安全。 @johnsmith</p>",
    "attachments": [],
    "created_at": "2023-01-03T12:00:00Z",
    "updated_at": "2023-01-03T12:00:00Z"
  }
]
```

### 更新評論

```
PUT /comments/{comment_id}
```

路徑參數：
- `comment_id`: 評論 ID

請求體：
```json
{
  "content": "<p>我認為可以使用 OAuth 2.0 進行身份驗證，這樣會更安全。 @johnsmith @maryjones</p>"
}
```

響應：
```json
{
  "id": "60c72b2f9b1a8d001f3a0a1f",
  "task_id": "60c72b2f9b1a8d001f3a0a1e",
  "author_id": "507f1f77bcf86cd799439011",
  "content": "<p>我認為可以使用 OAuth 2.0 進行身份驗證，這樣會更安全。 @johnsmith @maryjones</p>",
  "attachments": [],
  "created_at": "2023-01-03T12:00:00Z",
  "updated_at": "2023-01-03T12:30:00Z"
}
```

### 刪除評論

```
DELETE /comments/{comment_id}
```

路徑參數：
- `comment_id`: 評論 ID

響應：
```json
{
  "message": "Comment deleted successfully"
}
```

## 衝刺管理

### 創建衝刺

```
POST /sprints/projects/{project_id}/sprints/
```

路徑參數：
- `project_id`: 專案 ID

請求體：
```json
{
  "name": "Sprint 1",
  "start_date": "2023-01-01T00:00:00Z",
  "end_date": "2023-01-14T23:59:59Z",
  "state": "Active"
}
```

響應：
```json
{
  "id": "60c72b2f9b1a8d001f3a0a22",
  "project_id": "60c72b2f9b1a8d001f3a0a1d",
  "name": "Sprint 1",
  "start_date": "2023-01-01T00:00:00Z",
  "end_date": "2023-01-14T23:59:59Z",
  "state": "Active",
  "created_at": "2023-01-01T10:00:00Z",
  "updated_at": "2023-01-01T10:00:00Z"
}
```

### 獲取專案衝刺列表

```
GET /sprints/projects/{project_id}/sprints/
```

路徑參數：
- `project_id`: 專案 ID

查詢參數：
- `state` (可選): 按狀態過濾
- `skip` (可選): 分頁跳過數量，默認為 0
- `limit` (可選): 分頁限制數量，默認為 100

響應：
```json
[
  {
    "id": "60c72b2f9b1a8d001f3a0a22",
    "project_id": "60c72b2f9b1a8d001f3a0a1d",
    "name": "Sprint 1",
    "start_date": "2023-01-01T00:00:00Z",
    "end_date": "2023-01-14T23:59:59Z",
    "state": "Active",
    "created_at": "2023-01-01T10:00:00Z",
    "updated_at": "2023-01-01T10:00:00Z"
  }
]
```

### 獲取單個衝刺

```
GET /sprints/{sprint_id}
```

路徑參數：
- `sprint_id`: 衝刺 ID

響應：
```json
{
  "id": "60c72b2f9b1a8d001f3a0a22",
  "project_id": "60c72b2f9b1a8d001f3a0a1d",
  "name": "Sprint 1",
  "start_date": "2023-01-01T00:00:00Z",
  "end_date": "2023-01-14T23:59:59Z",
  "state": "Active",
  "created_at": "2023-01-01T10:00:00Z",
  "updated_at": "2023-01-01T10:00:00Z"
}
```

### 更新衝刺

```
PUT /sprints/{sprint_id}
```

路徑參數：
- `sprint_id`: 衝刺 ID

請求體：
```json
{
  "name": "Sprint 1 - Frontend",
  "start_date": "2023-01-01T00:00:00Z",
  "end_date": "2023-01-14T23:59:59Z",
  "state": "Completed"
}
```

響應：
```json
{
  "id": "60c72b2f9b1a8d001f3a0a22",
  "project_id": "60c72b2f9b1a8d001f3a0a1d",
  "name": "Sprint 1 - Frontend",
  "start_date": "2023-01-01T00:00:00Z",
  "end_date": "2023-01-14T23:59:59Z",
  "state": "Completed",
  "created_at": "2023-01-01T10:00:00Z",
  "updated_at": "2023-01-15T10:00:00Z"
}
```

### 刪除衝刺

```
DELETE /sprints/{sprint_id}
```

路徑參數：
- `sprint_id`: 衝刺 ID

響應：
```json
{
  "message": "Sprint deleted successfully"
}
```

## 看板管理

### 創建看板

```
POST /boards/projects/{project_id}/boards/
```

路徑參數：
- `project_id`: 專案 ID

請求體：
```json
{
  "name": "開發看板",
  "type": "Kanban",
  "columns": [
    {
      "name": "待處理",
      "order": 1,
      "status_mapping": ["Open", "Reopened"]
    },
    {
      "name": "進行中",
      "order": 2,
      "status_mapping": ["In Progress"]
    },
    {
      "name": "已解決",
      "order": 3,
      "status_mapping": ["Resolved"]
    },
    {
      "name": "已關閉",
      "order": 4,
      "status_mapping": ["Closed"]
    }
  ]
}
```

響應：
```json
{
  "id": "60c72b2f9b1a8d001f3a0a27",
  "project_id": "60c72b2f9b1a8d001f3a0a1d",
  "name": "開發看板",
  "type": "Kanban",
  "columns": [
    {
      "id": "60c72b2f9b1a8d001f3a0a23",
      "name": "待處理",
      "order": 1,
      "status_mapping": ["Open", "Reopened"]
    },
    {
      "id": "60c72b2f9b1a8d001f3a0a24",
      "name": "進行中",
      "order": 2,
      "status_mapping": ["In Progress"]
    },
    {
      "id": "60c72b2f9b1a8d001f3a0a28",
      "name": "已解決",
      "order": 3,
      "status_mapping": ["Resolved"]
    },
    {
      "id": "60c72b2f9b1a8d001f3a0a29",
      "name": "已關閉",
      "order": 4,
      "status_mapping": ["Closed"]
    }
  ],
  "created_at": "2023-01-01T11:00:00Z",
  "updated_at": "2023-01-01T11:00:00Z"
}
```

### 獲取專案看板列表

```
GET /boards/projects/{project_id}/boards/
```

路徑參數：
- `project_id`: 專案 ID

響應：
```json
[
  {
    "id": "60c72b2f9b1a8d001f3a0a27",
    "project_id": "60c72b2f9b1a8d001f3a0a1d",
    "name": "開發看板",
    "type": "Kanban",
    "columns": [...],
    "created_at": "2023-01-01T11:00:00Z",
    "updated_at": "2023-01-01T11:00:00Z"
  }
]
```

### 獲取單個看板

```
GET /boards/{board_id}
```

路徑參數：
- `board_id`: 看板 ID

響應：
```json
{
  "id": "60c72b2f9b1a8d001f3a0a27",
  "project_id": "60c72b2f9b1a8d001f3a0a1d",
  "name": "開發看板",
  "type": "Kanban",
  "columns": [...],
  "created_at": "2023-01-01T11:00:00Z",
  "updated_at": "2023-01-01T11:00:00Z"
}
```

### 更新看板

```
PUT /boards/{board_id}
```

路徑參數：
- `board_id`: 看板 ID

請求體：
```json
{
  "name": "開發與測試看板",
  "type": "Kanban",
  "columns": [
    {
      "id": "60c72b2f9b1a8d001f3a0a23",
      "name": "待處理",
      "order": 1,
      "status_mapping": ["Open", "Reopened"]
    },
    {
      "id": "60c72b2f9b1a8d001f3a0a24",
      "name": "進行中",
      "order": 2,
      "status_mapping": ["In Progress"]
    },
    {
      "id": "60c72b2f9b1a8d001f3a0a28",
      "name": "已解決",
      "order": 3,
      "status_mapping": ["Resolved"]
    },
    {
      "id": "60c72b2f9b1a8d001f3a0a29",
      "name": "已關閉",
      "order": 4,
      "status_mapping": ["Closed"]
    },
    {
      "name": "測試中",
      "order": 2.5,
      "status_mapping": ["Testing"]
    }
  ]
}
```

響應：
```json
{
  "id": "60c72b2f9b1a8d001f3a0a27",
  "project_id": "60c72b2f9b1a8d001f3a0a1d",
  "name": "開發與測試看板",
  "type": "Kanban",
  "columns": [...],
  "created_at": "2023-01-01T11:00:00Z",
  "updated_at": "2023-01-05T11:00:00Z"
}
```

### 刪除看板

```
DELETE /boards/{board_id}
```

路徑參數：
- `board_id`: 看板 ID

響應：
```json
{
  "message": "Board deleted successfully"
}
```

## 附件管理

### 獲取任務附件列表

```
GET /attachments/tasks/{task_id}/
```

路徑參數：
- `task_id`: 任務 ID

響應：
```json
[
  {
    "id": "60c72b2f9b1a8d001f3a0a30",
    "file_name": "login_screen_design.png",
    "file_size": 1024000,
    "content_type": "image/png",
    "storage_path": "uploads/abcdef123456.png",
    "url": "/uploads/abcdef123456.png",
    "uploaded_by": "507f1f77bcf86cd799439011",
    "uploaded_at": "2023-01-04T12:00:00Z",
    "attached_to_task": "60c72b2f9b1a8d001f3a0a1e",
    "attached_to_comment": null
  }
]
```

### 上傳任務附件

```
POST /attachments/tasks/{task_id}/
```

路徑參數：
- `task_id`: 任務 ID

請求體: `multipart/form-data`
- `file`: 文件

響應：
```json
{
  "id": "60c72b2f9b1a8d001f3a0a30",
  "file_name": "login_screen_design.png",
  "file_size": 1024000,
  "content_type": "image/png",
  "storage_path": "uploads/abcdef123456.png",
  "url": "/uploads/abcdef123456.png",
  "uploaded_by": "507f1f77bcf86cd799439011",
  "uploaded_at": "2023-01-04T12:00:00Z",
  "attached_to_task": "60c72b2f9b1a8d001f3a0a1e",
  "attached_to_comment": null
}
```

### 獲取評論附件列表

```
GET /attachments/comments/{comment_id}/
```

路徑參數：
- `comment_id`: 評論 ID

響應：
```json
[
  {
    "id": "60c72b2f9b1a8d001f3a0a31",
    "file_name": "oauth_diagram.png",
    "file_size": 512000,
    "content_type": "image/png",
    "storage_path": "uploads/ghijkl789012.png",
    "url": "/uploads/ghijkl789012.png",
    "uploaded_by": "507f1f77bcf86cd799439011",
    "uploaded_at": "2023-01-04T13:00:00Z",
    "attached_to_task": null,
    "attached_to_comment": "60c72b2f9b1a8d001f3a0a1f"
  }
]
```

### 上傳評論附件

```
POST /attachments/comments/{comment_id}/
```

路徑參數：
- `comment_id`: 評論 ID

請求體: `multipart/form-data`
- `file`: 文件

響應：
```json
{
  "id": "60c72b2f9b1a8d001f3a0a31",
  "file_name": "oauth_diagram.png",
  "file_size": 512000,
  "content_type": "image/png",
  "storage_path": "uploads/ghijkl789012.png",
  "url": "/uploads/ghijkl789012.png",
  "uploaded_by": "507f1f77bcf86cd799439011",
  "uploaded_at": "2023-01-04T13:00:00Z",
  "attached_to_task": null,
  "attached_to_comment": "60c72b2f9b1a8d001f3a0a1f"
}
```

### 刪除附件

```
DELETE /attachments/{attachment_id}
```

路徑參數：
- `attachment_id`: 附件 ID

響應：
```json
{
  "message": "Attachment deleted successfully"
}
```

### 獲取附件信息

```
GET /attachments/{attachment_id}
```

路徑參數：
- `attachment_id`: 附件 ID

響應：
```json
{
  "id": "60c72b2f9b1a8d001f3a0a31",
  "file_name": "oauth_diagram.png",
  "file_size": 512000,
  "content_type": "image/png",
  "storage_path": "uploads/ghijkl789012.png",
  "url": "/uploads/ghijkl789012.png",
  "uploaded_by": "507f1f77bcf86cd799439011",
  "uploaded_at": "2023-01-04T13:00:00Z",
  "attached_to_task": null,
  "attached_to_comment": "60c72b2f9b1a8d001f3a0a1f"
}
```

## 關係管理

### 創建任務關係

```
POST /relationships/tasks/{source_task_id}/relationships/
```

路徑參數：
- `source_task_id`: 源任務 ID

請求體：
```json
{
  "target_task_id": "60c72b2f9b1a8d001f3a0a32",
  "type": "blocks"
}
```

響應：
```json
{
  "id": "60c72b2f9b1a8d001f3a0a33",
  "project_id": "60c72b2f9b1a8d001f3a0a1d",
  "type": "blocks",
  "source_task_id": "60c72b2f9b1a8d001f3a0a1e",
  "target_task_id": "60c72b2f9b1a8d001f3a0a32",
  "created_by": "507f1f77bcf86cd799439011",
  "created_at": "2023-01-05T12:00:00Z"
}
```

### 獲取任務關係列表

```
GET /relationships/tasks/{task_id}/relationships/
```

路徑參數：
- `task_id`: 任務 ID

查詢參數：
- `type` (可選): 按關係類型過濾
- `direction` (可選): "outgoing", "incoming", 或 "both"，默認為 "outgoing"

響應：
```json
[
  {
    "id": "60c72b2f9b1a8d001f3a0a33",
    "project_id": "60c72b2f9b1a8d001f3a0a1d",
    "type": "blocks",
    "source_task_id": "60c72b2f9b1a8d001f3a0a1e",
    "target_task_id": "60c72b2f9b1a8d001f3a0a32",
    "created_by": "507f1f77bcf86cd799439011",
    "created_at": "2023-01-05T12:00:00Z"
  },
  {
    "id": "60c72b2f9b1a8d001f3a0a34",
    "project_id": "60c72b2f9b1a8d001f3a0a1d",
    "type": "relates_to",
    "source_task_id": "60c72b2f9b1a8d001f3a0a1e",
    "target_task_id": "60c72b2f9b1a8d001f3a0a35",
    "created_by": "507f1f77bcf86cd799439011",
    "created_at": "2023-01-05T12:30:00Z"
  }
]
```

### 刪除關係

```
DELETE /relationships/{relationship_id}
```

路徑參數：
- `relationship_id`: 關係 ID

響應：
```json
{
  "message": "Relationship deleted successfully"
}
```

## 活動日誌

### 獲取專案活動日誌

```
GET /activity_logs/projects/{project_id}
```

路徑參數：
- `project_id`: 專案 ID

查詢參數：
- `skip` (可選): 分頁跳過數量，默認為 0
- `limit` (可選): 分頁限制數量，默認為 100，最大為 1000
- `action_type` (可選): 按活動類型過濾
- `target_type` (可選): 按目標實體類型過濾
- `user_id` (可選): 按用戶過濾

響應：
```json
[
  {
    "id": "60c72b2f9b1a8d001f3a0a25",
    "user_id": "507f1f77bcf86cd799439011",
    "action_type": "task_created",
    "project_id": "60c72b2f9b1a8d001f3a0a1d",
    "target_type": "task",
    "target_id": "60c72b2f9b1a8d001f3a0a1e",
    "details": {
      "summary": "修復登入頁面的bug",
      "status": "Open"
    },
    "created_at": "2023-01-01T12:00:00Z"
  },
  {
    "id": "60c72b2f9b1a8d001f3a0a26",
    "user_id": "507f1f77bcf86cd799439011",
    "action_type": "task_updated",
    "project_id": "60c72b2f9b1a8d001f3a0a1d",
    "target_type": "task",
    "target_id": "60c72b2f9b1a8d001f3a0a1e",
    "details": {
      "changed_fields": ["summary", "description", "status", "priority", "assignee_id", "due_date", "sprint_id", "tags"],
      "old_values": {
        "summary": "修復登入頁面的bug",
        "status": "Open",
        "priority": "High",
        "assignee_id": "507f1f77bcf86cd799439011"
      },
      "new_values": {
        "summary": "修復登入頁面的驗證 bug",
        "status": "In Progress",
        "priority": "Critical",
        "assignee_id": "507f1f77bcf86cd799439012"
      }
    },
    "created_at": "2023-01-02T12:00:00Z"
  }
]
```

### 獲取用戶活動日誌

```
GET /activity_logs/users/{user_id}
```

路徑參數：
- `user_id`: 用戶 ID

查詢參數：
- `skip` (可選): 分頁跳過數量，默認為 0
- `limit` (可選): 分頁限制數量，默認為 100，最大為 1000
- `action_type` (可選): 按活動類型過濾
- `target_type` (可選): 按目標實體類型過濾
- `project_id` (可選): 按專案過濾

響應：
```json
[
  {
    "id": "60c72b2f9b1a8d001f3a0a25",
    "user_id": "507f1f77bcf86cd799439011",
    "action_type": "task_created",
    "project_id": "60c72b2f9b1a8d001f3a0a1d",
    "target_type": "task",
    "target_id": "60c72b2f9b1a8d001f3a0a1e",
    "details": {
      "summary": "修復登入頁面的bug",
      "status": "Open"
    },
    "created_at": "2023-01-01T12:00:00Z"
  }
]
```

## 通知管理

### 獲取用戶通知列表

```
GET /notifications/users/{user_id}/
```

路徑參數：
- `user_id`: 用戶 ID

查詢參數：
- `is_read` (可選): 按已讀狀態過濾
- `type` (可選): 按通知類型過濾
- `skip` (可選): 分頁跳過數量，默認為 0
- `limit` (可選): 分頁限制數量，默認為 100

響應：
```json
[
  {
    "id": "60c72b2f9b1a8d001f3a0a36",
    "recipient_id": "507f1f77bcf86cd799439011",
    "sender_id": "507f1f77bcf86cd799439011",
    "type": "task_assigned_to_me",
    "message": "你被指派了新任務：實現登入功能",
    "target_type": "task",
    "target_id": "60c72b2f9b1a8d001f3a0a1e",
    "is_read": false,
    "created_at": "2023-01-01T12:00:00Z"
  },
  {
    "id": "60c72b2f9b1a8d001f3a0a37",
    "recipient_id": "507f1f77bcf86cd799439011",
    "sender_id": "507f1f77bcf86cd799439012",
    "type": "mentioned_me",
    "message": "有人在評論中提及了你 @testuser",
    "target_type": "comment",
    "target_id": "60c72b2f9b1a8d001f3a0a1f",
    "is_read": false,
    "created_at": "2023-01-03T12:00:00Z"
  }
]
```

### 標記通知為已讀

```
PUT /notifications/{notification_id}/read
```

路徑參數：
- `notification_id`: 通知 ID

響應：
```json
{
  "id": "60c72b2f9b1a8d001f3a0a36",
  "recipient_id": "507f1f77bcf86cd799439011",
  "sender_id": "507f1f77bcf86cd799439011",
  "type": "task_assigned_to_me",
  "message": "你被指派了新任務：實現登入功能",
  "target_type": "task",
  "target_id": "60c72b2f9b1a8d001f3a0a1e",
  "is_read": true,
  "created_at": "2023-01-01T12:00:00Z"
}
```

### 將所有通知標記為已讀

```
PUT /notifications/users/{user_id}/mark_all_read
```

路徑參數：
- `user_id`: 用戶 ID

響應：
```json
{
  "message": "All notifications marked as read",
  "count": 2
}
```

## 權限控制

目前，API 不實現完整的身份驗證和授權。在未來版本中，將添加以下功能：

1. 用戶註冊和登入
2. 基於角色的訪問控制 (RBAC)
3. 專案級別的訪問權限
4. API 令牌驗證

## 使用示例

### 創建專案並添加任務

```javascript
// 創建專案
const projectResponse = await fetch("http://localhost:8000/api/v1/projects/", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    name: "電子商務網站",
    description: "建立一個現代化的電子商務網站"
  })
});
const project = await projectResponse.json();

// 創建任務
const taskResponse = await fetch(`http://localhost:8000/api/v1/tasks/projects/${project.id}/tasks/`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    summary: "設計首頁佈局",
    description: "<p>創建響應式首頁設計</p>",
    status: "Open",
    priority: "High",
    task_type: "Task",
    tags: ["design", "frontend"]
  })
});
const task = await taskResponse.json();

// 為任務添加評論
const commentResponse = await fetch(`http://localhost:8000/api/v1/tasks/${task.id}/comments/`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    content: "<p>我們應該參考競爭對手的網站佈局</p>"
  })
});
```

### 使用看板和移動任務

```javascript
// 創建看板
const boardResponse = await fetch(`http://localhost:8000/api/v1/boards/projects/${project.id}/boards/`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    name: "開發看板",
    type: "Kanban",
    columns: [
      { name: "待處理", order: 1, status_mapping: ["Open"] },
      { name: "進行中", order: 2, status_mapping: ["In Progress"] },
      { name: "已完成", order: 3, status_mapping: ["Resolved", "Closed"] }
    ]
  })
});
const board = await boardResponse.json();

// 移動任務到進行中列
const moveTaskResponse = await fetch(`http://localhost:8000/api/v1/tasks/${task.id}/move`, {
  method: "PUT",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    target_column_id: board.columns[1].id,  // "進行中"列
    position: 1.0, 
    __v: task.__v  // 版本號，用於樂觀鎖定
  })
});
```

### 監聽實時事件

```javascript
// 建立 SSE 連接
const eventSource = new EventSource(`http://localhost:8000/api/v1/events/${user_id}?project_id=${project_id}`);

// 監聽任務創建事件
eventSource.addEventListener("task.created", (e) => {
  const data = JSON.parse(e.data);
  console.log(`新任務創建: ${data.summary}`);
  // 更新 UI
});

// 監聽任務更新事件
eventSource.addEventListener("task.updated", (e) => {
  const data = JSON.parse(e.data);
  console.log(`任務 ${data.task_id} 已更新`);
  // 更新 UI
});

// 監聽通知事件
eventSource.addEventListener("notification.created", (e) => {
  const data = JSON.parse(e.data);
  console.log(`新通知: ${data.type}`);
  // 更新通知徽章
});

// 處理連接錯誤
eventSource.onerror = (error) => {
  console.error("SSE connection error:", error);
  // 實現重連邏輯
};

// 關閉連接
// eventSource.close();
```

## 注意事項

1. 所有 ID 參數應為有效的 MongoDB ObjectId 字串格式。
2. 版本控制 (`__v` 字段) 用於任務更新的樂觀鎖定。
3. 使用 Server-Sent Events (SSE) 接收實時更新。
4. 文件上傳使用 `multipart/form-data` 格式。
5. 日期時間格式使用 ISO 8601 (`YYYY-MM-DDTHH:MM:SSZ`)。

## RAG系统

### 生成嵌入向量

```
POST /rag/embeddings/generate/{repo_id}
```

路径参数:
- `repo_id`: 代码仓库ID

请求体:
```json
{
  "force_regenerate": false
}
```

响应:
```json
{
  "success": true,
  "message": "Embedding generation started successfully.",
  "status": {
    "repo_id": "60c72b2f9b1a8d001f3a0a1d",
    "status": "processing",
    "start_time": "2023-05-03T10:00:00Z",
    "progress": 0.0,
    "total_files": 0,
    "processed_files": 0,
    "errors": []
  }
}
```

### 查询嵌入状态

```
GET /rag/embeddings/status/{repo_id}
```

路径参数:
- `repo_id`: 代码仓库ID

响应:
```json
{
  "success": true,
  "status": {
    "repo_id": "60c72b2f9b1a8d001f3a0a1d",
    "status": "completed",
    "start_time": "2023-05-03T10:00:00Z",
    "end_time": "2023-05-03T10:05:00Z",
    "progress": 1.0,
    "total_files": 120,
    "processed_files": 120,
    "failed_files": 2,
    "code_chunks": 350,
    "doc_chunks": 75,
    "errors": []
  }
}
```

### 执行语义搜索

```
POST /rag/search
```

请求体:
```json
{
  "query": "如何实现用户认证功能?",
  "repo_id": "60c72b2f9b1a8d001f3a0a1d",
  "collection": "all",
  "limit": 5,
  "file_types": ["js", "py"]
}
```

响应:
```json
{
  "success": true,
  "data": [
    {
      "file_path": "src/auth/auth.js",
      "file_name": "auth.js",
      "content": "function authenticate(username, password) {\n  // 验证逻辑\n  return jwt.sign({ username }, SECRET_KEY);\n}",
      "score": 0.85,
      "language": "javascript",
      "type": "code",
      "metadata": {
        "line_start": 45,
        "line_end": 48
      }
    },
    {
      "file_path": "docs/authentication.md",
      "file_name": "authentication.md",
      "content": "# 认证系统\n\n本系统使用JWT进行用户认证...",
      "score": 0.82,
      "language": null,
      "type": "doc",
      "metadata": {}
    }
  ],
  "count": 2,
  "query": "如何实现用户认证功能?"
}
```

### 执行RAG查询

```
POST /rag/query
```

请求体:
```json
{
  "query": "如何实现用户认证功能?",
  "repo_id": "60c72b2f9b1a8d001f3a0a1d",
  "context_limit": 5,
  "llm_model": "gemini-2.5-flash",
  "llm_provider": "google",
  "include_code": true,
  "include_docs": true,
  "temperature": 0.7,
  "max_tokens": 1000
}
```

响应:
```json
{
  "success": true,
  "data": {
    "answer": "在这个仓库中，用户认证功能使用JWT实现。主要代码位于`src/auth/auth.js`文件...",
    "references": [
      {
        "file_path": "src/auth/auth.js",
        "file_name": "auth.js",
        "content": "function authenticate(username, password) {\n  // 验证逻辑\n  return jwt.sign({ username }, SECRET_KEY);\n}",
        "score": 0.85,
        "language": "javascript",
        "type": "code",
        "metadata": {
          "line_start": 45,
          "line_end": 48
        }
      }
    ],
    "model": "gemini-2.5-flash",
    "provider": "google"
  },
  "query": "如何实现用户认证功能?"
}
```

### 删除嵌入向量

```
DELETE /rag/embeddings/{repo_id}
```

路径参数:
- `repo_id`: 代码仓库ID

响应:
```json
{
  "success": true,
  "message": "Embeddings for repository 60c72b2f9b1a8d001f3a0a1d have been deleted successfully."
}
```

### 获取消息可视化数据

```
GET /rag/visualization/message/{message_id}
```

路径参数:
- `message_id`: 消息ID

响应:
```json
{
  "success": true,
  "data": {
    "sources": [
      {
        "id": 0,
        "file_id": "60c72b2f9b1a8d001f3a0a2e",
        "file_path": "src/auth/auth.js",
        "file_name": "auth.js",
        "content": "function authenticate(username, password) {\n  // 验证逻辑\n  return jwt.sign({ username }, SECRET_KEY);\n}",
        "preview": "function authenticate(username, password) {\n  // 验证逻辑\n  return jwt.sign({ username }, SECRET_KEY);\n}",
        "score": 0.85,
        "language": "javascript",
        "type": "code",
        "metadata": {
          "line_start": 45,
          "line_end": 48
        }
      }
    ],
    "summary": {
      "total_sources": 1,
      "code_sources": 1,
      "doc_sources": 0,
      "avg_score": 0.85
    },
    "file_types": {
      "javascript": 1
    }
  }
}
```

### 高亮匹配内容

```
POST /rag/visualization/highlight
```

请求体:
```json
{
  "query": "用户认证",
  "context": "function authenticate(username, password) {\n  // 验证逻辑\n  return jwt.sign({ username }, SECRET_KEY);\n}",
  "language": "javascript"
}
```

响应:
```json
{
  "success": true,
  "data": {
    "matched_lines": [
      {
        "line": 1,
        "content": "function authenticate(username, password) {",
        "matched_terms": ["认证"]
      }
    ],
    "context_lines": [
      {
        "line": 1,
        "content": "function authenticate(username, password) {",
        "is_match": true
      },
      {
        "line": 2,
        "content": "  // 验证逻辑",
        "is_match": false
      },
      {
        "line": 3,
        "content": "  return jwt.sign({ username }, SECRET_KEY);",
        "is_match": false
      }
    ],
    "has_highlights": true,
    "language": "javascript"
  }
}
```

## 对话系统

### 创建对话会话

```
POST /conversations/
```

请求体:
```json
{
  "title": "代码问答",
  "project_id": "60c72b2f9b1a8d001f3a0a1d",
  "repo_id": "60c72b2f9b1a8d001f3a0a1e",
  "settings": {
    "model": "gemini-2.5-flash",
    "temperature": 0.7,
    "max_tokens": 1000,
    "context_limit": 5,
    "include_code": true,
    "include_docs": true
  }
}
```

响应:
```json
{
  "success": true,
  "data": {
    "_id": "60c72b2f9b1a8d001f3a0a2f",
    "user_id": "507f1f77bcf86cd799439011",
    "title": "代码问答",
    "created_at": "2023-05-03T10:00:00Z",
    "last_message_at": "2023-05-03T10:00:00Z",
    "message_count": 0,
    "settings": {
      "model": "gemini-2.5-flash",
      "temperature": 0.7,
      "max_tokens": 1000,
      "context_limit": 5,
      "include_code": true,
      "include_docs": true
    }
  }
}
```

### 获取对话会话列表

```
GET /conversations/
```

查询参数:
- `skip` (可选): 分页跳过数量，默认为0
- `limit` (可选): 分页限制数量，默认为20
- `project_id` (可选): 按项目ID过滤

响应:
```json
{
  "success": true,
  "data": [
    {
      "_id": "60c72b2f9b1a8d001f3a0a2f",
      "user_id": "507f1f77bcf86cd799439011",
      "title": "代码问答",
      "created_at": "2023-05-03T10:00:00Z",
      "last_message_at": "2023-05-03T10:00:00Z",
      "message_count": 0
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 20
}
```

### 获取单个对话会话

```
GET /conversations/{conversation_id}
```

路径参数:
- `conversation_id`: 对话会话ID

响应:
```json
{
  "success": true,
  "data": {
    "_id": "60c72b2f9b1a8d001f3a0a2f",
    "user_id": "507f1f77bcf86cd799439011",
    "title": "代码问答",
    "created_at": "2023-05-03T10:00:00Z",
    "last_message_at": "2023-05-03T10:00:00Z",
    "message_count": 0,
    "settings": {
      "model": "gemini-2.5-flash",
      "temperature": 0.7,
      "max_tokens": 1000,
      "context_limit": 5,
      "include_code": true,
      "include_docs": true
    }
  }
}
```

### 获取会话消息列表

```
GET /conversations/{conversation_id}/messages
```

路径参数:
- `conversation_id`: 对话会话ID

查询参数:
- `skip` (可选): 分页跳过数量，默认为0
- `limit` (可选): 分页限制数量，默认为50
- `sort_order` (可选): 排序顺序，可选值为"asc"或"desc"，默认为"asc"

响应:
```json
{
  "success": true,
  "data": [
    {
      "_id": "60c72b2f9b1a8d001f3a0a30",
      "conversation_id": "60c72b2f9b1a8d001f3a0a2f",
      "user_id": "507f1f77bcf86cd799439011",
      "role": "user",
      "content": "如何实现用户认证功能?",
      "type": "text",
      "status": "completed",
      "created_at": "2023-05-03T10:01:00Z",
      "references": []
    },
    {
      "_id": "60c72b2f9b1a8d001f3a0a31",
      "conversation_id": "60c72b2f9b1a8d001f3a0a2f",
      "user_id": "507f1f77bcf86cd799439011",
      "role": "assistant",
      "content": "在这个仓库中，用户认证功能使用JWT实现...",
      "type": "text",
      "status": "completed",
      "created_at": "2023-05-03T10:01:05Z",
      "references": [
        {
          "file_path": "src/auth/auth.js",
          "file_name": "auth.js",
          "content": "function authenticate(username, password) {...}",
          "score": 0.85,
          "language": "javascript",
          "type": "code",
          "metadata": {
            "line_start": 45,
            "line_end": 48
          }
        }
      ]
    }
  ],
  "total": 2,
  "skip": 0,
  "limit": 50
}
```

### 在会话中创建消息

```
POST /conversations/{conversation_id}/messages
```

路径参数:
- `conversation_id`: 对话会话ID

请求体:
```json
{
  "content": "如何实现用户认证功能?",
  "type": "text",
  "metadata": {}
}
```

响应:
```json
{
  "success": true,
  "data": {
    "user_message": {
      "_id": "60c72b2f9b1a8d001f3a0a30",
      "conversation_id": "60c72b2f9b1a8d001f3a0a2f",
      "user_id": "507f1f77bcf86cd799439011",
      "role": "user",
      "content": "如何实现用户认证功能?",
      "type": "text",
      "status": "completed",
      "created_at": "2023-05-03T10:01:00Z",
      "references": []
    },
    "ai_message_id": "60c72b2f9b1a8d001f3a0a31"
  }
}
```

### WebSocket对话API

系统提供两个WebSocket端点用于实时对话:

```
WebSocket: ws://localhost:8000/api/v1/ws/chat
WebSocket: ws://localhost:8000/api/v1/ws/chat/{conversation_id}
```

#### 连接参数

- `token` (可选): 用户身份验证令牌
- `conversation_id` (可选): 要加入的会话ID
- `reconnect_token` (可选): 用于断线重连的令牌

#### 客户端发送消息格式

##### 心跳消息
```json
{
  "type": "ping"
}
```

##### 订阅会话
```json
{
  "type": "subscribe",
  "conversation_id": "60c72b2f9b1a8d001f3a0a2f"
}
```

##### 发送新消息
```json
{
  "type": "message",
  "conversation_id": "60c72b2f9b1a8d001f3a0a2f",
  "content": "如何实现用户认证功能?",
  "metadata": {}
}
```

##### 编辑消息
```json
{
  "type": "edit_message",
  "message_id": "60c72b2f9b1a8d001f3a0a30",
  "content": "如何使用JWT实现用户认证功能?"
}
```

##### 正在输入指示
```json
{
  "type": "typing",
  "conversation_id": "60c72b2f9b1a8d001f3a0a2f"
}
```

#### 服务器响应格式

##### 连接成功
```json
{
  "type": "connected",
  "data": {
    "connection_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "507f1f77bcf86cd799439011",
    "reconnect_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

##### 订阅成功
```json
{
  "type": "subscribed",
  "data": {
    "conversation_id": "60c72b2f9b1a8d001f3a0a2f"
  }
}
```

##### 接收消息
```json
{
  "type": "message",
  "data": {
    "_id": "60c72b2f9b1a8d001f3a0a30",
    "conversation_id": "60c72b2f9b1a8d001f3a0a2f",
    "user_id": "507f1f77bcf86cd799439011",
    "role": "user",
    "content": "如何实现用户认证功能?",
    "type": "text",
    "status": "completed",
    "created_at": "2023-05-03T10:01:00Z"
  }
}
```

##### 心跳响应
```json
{
  "type": "pong",
  "timestamp": 1620032460.0
}
```

##### 错误消息
```json
{
  "type": "error",
  "data": {
    "message": "Invalid JSON message"
  }
}
```

## AI 配置管理

管理不同 AI 服务提供商的配置和凭证。

### 基础 URL

```
/api/v1/ai/config/
```

### 创建 AI 服务提供商配置

```
POST /ai/config/providers/
```

请求体：
```json
{
  "provider_name": "openai",
  "display_name": "Personal OpenAI Key",
  "api_key": "sk-xxxxxxxxxxxxxxxxxxxx",
  "is_active": true,
  "models": ["gpt-4o", "gpt-4-turbo"],
  "additional_config": {}
}
```

说明：
- `provider_name` 必须是系统支持的提供商之一（如 "openai", "google", "anthropic", "azure_openai", "aws_bedrock"）
- `api_key` 为 API 密钥，将被加密存储
- `additional_config` 根据不同的提供商可能需要不同的配置项（如 Azure OpenAI 需要 endpoint URL）

响应 (201 Created)：
```json
{
  "id": "64a2f3d5c1b8d3d7f8a9e0b2",
  "user_id": "507f1f77bcf86cd799439011",
  "provider_name": "openai",
  "display_name": "Personal OpenAI Key",
  "is_active": true,
  "models": ["gpt-4o", "gpt-4-turbo"],
  "additional_config": {},
  "created_at": "2023-07-03T14:25:33Z",
  "updated_at": "2023-07-03T14:25:33Z"
}
```

### 获取 AI 服务提供商配置列表

```
GET /ai/config/providers/
```

查询参数：
- `provider_name` (可选): 按提供商名称过滤
- `is_active` (可选): 按激活状态过滤 (true/false)
- `skip` (可选): 分页跳过数量, 默认为 0
- `limit` (可选): 分页限制数量, 默认为 20

响应 (200 OK)：
```json
{
  "success": true,
  "data": [
    {
      "id": "64a2f3d5c1b8d3d7f8a9e0b2",
      "user_id": "507f1f77bcf86cd799439011",
      "provider_name": "openai",
      "display_name": "Personal OpenAI Key",
      "is_active": true,
      "models": ["gpt-4o", "gpt-4-turbo"],
      "additional_config": {},
      "created_at": "2023-07-03T14:25:33Z",
      "updated_at": "2023-07-03T14:25:33Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 20
}
```

### 获取单个 AI 服务提供商配置

```
GET /ai/config/providers/{config_id}
```

路径参数：
- `config_id`: AI 服务提供商配置的 ID

响应 (200 OK)：
```json
{
  "id": "64a2f3d5c1b8d3d7f8a9e0b2",
  "user_id": "507f1f77bcf86cd799439011",
  "provider_name": "openai",
  "display_name": "Personal OpenAI Key",
  "is_active": true,
  "models": ["gpt-4o", "gpt-4-turbo"],
  "additional_config": {},
  "created_at": "2023-07-03T14:25:33Z",
  "updated_at": "2023-07-03T14:25:33Z"
}
```

### 更新 AI 服务提供商配置

```
PUT /ai/config/providers/{config_id}
```

路径参数：
- `config_id`: AI 服务提供商配置的 ID

请求体：
```json
{
  "display_name": "Updated OpenAI Key Name",
  "api_key": "sk-new-key-if-needed",
  "is_active": false,
  "models": ["gpt-4o"]
}
```

说明：
- 所有字段都是可选的，只有提供的字段才会被更新
- `provider_name` 通常不允许更改

响应 (200 OK)：
```json
{
  "id": "64a2f3d5c1b8d3d7f8a9e0b2",
  "user_id": "507f1f77bcf86cd799439011",
  "provider_name": "openai",
  "display_name": "Updated OpenAI Key Name",
  "is_active": false,
  "models": ["gpt-4o"],
  "additional_config": {},
  "created_at": "2023-07-03T14:25:33Z",
  "updated_at": "2023-07-03T15:10:42Z"
}
```

### 删除 AI 服务提供商配置

```
DELETE /ai/config/providers/{config_id}
```

路径参数：
- `config_id`: AI 服务提供商配置的 ID

响应 (200 OK)：
```json
{
  "success": true,
  "message": "AI provider configuration deleted successfully"
}
```

### 获取支持的 AI 服务提供商列表

```
GET /ai/config/supported-providers/
```

响应 (200 OK)：
```json
{
  "success": true,
  "data": [
    {
      "provider_name": "openai",
      "display_name": "OpenAI",
      "credentials_schema": {
        "api_key": { "type": "password", "required": true, "label": "API Key" }
      },
      "models": [
        {"id": "gpt-4o", "name": "gpt-4o"},
        {"id": "gpt-4-turbo", "name": "gpt-4-turbo"},
        {"id": "gpt-3.5-turbo", "name": "gpt-3.5-turbo"}
      ]
    },
    {
      "provider_name": "google",
      "display_name": "Google AI",
      "credentials_schema": {
        "api_key": { "type": "password", "required": true, "label": "API Key (Google AI Studio)" }
      },
      "models": [
        {"id": "gemini-1.5-pro-latest", "name": "Gemini 1.5 Pro"},
        {"id": "gemini-1.5-flash-latest", "name": "Gemini 1.5 Flash"}
      ]
    },
    {
      "provider_name": "anthropic",
      "display_name": "Anthropic",
      "credentials_schema": {
        "api_key": { "type": "password", "required": true, "label": "API Key" }
      },
      "models": [
        {"id": "claude-3.5-sonnet", "name": "claude-3.5-sonnet"},
        {"id": "claude-3.7-sonnet", "name": "claude-3.7-sonnet"}
      ]
    }
  ]
}
```

### 更新支持的 AI 服务提供商列表

```
PUT /ai/config/supported-providers/
```

请求体：
```json
{
  "providers": [
    {
      "provider_name": "openai",
      "display_name": "OpenAI",
      "credentials_schema": {
        "api_key": { "type": "password", "required": true, "label": "API Key" }
      },
      "models": [
        {"id": "gpt-4o", "name": "gpt-4o"},
        {"id": "gpt-4-turbo", "name": "gpt-4-turbo"}
      ]
    }
  ]
}
```

响应 (200 OK)：
```json
{
  "success": true,
  "data": [
    {
      "provider_name": "openai",
      "display_name": "OpenAI",
      "credentials_schema": {
        "api_key": { "type": "password", "required": true, "label": "API Key" }
      },
      "models": [
        {"id": "gpt-4o", "name": "gpt-4o"},
        {"id": "gpt-4-turbo", "name": "gpt-4-turbo"}
      ]
    }
  ]
}
```

### 根据模型名称列表更新提供商模型

```
POST /ai/config/supported-providers/update-models
```

请求体：
```json
{
  "ai_model_names": [
    "gpt-4o",
    "claude-3.5-sonnet", 
    "gemini-1.5-pro",
    "grok-3-mini-beta"
  ]
}
```

说明：
- 系统将自动识别每个模型名称属于哪个提供商，并更新相应提供商的模型列表
- 若提供的模型名称无法识别，则会被忽略

响应 (200 OK)：
```json
{
  "success": true,
  "data": [
    {
      "provider_name": "openai",
      "display_name": "OpenAI",
      "credentials_schema": {
        "api_key": { "type": "password", "required": true, "label": "API Key" }
      },
      "models": [
        {"id": "gpt-4o", "name": "gpt-4o"}
      ]
    },
    {
      "provider_name": "anthropic",
      "display_name": "Anthropic",
      "credentials_schema": {
        "api_key": { "type": "password", "required": true, "label": "API Key" }
      },
      "models": [
        {"id": "claude-3.5-sonnet", "name": "claude-3.5-sonnet"}
      ]
    },
    {
      "provider_name": "google",
      "display_name": "Google AI",
      "credentials_schema": {
        "api_key": { "type": "password", "required": true, "label": "API Key (Google AI Studio)" }
      },
      "models": [
        {"id": "gemini-1.5-pro", "name": "gemini-1.5-pro"}
      ]
    },
    {
      "provider_name": "xai",
      "display_name": "xAI (Grok)",
      "credentials_schema": {
        "api_key": { "type": "password", "required": true, "label": "API Key" }
      },
      "models": [
        {"id": "grok-3-mini-beta", "name": "grok-3-mini-beta"}
      ]
    }
  ]
}
```
