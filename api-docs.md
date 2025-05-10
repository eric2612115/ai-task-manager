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

## 默認路由

### 根路徑

```
GET /
```

響應：
```json
{
  "message": "Task Manager API is running"
}
```

### 健康檢查

```
GET /health
```

響應：
```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2023-07-12T12:00:00Z"
}
```

## Git倉庫管理

### 凭证管理

#### 创建Git凭证

```
POST /git/credentials
```

请求体：
```json
{
  "name": "GitHub账号",
  "platform": "github",
  "auth_type": "token",
  "token": "ghp_xxxxxxxxxxxxxxxx",
  "base_url": null
}
```

注意：
- `platform` 值必须为 "github" 或 "gitlab"
- `auth_type` 值必须为 "token" 或 "oauth"，默认为 "token"
- `base_url` 仅对 GitLab 企业版必填，否则可为 null

响应：
```json
{
  "success": true,
  "data": {
    "_id": "507f1f77bcf86cd799439011",
    "name": "GitHub账号",
    "platform": "github",
    "auth_type": "token",
    "token": "[加密后的token]",
    "base_url": null,
    "status": "active",
    "last_validated": null,
    "created_at": "2023-05-01T10:00:00Z",
    "updated_at": "2023-05-01T10:00:00Z"
  },
  "message": "Credential created successfully"
}
```

#### 获取所有Git凭证

```
GET /git/credentials
```

查询参数：
- `skip` (可选): 分页跳过数量，默认为 0
- `limit` (可选): 分页限制数量，默认为 100

响应：
```json
{
  "success": true,
  "data": [
    {
      "_id": "507f1f77bcf86cd799439011",
      "name": "GitHub账号",
      "platform": "github",
      "auth_type": "token",
      "token": "[加密后的token]",
      "base_url": null,
      "status": "active",
      "last_validated": "2023-05-01T10:30:00Z",
      "created_at": "2023-05-01T10:00:00Z",
      "updated_at": "2023-05-01T10:30:00Z"
    }
  ],
  "count": 1
}
```

#### 获取单个Git凭证

```
GET /git/credentials/{credential_id}
```

路径参数：
- `credential_id`: 凭证ID

响应：
```json
{
  "success": true,
  "data": {
    "_id": "507f1f77bcf86cd799439011",
    "name": "GitHub账号",
    "platform": "github",
    "auth_type": "token",
    "token": "[加密后的token]",
    "base_url": null,
    "status": "active",
    "last_validated": "2023-05-01T10:30:00Z",
    "created_at": "2023-05-01T10:00:00Z",
    "updated_at": "2023-05-01T10:30:00Z"
  }
}
```

#### 更新Git凭证

```
PUT /git/credentials/{credential_id}
```

路径参数：
- `credential_id`: 凭证ID

请求体：
```json
{
  "name": "GitHub个人账号",
  "token": "ghp_yyyyyyyyyyyyyyyy",
  "base_url": null,
  "status": "active"
}
```

注意：所有字段都是可选的，只有提供的字段才会被更新。

响应：
```json
{
  "success": true,
  "data": {
    "_id": "507f1f77bcf86cd799439011",
    "name": "GitHub个人账号",
    "platform": "github",
    "auth_type": "token",
    "token": "[加密后的新token]",
    "base_url": null,
    "status": "active",
    "last_validated": null,
    "created_at": "2023-05-01T10:00:00Z",
    "updated_at": "2023-05-01T11:00:00Z"
  },
  "message": "Credential updated successfully"
}
```

#### 删除Git凭证

```
DELETE /git/credentials/{credential_id}
```

路径参数：
- `credential_id`: 凭证ID

响应：
```json
{
  "success": true,
  "message": "Credential deleted successfully"
}
```

#### 测试Git凭证连接

```
POST /git/credentials/{credential_id}/test
```

路径参数：
- `credential_id`: 凭证ID

响应：
```json
{
  "success": true,
  "connected": true,
  "message": "Connection successful"
}
```

#### 测试Git令牌有效性

```
POST /git/credentials/test-token
```

