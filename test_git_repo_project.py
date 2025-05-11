#!/usr/bin/env python
"""
測試Git倉庫API的project_id支持功能
"""
import requests
import json
from bson import ObjectId
import os
from datetime import datetime

# API基礎URL
BASE_URL = "http://localhost:8000/api/v1"

# 生成測試ID
def generate_id():
    return str(ObjectId())

# 記錄測試步驟
def log_step(step, result=None):
    print(f"\n------ {step} ------")
    if result:
        if isinstance(result, dict) or isinstance(result, list):
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(result)

# 主測試函數
def test_git_repo_project_support():
    # 創建兩個測試項目ID
    project_id_1 = generate_id()
    project_id_2 = generate_id()
    
    log_step(f"測試開始 - 時間: {datetime.now().isoformat()}")
    log_step(f"測試項目ID 1: {project_id_1}")
    log_step(f"測試項目ID 2: {project_id_2}")
    
    # 步驟1: 獲取所有憑證
    log_step("步驟1: 獲取Git憑證列表")
    response = requests.get(f"{BASE_URL}/git/credentials")
    credentials = response.json()
    log_step("憑證列表", credentials)
    
    if not credentials.get("data"):
        log_step("錯誤: 沒有找到可用的Git憑證，請先創建憑證")
        return
    
    # 使用第一個可用的憑證
    credential_id = credentials["data"][0]["_id"]
    log_step(f"使用憑證ID: {credential_id}")
    
    # 步驟2: 為項目1發現可用倉庫
    log_step(f"步驟2: 為項目1 ({project_id_1}) 發現倉庫")
    response = requests.get(
        f"{BASE_URL}/git/repos/discover",
        params={"credential_id": credential_id, "project_id": project_id_1}
    )
    repos_project_1 = response.json()
    log_step("項目1可用倉庫", repos_project_1)
    
    # 步驟3: 為項目2發現可用倉庫
    log_step(f"步驟3: 為項目2 ({project_id_2}) 發現倉庫")
    response = requests.get(
        f"{BASE_URL}/git/repos/discover",
        params={"credential_id": credential_id, "project_id": project_id_2}
    )
    repos_project_2 = response.json()
    log_step("項目2可用倉庫", repos_project_2)
    
    # 檢查項目ID是否正確添加
    if not repos_project_1.get("data") or not repos_project_2.get("data"):
        log_step("錯誤: 沒有找到可用的倉庫")
        return
    
    # 確認project_id已添加到返回的倉庫數據中
    assert repos_project_1["data"][0].get("project_id") == project_id_1
    assert repos_project_2["data"][0].get("project_id") == project_id_2
    log_step("驗證通過: 發現的倉庫已關聯正確的項目ID")
    
    # 步驟4: 為每個項目創建一個倉庫
    if not repos_project_1.get("data") or not repos_project_2.get("data"):
        log_step("錯誤: 沒有可用倉庫可創建")
        return
    
    # 項目1創建倉庫
    repo_data_1 = repos_project_1["data"][0]
    create_data_1 = {
        "credential_id": credential_id,
        "project_id": project_id_1,
        "platform": repo_data_1["platform"],
        "owner": repo_data_1["owner"],
        "name": repo_data_1["name"],
        "full_name": repo_data_1["full_name"],
        "default_branch": repo_data_1.get("default_branch", "main"),
        "description": repo_data_1.get("description", "項目1測試倉庫"),
        "is_private": repo_data_1.get("is_private", False)
    }
    
    log_step(f"步驟4.1: 為項目1創建倉庫")
    try:
        response = requests.post(
            f"{BASE_URL}/git/repos",
            json=create_data_1
        )
        repo_1 = response.json()
        log_step("項目1創建的倉庫", repo_1)
        repo_id_1 = repo_1["data"]["_id"]
    except Exception as e:
        log_step(f"創建項目1倉庫時出錯: {str(e)}")
        if response:
            log_step(f"API響應: {response.text}")
        repo_id_1 = None
    
    # 項目2創建倉庫
    repo_data_2 = repos_project_2["data"][0]
    create_data_2 = {
        "credential_id": credential_id,
        "project_id": project_id_2,
        "platform": repo_data_2["platform"],
        "owner": repo_data_2["owner"],
        "name": repo_data_2["name"],
        "full_name": repo_data_2["full_name"],
        "default_branch": repo_data_2.get("default_branch", "main"),
        "description": repo_data_2.get("description", "項目2測試倉庫"),
        "is_private": repo_data_2.get("is_private", False)
    }
    
    log_step(f"步驟4.2: 為項目2創建倉庫")
    try:
        response = requests.post(
            f"{BASE_URL}/git/repos",
            json=create_data_2
        )
        repo_2 = response.json()
        log_step("項目2創建的倉庫", repo_2)
        repo_id_2 = repo_2["data"]["_id"]
    except Exception as e:
        log_step(f"創建項目2倉庫時出錯: {str(e)}")
        if response:
            log_step(f"API響應: {response.text}")
        repo_id_2 = None
    
    # 步驟5: 按項目ID過濾倉庫
    log_step(f"步驟5.1: 獲取項目1的倉庫列表")
    response = requests.get(
        f"{BASE_URL}/git/repos",
        params={"project_id": project_id_1}
    )
    project_1_repos = response.json()
    log_step("項目1倉庫列表", project_1_repos)
    
    log_step(f"步驟5.2: 獲取項目2的倉庫列表")
    response = requests.get(
        f"{BASE_URL}/git/repos",
        params={"project_id": project_id_2}
    )
    project_2_repos = response.json()
    log_step("項目2倉庫列表", project_2_repos)
    
    # 驗證倉庫按項目正確過濾
    if project_1_repos.get("data"):
        for repo in project_1_repos["data"]:
            assert repo.get("project_id") == project_id_1
        log_step(f"驗證通過: 項目1倉庫列表僅包含項目1的倉庫")
    
    if project_2_repos.get("data"):
        for repo in project_2_repos["data"]:
            assert repo.get("project_id") == project_id_2
        log_step(f"驗證通過: 項目2倉庫列表僅包含項目2的倉庫")
    
    # 步驟6: 清理測試數據（可選）
    log_step("步驟6: 清理測試數據")
    if repo_id_1:
        log_step(f"刪除項目1倉庫 (ID: {repo_id_1})")
        response = requests.delete(f"{BASE_URL}/git/repos/{repo_id_1}")
        log_step("刪除結果", response.json())
    
    if repo_id_2:
        log_step(f"刪除項目2倉庫 (ID: {repo_id_2})")
        response = requests.delete(f"{BASE_URL}/git/repos/{repo_id_2}")
        log_step("刪除結果", response.json())
    
    log_step(f"測試完成 - 時間: {datetime.now().isoformat()}")

if __name__ == "__main__":
    test_git_repo_project_support() 