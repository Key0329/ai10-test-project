## 1. Queue Worker 並行化

- [x] 1.1 使用 dict 追蹤多個 running tasks：將 `_current_task` 改為 `_running_tasks: dict[str, asyncio.Task]`，實現 concurrent job dispatch
- [x] 1.2 非阻塞 dispatch 搭配 done callback：將 `_get_next_job()` 改為 `_get_next_jobs(limit)` 一次取多個，輪詢迴圈使用 `add_done_callback` 非阻塞 dispatch（non-blocking dispatch loop）
- [x] 1.3 MAX_CONCURRENT 環境變數控制上限：新增 `MAX_CONCURRENT` 環境變數（預設 5），控制 concurrent job dispatch 上限（MAX_CONCURRENT configurable via environment）

## 2. Cancel 與 Shutdown

- [x] 2.1 Cancel specific running job：更新 `cancel_job` 從 `_running_tasks` dict 找到對應 task 取消，不影響其他 running jobs
- [x] 2.2 Graceful shutdown cancels all tasks：更新 `stop_queue_worker` 同時 cancel 所有 `_running_tasks` 中的 tasks

## 3. 設定與文件

- [x] 3.1 更新 `.env.example` 加入 `MAX_CONCURRENT=5`