请求体：
```json
{
  "platform": "github",
  "token": "ghp_xxxxxxxxxxxxxxxx",
  "base_url": null
}
```

注意：
- `platform` 值必须为 "github" 或 "gitlab"
- `base_url` 仅对 GitLab 企业版必填，否则可为 null
- 此API无需先创建凭证，可直接测试token有效性

响应：
```json
{
  "success": true,
  "data": {
    "valid": true,
    "message": "Connection successful",
    "user_info": {
      "username": "your-username",
      "name": "Your Name",
      "email": "your.email@example.com",
      "avatar_url": "https://avatars.githubusercontent.com/u/12345678"
    }
  }
}
```

### 仓库管理

#### 发现可访问的仓库

```
GET /git/repos/discover
```

查询参数：
- `credential_id` (必填): 凭证ID

响应：
```json
{
  "success": true,
  "data": [
    {
      "platform": "github",
      "owner": "username",
      "name": "repo-name",
      "full_name": "username/repo-name",
      "default_branch": "main",
      "description": "项目描述",
      "is_private": false,
      "exists": false
    },
    {
      "platform": "github",
      "owner": "username",
      "name": "another-repo",
      "full_name": "username/another-repo",
      "default_branch": "master",
      "description": "另一个项目描述",
      "is_private": true,
      "exists": true,
      "id": "507f1f77bcf86cd799439012"
    }
  ],
  "count": 2
}
```

#### 创建仓库记录

```
POST /git/repos
```

请求体：
```json
{
  "credential_id": "507f1f77bcf86cd799439011",
  "platform": "github",
  "owner": "username",
  "name": "repo-name",
  "full_name": "username/repo-name",
  "default_branch": "main",
  "description": "项目描述",
  "is_private": false,
  "sync_branches": ["main", "develop"]
}
```

响应：
```json
{
  "success": true,
  "data": {
    "_id": "507f1f77bcf86cd799439012",
    "credential_id": "507f1f77bcf86cd799439011",
    "platform": "github",
    "owner": "username",
    "name": "repo-name",
    "full_name": "username/repo-name",
    "default_branch": "main",
    "description": "项目描述",
    "is_private": false,
    "sync_enabled": true,
    "sync_branches": ["main", "develop"],
    "sync_status": "pending",
    "created_at": "2023-05-01T12:00:00Z",
    "updated_at": "2023-05-01T12:00:00Z"
  },
  "message": "Repository created successfully"
}
```

#### 获取所有仓库

```
GET /git/repos
```

查询参数：
- `skip` (可选): 分页跳过数量，默认为 0
- `limit` (可选): 分页限制数量，默认为 100

响应：
```json
{
  "success": true,
  "data": [
    {
      "_id": "507f1f77bcf86cd799439012",
      "credential_id": "507f1f77bcf86cd799439011",
      "platform": "github",
      "owner": "username",
      "name": "repo-name",
      "full_name": "username/repo-name",
      "default_branch": "main",
      "description": "项目描述",
      "is_private": false,
      "sync_enabled": true,
      "sync_branches": ["main", "develop"],
      "sync_status": "completed",
      "last_synced_at": "2023-05-01T12:30:00Z",
      "last_commit_sha": "abcdef1234567890",
      "created_at": "2023-05-01T12:00:00Z",
      "updated_at": "2023-05-01T12:30:00Z",
      "credential": {
        "id": "507f1f77bcf86cd799439011",
        "name": "GitHub个人账号",
        "platform": "github",
        "status": "active"
      }
    }
  ],
  "count": 1
}
```

#### 获取单个仓库

```
GET /git/repos/{repo_id}
```

路径参数：
- `repo_id`: 仓库ID

响应：
```json
{
  "success": true,
  "data": {
    "_id": "507f1f77bcf86cd799439012",
    "credential_id": "507f1f77bcf86cd799439011",
    "platform": "github",
    "owner": "username",
    "name": "repo-name",
    "full_name": "username/repo-name",
    "default_branch": "main",
    "description": "项目描述",
    "is_private": false,
    "sync_enabled": true,
    "sync_branches": ["main", "develop"],
    "sync_status": "completed",
    "last_synced_at": "2023-05-01T12:30:00Z",
    "last_commit_sha": "abcdef1234567890",
    "created_at": "2023-05-01T12:00:00Z",
    "updated_at": "2023-05-01T12:30:00Z",
    "credential": {
      "id": "507f1f77bcf86cd799439011",
      "name": "GitHub个人账号",
      "platform": "github",
      "status": "active"
    }
  }
}
```

