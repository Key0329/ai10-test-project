## Why

Priority 欄位（1-5）目前前端已被註解隱藏，所有 Job 皆以預設值 3 送出，實際行為等同純 FIFO。保留這個未使用的功能只增加 DB schema、queue 排序邏輯與 queue_position 計算的複雜度，沒有實際價值。移除後可簡化程式碼並減少維護負擔。

## What Changes

- **BREAKING** 移除 `JobCreate` model 的 `priority` 欄位，API 不再接受 priority 參數
- Queue 排序從 `ORDER BY priority ASC, created_at ASC` 簡化為 `ORDER BY created_at ASC`
- Queue position 計算移除 priority 比較邏輯，改為純 FIFO 計數
- Rerun 不再複製 priority 欄位
- 前端移除被註解的 priority 相關 HTML 與 form 欄位
- DB schema 移除 priority 欄位

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `concurrent-job-execution`: 排隊規則從 priority + FIFO 改為純 FIFO
- `job-rerun`: 移除 rerun 時繼承 priority 的行為

## Impact

- 受影響程式碼：`backend/models/job.py`、`backend/routers/jobs.py`、`backend/services/queue.py`、`frontend/src/pages/NewJob.vue`
- 受影響 API：`POST /jobs` 不再接受 `priority` 參數，回應中不再包含 `priority` 欄位
- DB：需要 migration 移除 `priority` 欄位（或容許欄位殘留但不使用）
- 文件：`docs/system-spec.md` 中 priority 相關描述需更新
