## Context

目前系統是 Jira-to-PR 自動化平台，使用者提交 Jira Ticket 後由 Claude Code + Jirara SOP 自動完成開發並建立 PR。Jirara 已支援多輪迭代——透過讀取 Jira Comment 判斷修正意圖，在同一 branch / PR 上繼續修改。

然而平台層缺乏 Rerun 機制，使用者必須手動回到 NewJob 頁面重新填入相同資訊才能觸發下一輪，UX 不佳。

## Goals / Non-Goals

**Goals:**

- 提供一鍵 Rerun，從已完成或失敗的 Job 直接觸發新一輪執行
- 保留每輪完整的 logs 紀錄，互不干擾
- 在前端顯示輪次關聯，可在各輪之間導航

**Non-Goals:**

- 自動重試（失敗後自動觸發，無需人工介入）——不在此次範圍
- 修改 Jirara SOP——Jirara 已能透過 Comment 判斷修正意圖
- 修改 Queue / Executor 邏輯——Rerun 建立的 Job 走一般佇列流程

## Decisions

### Rerun 建立新 Job 而非 Reset 原 Job

Rerun 時建立全新 Job 並透過 `parent_job_id` 指向原 Job，而非重置原 Job 狀態。

**理由：**
- 每輪 logs 乾淨分離，方便 debug 與追溯
- 與現有 `create_job` 邏輯一致，實作簡單
- 不需處理 logs 清理、SSE 重連等複雜邏輯

**替代方案：** Reset 原 Job（清除 logs、重置狀態）——會造成歷史紀錄遺失且實作複雜度高。

### Rerun API 為獨立端點

新增 `POST /api/v1/jobs/{id}/rerun` 端點，而非讓前端呼叫 `POST /api/v1/jobs` 帶 `parent_job_id`。

**理由：**
- 語意清楚——rerun 是對特定 Job 的操作
- 後端負責複製參數，前端不需知道原 Job 的所有欄位
- 方便加入 rerun 限制邏輯（如只允許 completed/failed 狀態）

### parent_job_id 為 nullable 欄位

`jobs` 表新增 `parent_job_id TEXT` 欄位，預設 NULL。首次建立的 Job 無 parent，Rerun 建立的 Job 指向前一輪。

**理由：**
- 向後相容，不影響現有 Job
- 透過 migration 函數安全新增欄位（與現有 `_migrate_job_logs` 模式一致）

### 前端輪次導航以連結串顯示

在 JobDetail 頁面顯示輪次資訊，格式為「第 N 輪」加上前後輪連結，而非獨立的時間軸或 tab 頁面。

**理由：**
- 實作簡單，符合現有 UI 風格
- 輪次通常不多（2~5 輪），不需複雜的導航元件

## Risks / Trade-offs

- **快速連續點擊 Rerun** → 既有 duplicate check 已防護（同 ticket 有 queued/running 時會 409），不需額外處理
- **parent_job_id 連結斷裂**（原 Job 被刪除）→ 目前系統無刪除 Job 功能，風險極低
- **輪次查詢效能** → 透過 parent_job_id 遞迴查詢。輪次少（<10），無效能問題