#### 更新仓库

```
PUT /git/repos/{repo_id}
```

路径参数：
- `repo_id`: 仓库ID

请求体：
```json
{
  "default_branch": "master",
  "sync_enabled": true,
  "sync_branches": ["master", "develop", "feature/*"],
  "description": "更新的项目描述"
}
```

注意：所有字段都是可选的，只有提供的字段才会被更新。

响应：
```json
{
  "success": true,
  "data": {
    "_id": "507f1f77bcf86cd799439012",
    "credential_id": "507f1f77bcf86cd799439011",
    "platform": "github",
    "owner": "username",
    "name": "repo-name",
    "full_name": "username/repo-name",
    "default_branch": "master",
    "description": "更新的项目描述",
    "is_private": false,
    "sync_enabled": true,
    "sync_branches": ["master", "develop", "feature/*"],
    "sync_status": "completed",
    "last_synced_at": "2023-05-01T12:30:00Z",
    "last_commit_sha": "abcdef1234567890",
    "created_at": "2023-05-01T12:00:00Z",
    "updated_at": "2023-05-01T13:00:00Z"
  },
  "message": "Repository updated successfully"
}
```

#### 删除仓库

```
DELETE /git/repos/{repo_id}
```

路径参数：
- `repo_id`: 仓库ID

响应：
```json
{
  "success": true,
  "message": "Repository deleted successfully"
}
```

### 同步操作

#### 同步仓库

```
POST /git/repos/{repo_id}/sync
```

路径参数：
- `repo_id`: 仓库ID

查询参数：
- `sync_type` (可选): 同步类型，可以是 "full" 或 "incremental"，默认为 "full"

响应：
```json
{
  "success": true,
  "message": "Repository synchronization (full) started",
  "sync_status": "syncing"
}
```

#### 获取仓库同步状态

```
GET /git/repos/{repo_id}/sync/status
```

路径参数：
- `repo_id`: 仓库ID

响应：
```json
{
  "success": true,
  "data": {
    "sync_status": "completed",
    "last_synced_at": "2023-05-01T13:30:00Z",
    "latest_sync": {
      "_id": "507f1f77bcf86cd799439013",
      "repository_id": "507f1f77bcf86cd799439012",
      "sync_type": "full",
      "started_at": "2023-05-01T13:00:00Z",
      "completed_at": "2023-05-01T13:30:00Z",
      "status": "completed",
      "files_processed": 120,
      "files_added": 120,
      "files_updated": 0,
      "files_deleted": 0,
      "to_commit": "abcdef1234567890"
    }
  }
}
```

#### 获取仓库同步历史

```
GET /git/repos/{repo_id}/sync/history
```

路径参数：
- `repo_id`: 仓库ID

查询参数：
- `skip` (可选): 分页跳过数量，默认为 0
- `limit` (可选): 分页限制数量，默认为 10

响应：
```json
{
  "success": true,
  "data": [
    {
      "_id": "507f1f77bcf86cd799439014",
      "repository_id": "507f1f77bcf86cd799439012",
      "sync_type": "incremental",
      "started_at": "2023-05-02T10:00:00Z",
      "completed_at": "2023-05-02T10:05:00Z",
      "status": "completed",
      "from_commit": "abcdef1234567890",
      "to_commit": "fedcba0987654321",
      "files_processed": 5,
      "files_added": 2,
      "files_updated": 3,
      "files_deleted": 0
    },
    {
      "_id": "507f1f77bcf86cd799439013",
      "repository_id": "507f1f77bcf86cd799439012",
      "sync_type": "full",
      "started_at": "2023-05-01T13:00:00Z",
      "completed_at": "2023-05-01T13:30:00Z",
      "status": "completed",
      "files_processed": 120,
      "files_added": 120,
      "files_updated": 0,
      "files_deleted": 0,
      "to_commit": "abcdef1234567890"
    }
  ],
  "count": 2
}
```

