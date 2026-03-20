## Why

原本 queue worker 一次只執行一個 Job，其餘排隊等待。當多人同時提交不同專案的工單、或同一 repo 有多張獨立任務時，等待時間過長。需要支援並行執行以提升吞吐量。

## What Changes

- Queue worker 從單一 task 改為最多同時 `MAX_CONCURRENT` 個 task（預設 5）
- `_current_task` 單一變數改為 `_running_tasks` dict（job_id → asyncio.Task）
- `_get_next_job()` 改為 `_get_next_jobs(limit)` 一次取多個
- `_is_any_running()` 改為 `_count_running()` 計算空位
- 輪詢迴圈不再 await 等待 task 完成，改用 `add_done_callback` 非阻塞
- cancel 支援從 `_running_tasks` 找到對應 task 取消
- `stop_queue_worker` 同時 cancel 所有 running tasks
- 新增 `MAX_CONCURRENT` 環境變數

## Capabilities

### New Capabilities

- `concurrent-job-execution`: Queue worker 支援同時執行多個 Job，上限由 MAX_CONCURRENT 環境變數控制

### Modified Capabilities

（無）

## Impact

- 影響的程式碼：
  - `backend/services/queue.py` — 核心並行邏輯重寫
  - `.env.example` — 新增 MAX_CONCURRENT
- 不影響：executor.py、routers、前端、資料庫 schema
