## Context

Queue worker（`backend/services/queue.py`）原本使用單一 `_current_task` 變數追蹤執行中的 Job，輪詢時先檢查 `_is_any_running()`，有任何 Job 在跑就跳過。輪詢迴圈 `await _current_task` 等待完成後才繼續。

## Goals / Non-Goals

**Goals:**

- 支援同時執行最多 N 個 Job（由 `MAX_CONCURRENT` 環境變數控制，預設 5）
- 輪詢迴圈非阻塞，每次 poll 填滿空位
- Cancel 能精準取消指定 Job

**Non-Goals:**

- 不做 per-repo 或 per-user 的並行限制
- 不做 Job 之間的資源隔離（共享同一台 Mac Mini）
- 不修改 executor 本身的執行邏輯

## Decisions

### 使用 dict 追蹤多個 running tasks

`_running_tasks: dict[str, asyncio.Task]` 以 job_id 為 key。每次 poll 計算 `slots = MAX_CONCURRENT - len(_running_tasks)`，有空位就 dispatch。

**替代方案**：使用 `asyncio.Semaphore`。但 Semaphore 不方便做 cancel-by-job-id，且需要額外的 task 管理邏輯。dict 更直觀。

### 非阻塞 dispatch 搭配 done callback

不再 `await task`，改用 `task.add_done_callback` 在完成時自動清理。輪詢迴圈保持每 `POLL_INTERVAL` 秒執行一次。

### MAX_CONCURRENT 環境變數控制上限

預設 5，可不重啟調整（修改 .env 後重啟 server）。考量 Mac Mini 資源和 Claude Max rate limit，5 是保守起點。

## Risks / Trade-offs

- **Rate limit** → 同時 5 個 Job 可能觸發 Claude Max 的 rate limit。`--fallback-model sonnet` 可緩解，但需觀察實際表現
- **Mac Mini 資源** → 每個 Job 有 git clone + Claude subprocess，5 個同時跑會消耗 CPU/RAM/磁碟。需監控資源使用
- **同 repo 衝突** → 兩個 Job 同時修改同一 repo 的同一 branch 可能產生 push 衝突。目前不防範，依賴 Jirara 的 branch 命名策略（feature/TICKET）隔離