## 代码文件管理

#### 获取仓库文件树结构

```
GET /code/repos/{repo_id}/tree
```

路径参数：
- `repo_id`: 仓库ID

查询参数：
- `include_deleted` (可选): 是否包含已删除的文件，默认为 false

响应：
```json
{
  "success": true,
  "data": [
    {
      "name": "src",
      "path": "src",
      "type": "directory",
      "children": [
        {
          "id": "507f1f77bcf86cd799439015",
          "name": "main.js",
          "path": "src/main.js",
          "type": "file",
          "language": "javascript",
          "size": 1024,
          "is_deleted": false
        }
      ]
    },
    {
      "name": "README.md",
      "path": "README.md",
      "type": "file",
      "language": "markdown",
      "size": 512,
      "is_deleted": false
    }
  ]
}
```

#### 获取文件内容

```
GET /code/files/{file_id}
```

路径参数：
- `file_id`: 文件ID

响应：
```json
{
  "success": true,
  "data": {
    "_id": "507f1f77bcf86cd799439015",
    "repository_id": "507f1f77bcf86cd799439012",
    "file_path": "src/main.js",
    "file_name": "main.js",
    "content": "console.log('Hello, world!');\n\nfunction sayHello() {\n  return 'Hello!';\n}\n",
    "language": "javascript",
    "size_bytes": 1024,
    "line_count": 5,
    "commit_sha": "fedcba0987654321",
    "branch": "main",
    "last_modified": "2023-05-02T10:05:00Z",
    "author": "username",
    "is_deleted": false,
    "created_at": "2023-05-01T13:30:00Z",
    "updated_at": "2023-05-02T10:05:00Z"
  }
}
```

#### 根据路径获取文件

```
GET /code/repos/{repo_id}/files
```

路径参数：
- `repo_id`: 仓库ID

查询参数：
- `path` (必填): 文件路径，相对于仓库根目录

响应：
```json
{
  "success": true,
  "data": {
    "_id": "507f1f77bcf86cd799439015",
    "repository_id": "507f1f77bcf86cd799439012",
    "file_path": "src/main.js",
    "file_name": "main.js",
    "content": "console.log('Hello, world!');\n\nfunction sayHello() {\n  return 'Hello!';\n}\n",
    "language": "javascript",
    "size_bytes": 1024,
    "line_count": 5,
    "commit_sha": "fedcba0987654321",
    "branch": "main",
    "last_modified": "2023-05-02T10:05:00Z",
    "author": "username",
    "is_deleted": false,
    "created_at": "2023-05-01T13:30:00Z",
    "updated_at": "2023-05-02T10:05:00Z"
  }
}
```

#### 获取文件版本历史

```
GET /code/files/{file_id}/versions
```

路径参数：
- `file_id`: 文件ID

查询参数：
- `skip` (可选): 分页跳过数量，默认为 0
- `limit` (可选): 分页限制数量，默认为 10

响应：
```json
{
  "success": true,
  "data": [
    {
      "_id": "507f1f77bcf86cd799439017",
      "file_id": "507f1f77bcf86cd799439015",
      "commit_sha": "fedcba0987654321",
      "content": "console.log('Hello, world!');\n\nfunction sayHello() {\n  return 'Hello!';\n}\n",
      "diff": "@@ -1,4 +1,5 @@\n console.log('Hello, world!');\n \n function sayHello() {\n+  return 'Hello!';\n }\n",
      "author": "username",
      "commit_message": "Add return statement to sayHello function",
      "committed_at": "2023-05-02T10:05:00Z",
      "created_at": "2023-05-02T10:05:00Z"
    },
    {
      "_id": "507f1f77bcf86cd799439016",
      "file_id": "507f1f77bcf86cd799439015",
      "commit_sha": "abcdef1234567890",
      "content": "console.log('Hello, world!');\n\nfunction sayHello() {\n}\n",
      "diff": null,
      "author": "username",
      "commit_message": "Initial commit",
      "committed_at": "2023-05-01T13:30:00Z",
      "created_at": "2023-05-01T13:30:00Z"
    }
  ],
  "count": 2
}
```

