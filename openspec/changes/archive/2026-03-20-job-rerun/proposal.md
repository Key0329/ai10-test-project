## Why

使用者在 AI 完成工作後，可能對輸出結果不滿意，需要透過 Jira Comment 描述調整內容後重新執行。目前系統沒有 Rerun 機制，使用者必須回到 NewJob 頁面手動重新填入相同資訊才能觸發下一輪執行，UX 不佳且容易出錯。

## What Changes

- 新增 `POST /api/v1/jobs/{id}/rerun` API 端點，複製原 Job 參數建立新 Job 並設定 `parent_job_id` 關聯
- `jobs` 資料表新增 `parent_job_id` 欄位，追蹤 Rerun 的輪次關聯
- 前端 JobDetail 頁面新增 Rerun 按鈕（僅在 `completed` / `failed` 狀態顯示）
- 前端顯示輪次資訊與前後輪連結導航

## Capabilities

### New Capabilities

- `job-rerun`: 工作重新執行機制，包含 Rerun API 端點、parent_job_id 資料關聯、前端 Rerun 按鈕與輪次導航

### Modified Capabilities

- `vue-frontend`: 新增 Rerun 按鈕元件與輪次導航 UI

## Impact

- 受影響的程式碼：
  - `backend/db.py` — jobs 表新增 `parent_job_id` 欄位
  - `backend/models/job.py` — JobResponse 新增 `parent_job_id` 欄位
  - `backend/routers/jobs.py` — 新增 rerun 端點
  - `frontend/src/pages/JobDetail.vue` — 新增 Rerun 按鈕與輪次導航
  - `frontend/src/api.js` — 新增 `rerunJob` API 函數
- Jirara SOP（`.claude/skills/jirara.md`）不需修改
- Queue / Executor 不需修改，Rerun 建立的新 Job 走一般佇列流程
