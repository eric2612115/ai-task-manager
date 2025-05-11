# Git 倉庫 API 更新文檔

## 更新概述

我們已經更新了Git倉庫管理相關的API，添加了對`project_id`的支持。這允許用戶將倉庫與特定項目關聯，並按項目過濾倉庫列表。

## 已更新的API端點

### 1. 發現可訪問的倉庫

```
GET /git/repos/discover
```

**查詢參數:**
- `credential_id` (必填): 憑證ID
- `project_id` (可選): 項目ID，用於將發現的倉庫關聯到特定項目

**更新說明:**
添加了`project_id`參數，當提供此參數時，發現的倉庫將預先關聯到指定的項目，方便後續創建倉庫時使用。

### 2. 創建倉庫記錄

```
POST /git/repos
```

**請求體:**
```json
{
  "credential_id": "507f1f77bcf86cd799439011",
  "project_id": "507f1f77bcf86cd799439013",  // 新增: 項目ID
  "platform": "github",
  "owner": "username",
  "name": "repo-name",
  "full_name": "username/repo-name",
  "default_branch": "main",
  "description": "項目描述",
  "is_private": false,
  "sync_branches": ["main", "develop"]
}
```

**更新說明:**
在請求體中添加了可選的`project_id`字段，用於關聯倉庫到特定項目。

### 3. 獲取所有倉庫

```
GET /git/repos
```

**查詢參數:**
- `skip` (可選): 分頁跳過數量，默認為 0
- `limit` (可選): 分頁限制數量，默認為 100
- `project_id` (可選): 項目ID，用於過濾特定項目的倉庫

**更新說明:**
添加了`project_id`查詢參數，允許用戶僅獲取與特定項目關聯的倉庫，便於按項目組織和管理倉庫。

### 4. 獲取單個倉庫

```
GET /git/repos/{repo_id}
```

**更新說明:**
響應中添加了`project_id`字段，如果倉庫已關聯到項目。

## 使用示例

### 按項目過濾倉庫

```javascript
// 獲取與特定項目關聯的倉庫
const projectRepos = await fetch(`http://localhost:8000/api/v1/git/repos?project_id=507f1f77bcf86cd799439013`);
```

### 創建並關聯到項目的倉庫

```javascript
// 發現特定項目的可用倉庫
const discoverRepos = await fetch(`http://localhost:8000/api/v1/git/repos/discover?credential_id=507f1f77bcf86cd799439011&project_id=507f1f77bcf86cd799439013`);

// 創建關聯到項目的倉庫
const createRepo = await fetch(`http://localhost:8000/api/v1/git/repos`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    credential_id: "507f1f77bcf86cd799439011",
    project_id: "507f1f77bcf86cd799439013",
    platform: "github",
    owner: "username",
    name: "repo-name",
    full_name: "username/repo-name",
    default_branch: "main"
  })
});
```

## 技術實現細節

1. 在數據模型中添加了`project_id`字段，作為可選的關聯字段
2. 更新了倉庫查詢邏輯，支持按項目ID過濾
3. 修改了倉庫創建邏輯，支持設置項目關聯
4. 更新了現有倉庫檢測邏輯，考慮項目ID作為唯一性約束的一部分

這些更新使得用戶可以更有效地管理不同項目中的Git倉庫，提高了系統的組織性和用戶體驗。 