#### 搜索代码内容

```
POST /code/search
```

请求体：
```json
{
  "repository_id": "507f1f77bcf86cd799439012",
  "query": "function sayHello",
  "file_extensions": [".js", ".ts"],
  "limit": 50,
  "skip": 0
}
```

响应：
```json
{
  "success": true,
  "data": [
    {
      "id": "507f1f77bcf86cd799439015",
      "file_path": "src/main.js",
      "file_name": "main.js",
      "language": "javascript",
      "matches": [
        {
          "start_line": 1,
          "end_line": 5,
          "match_line": 3,
          "context": [
            {
              "line_number": 1,
              "content": "console.log('Hello, world!');",
              "is_match": false
            },
            {
              "line_number": 2,
              "content": "",
              "is_match": false
            },
            {
              "line_number": 3,
              "content": "function sayHello() {",
              "is_match": true
            },
            {
              "line_number": 4,
              "content": "  return 'Hello!';",
              "is_match": false
            },
            {
              "line_number": 5,
              "content": "}",
              "is_match": false
            }
          ]
        }
      ],
      "score": 0.95
    }
  ],
  "count": 1
}
```

## 文档管理

#### 创建文档

```
POST /docs
```

请求体：
```json
{
  "repository_id": "507f1f77bcf86cd799439012",
  "title": "项目文档",
  "content": "# 项目文档\n\n这是一个示例文档。",
  "path": "docs/README.md",
  "tags": ["文档", "说明"]
}
```

响应：
```json
{
  "success": true,
  "data": {
    "_id": "507f1f77bcf86cd799439018",
    "repository_id": "507f1f77bcf86cd799439012",
    "title": "项目文档",
    "content": "# 项目文档\n\n这是一个示例文档。",
    "path": "docs/README.md",
    "tags": ["文档", "说明"],
    "author_id": null,
    "last_modified_by": null,
    "is_deleted": false,
    "created_at": "2023-05-03T10:00:00Z",
    "updated_at": "2023-05-03T10:00:00Z"
  },
  "message": "Document created successfully"
}
```

#### 获取文档列表

```
GET /docs
```

查询参数：
- `repo_id` (可选): 仓库ID，用于筛选特定仓库的文档
- `skip` (可选): 分页跳过数量，默认为 0
- `limit` (可选): 分页限制数量，默认为 100

响应：
```json
{
  "success": true,
  "data": [
    {
      "_id": "507f1f77bcf86cd799439018",
      "repository_id": "507f1f77bcf86cd799439012",
      "title": "项目文档",
      "content": "# 项目文档\n\n这是一个示例文档。",
      "path": "docs/README.md",
      "tags": ["文档", "说明"],
      "author_id": null,
      "last_modified_by": null,
      "is_deleted": false,
      "created_at": "2023-05-03T10:00:00Z",
      "updated_at": "2023-05-03T10:00:00Z"
    }
  ],
  "count": 1
}
```

#### 获取单个文档

```
GET /docs/{doc_id}
```

路径参数：
- `doc_id`: 文档ID

响应：
```json
{
  "success": true,
  "data": {
    "_id": "507f1f77bcf86cd799439018",
    "repository_id": "507f1f77bcf86cd799439012",
    "title": "项目文档",
    "content": "# 项目文档\n\n这是一个示例文档。",
    "path": "docs/README.md",
    "tags": ["文档", "说明"],
    "author_id": null,
    "last_modified_by": null,
    "is_deleted": false,
    "created_at": "2023-05-03T10:00:00Z",
    "updated_at": "2023-05-03T10:00:00Z"
  }
}
```

#### 更新文档

```
PUT /docs/{doc_id}
```

路径参数：
- `doc_id`: 文档ID

查询参数：
- `user_id` (可选): 更新用户ID

