# 文檔API更新說明

## 更新概述

我們已經更新了文檔管理相關的API，將之前的`repository_id`替換為`project_id`。這使得文檔現在與項目（project）關聯，而不是與特定的代碼倉庫（repository）關聯。

## 主要變更

1. 數據模型變更：
   - `ProjectDocumentation`模型中的`repository_id`字段更改為`project_id`
   - `DocCreate`請求模型中的`repository_id`字段更改為`project_id`

2. API端點變更：
   - 獲取文檔列表的查詢參數從`repo_id`改為`project_id`
   - 生成文檔的端點從`/docs/{repo_id}/generate`改為`/project-docs/projects/{project_id}/generate`

3. 文檔生成邏輯變更：
   - 生成文檔時會在項目的所有倉庫中查找源文件，而不僅限於單個倉庫
   - 文檔存儲時關聯到項目，而不是倉庫

## 更新後的API說明

### 創建文檔

```
POST /project-docs
```

請求體：
```json
{
  "project_id": "507f1f77bcf86cd799439013",
  "title": "項目文檔",
  "content": "# 項目文檔\n\n這是一個示例文檔。",
  "path": "docs/README.md",
  "tags": ["文檔", "說明"]
}
```

響應：
```json
{
  "success": true,
  "data": {
    "_id": "507f1f77bcf86cd799439018",
    "project_id": "507f1f77bcf86cd799439013",
    "title": "項目文檔",
    "content": "# 項目文檔\n\n這是一個示例文檔。",
    "path": "docs/README.md",
    "tags": ["文檔", "說明"],
    "author_id": null,
    "last_modified_by": null,
    "is_deleted": false,
    "created_at": "2023-05-03T10:00:00Z",
    "updated_at": "2023-05-03T10:00:00Z"
  },
  "message": "Document created successfully"
}
```

### 獲取文檔列表

```
GET /project-docs
```

查詢參數：
- `project_id` (可選): 項目ID，用於篩選特定項目的文檔
- `skip` (可選): 分頁跳過數量，默認為 0
- `limit` (可選): 分頁限制數量，默認為 100

### 生成文檔

```
POST /project-docs/projects/{project_id}/generate
```

路徑參數：
- `project_id`: 項目ID

請求體：
```json
{
  "source_files": ["src/main.js", "README.md"],
  "title": "API文檔",
  "target_format": "markdown",
  "include_code": true,
  "doc_type": "technical"
}
```

## 遷移說明

以前使用`repository_id`關聯的文檔數據需要進行遷移，將其關聯到適當的`project_id`。這可以通過查詢倉庫所屬的項目來實現：

```javascript
// 偽代碼示例
for (let doc of all_documents) {
  if (doc.has("repository_id") && !doc.has("project_id")) {
    let repo = find_repository_by_id(doc.repository_id)
    if (repo && repo.has("project_id")) {
      doc.project_id = repo.project_id
      save(doc)
    }
  }
}
```

## 使用示例

### 創建項目文檔

```javascript
// 創建與項目關聯的文檔
const response = await fetch("http://localhost:8000/api/v1/project-docs", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    project_id: "507f1f77bcf86cd799439013",
    title: "項目設計文檔",
    content: "# 項目設計\n\n本文檔描述了整個項目的架構設計..."
  })
});
```

### 獲取項目的所有文檔

```javascript
// 獲取特定項目的所有文檔
const docs = await fetch("http://localhost:8000/api/v1/project-docs?project_id=507f1f77bcf86cd799439013");
``` 