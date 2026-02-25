# DKEC 工作進度追蹤系統 - Claude 指示

## 每次對話開始時

當使用者開始新的對話時，請自動執行以下步驟：

1. **讀取** `data/tasks.json` 檔案
2. **提供工作摘要**，包含：
   - 進行中的任務清單及其進度百分比
   - 今日到期的任務（`estimated_completion` 為今天）
   - 已逾期但未完成的任務（`estimated_completion` 已過但 status 仍為 `in_progress`）
   - 暫緩中的任務及預計重啟時間
   - 本週整體完成率

## 更新任務規範

當使用者要求更新任務時，請遵循以下流程：

1. **先讀取** `data/tasks.json` 取得最新狀態
2. **修改對應欄位**，注意：
   - 更新 `updated_at` 為當前時間（ISO 8601 格式，+08:00 時區）
   - 更新 `meta.last_updated` 為當前時間
   - 變更狀態時更新對應欄位：
     - 改為 `completed` → 設定 `completed_at`，`progress` 設為 100
     - 改為 `in_progress` → 設定 `estimated_completion`
     - 改為 `pending` → 設定 `estimated_restart`
     - 改為 `cancelled` → 設定 `cancelled_reason`
3. **記錄到 weekly_log**：在對應週的 entries 中新增一筆紀錄
4. **寫回** `data/tasks.json`

## ID 命名規則

- 專案 ID：`proj_001`, `proj_002`, ...（三位數補零）
- 任務 ID：`task_001`, `task_002`, ...（三位數補零，全域遞增）
- 新增時掃描現有最大 ID 後 +1

## 任務狀態

| 狀態 | 值 | 說明 |
|------|------|------|
| 已完成 | `completed` | 任務已結束，記錄完成時間 |
| 進行中 | `in_progress` | 正在執行，有預計完成日和進度 |
| 暫緩 | `pending` | 暫時擱置，有預計重啟日 |
| 終止 | `cancelled` | 不再執行，記錄終止原因 |

## 週報產生

使用者可能會要求產生週報。產生時請：
1. 讀取 `data/tasks.json`
2. 篩選本週（或指定週）的所有任務變動
3. 以清晰的格式列出：
   - 本週完成的任務
   - 本週進行中任務的進度變化
   - 暫緩和終止的任務
   - 下週預計工作重點

## 技術資訊

- Web 應用：Flask，運行於 `0.0.0.0:5000`
- 資料儲存：`data/tasks.json`（JSON 格式）
- 啟動指令：`python app.py`