请求体：
```json
{
  "title": "更新的项目文档",
  "content": "# 更新的项目文档\n\n这是一个更新后的示例文档。",
  "path": "docs/README.md",
  "tags": ["文档", "说明", "更新"],
  "change_summary": "更新文档标题和内容"
}
```

注意：所有字段都是可选的，只有提供的字段才会被更新。

响应：
```json
{
  "success": true,
  "data": {
    "_id": "507f1f77bcf86cd799439018",
    "repository_id": "507f1f77bcf86cd799439012",
    "title": "更新的项目文档",
    "content": "# 更新的项目文档\n\n这是一个更新后的示例文档。",
    "path": "docs/README.md",
    "tags": ["文档", "说明", "更新"],
    "author_id": null,
    "last_modified_by": "507f1f77bcf86cd799439011",
    "is_deleted": false,
    "created_at": "2023-05-03T10:00:00Z",
    "updated_at": "2023-05-03T11:00:00Z"
  },
  "message": "Document updated successfully"
}
```

#### 删除文档

```
DELETE /docs/{doc_id}
```

路径参数：
- `doc_id`: 文档ID

响应：
```json
{
  "success": true,
  "message": "Document deleted successfully"
}
```

#### 获取文档版本历史

```
GET /docs/{doc_id}/versions
```

路径参数：
- `doc_id`: 文档ID

查询参数：
- `skip` (可选): 分页跳过数量，默认为 0
- `limit` (可选): 分页限制数量，默认为 20

响应：
```json
{
  "success": true,
  "data": [
    {
      "_id": "507f1f77bcf86cd799439020",
      "doc_id": "507f1f77bcf86cd799439018",
      "title": "更新的项目文档",
      "content": "# 更新的项目文档\n\n这是一个更新后的示例文档。",
      "edited_by": "507f1f77bcf86cd799439011",
      "version_number": 2,
      "change_summary": "更新文档标题和内容",
      "created_at": "2023-05-03T11:00:00Z"
    },
    {
      "_id": "507f1f77bcf86cd799439019",
      "doc_id": "507f1f77bcf86cd799439018",
      "title": "项目文档",
      "content": "# 项目文档\n\n这是一个示例文档。",
      "edited_by": null,
      "version_number": 1,
      "change_summary": null,
      "created_at": "2023-05-03T10:00:00Z"
    }
  ],
  "count": 2
}
```

#### 获取指定版本的文档

```
GET /docs/{doc_id}/versions/{version_number}
```

路径参数：
- `doc_id`: 文档ID
- `version_number`: 版本号

响应：
```json
{
  "success": true,
  "data": {
    "_id": "507f1f77bcf86cd799439019",
    "doc_id": "507f1f77bcf86cd799439018",
    "title": "项目文档",
    "content": "# 项目文档\n\n这是一个示例文档。",
    "edited_by": null,
    "version_number": 1,
    "change_summary": null,
    "created_at": "2023-05-03T10:00:00Z"
  }
}
```

#### 生成文档

```
POST /docs/{repo_id}/generate
```

路径参数：
- `repo_id`: 仓库ID

请求体：
```json
{
  "source_files": ["src/main.js", "README.md"],
  "title": "API文档",
  "target_format": "markdown",
  "include_code": true,
  "doc_type": "technical"
}
```

响应：
```json
{
  "success": true,
  "data": {
    "_id": "507f1f77bcf86cd799439021",
    "repository_id": "507f1f77bcf86cd799439012",
    "title": "API文档",
    "content": "# Generated Documentation\n\n## src/main.js\n\n**Language**: javascript\n\n```\nconsole.log('Hello, world!');\n\nfunction sayHello() {\n  return 'Hello!';\n}\n```\n\n## README.md\n\n**Language**: markdown\n\n```\n# Example Project\n\nThis is an example project.\n```\n",
    "path": null,
    "tags": ["auto-generated", "technical"],
    "author_id": null,
    "last_modified_by": null,
    "is_deleted": false,
    "created_at": "2023-05-03T12:00:00Z",
    "updated_at": "2023-05-03T12:00:00Z"
  },
  "message": "Document generated successfully"
}
```
