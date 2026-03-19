## Context

目前 executor (`backend/services/executor.py`) 透過 `build_claude_command` 組裝 CLI 命令，使用 `_stream_output` 逐行讀取 subprocess 的 stdout/stderr 原始文字存入 `job_logs` 表。前端 `JobDetail.jsx` 透過 SSE 端點取得這些 log 並以純文字顯示。

現有命令：
```
claude -p --dangerously-skip-permissions --append-system-prompt-file jirara.md "prompt"
```

問題：
1. 原始文字 log 無法區分 tool call、assistant 回應、系統資訊
2. 無法追蹤 token 用量和成本
3. Job 卡住只靠硬性 timeout (1800s) 強制終止，可能中斷關鍵操作
4. API 過載時 Job 直接失敗，無自動恢復

## Goals / Non-Goals

**Goals:**

- 讓 executor 輸出結構化 JSON 事件流，支援分類儲存
- 加入 agent 輪數限制作為軟性安全機制
- 加入模型降級機制提升穩定性
- 前端能依事件類型分類顯示 log

**Non-Goals:**

- 不改變權限策略（維持 `--dangerously-skip-permissions`）
- 不做並行 Job 執行
- 不修改 Jirara SOP 本身
- 不重新設計 job_logs 表結構（只新增欄位）

## Decisions

### 使用 stream-json 輸出格式取代原始文字

在 `build_claude_command` 中加入 `--output-format stream-json`。每行輸出為一個 JSON 物件，包含 `type` 欄位可用於分類。

`_stream_output` 改為嘗試解析每行 JSON，提取 `type` 作為 `event_type` 儲存。解析失敗時 fallback 為原始文字（相容 stderr 和非 JSON 輸出）。

**替代方案**：使用 `--output-format json`（非串流），但這會等到 Claude 完成才一次輸出，失去即時 log 串流能力。

### job_logs 表新增 event_type 和 metadata 欄位

```sql
ALTER TABLE job_logs ADD COLUMN event_type TEXT DEFAULT 'raw';
ALTER TABLE job_logs ADD COLUMN metadata TEXT;  -- JSON string
```

`event_type` 用於前端篩選（如 `assistant`、`tool_use`、`tool_result`、`system`、`raw`）。`metadata` 存放完整 JSON 事件供進階查詢。

**替代方案**：建立新表。但現有 SSE 端點和前端都綁定 `job_logs`，改動最小的方式是擴展欄位。

### max-turns 設為 50 搭配現有 timeout 作為雙重保護

`--max-turns 50` 讓 Claude 在達到限制時優雅停止（有機會完成收尾動作），`JOB_TIMEOUT` 作為最後防線。50 是初始估值，可透過 stream-json 的事件數觀察實際 Job 的 turn 數再微調。

新增環境變數 `MAX_TURNS`，預設 50，允許不重新部署即可調整。

### fallback-model 使用 sonnet 作為降級目標

`--fallback-model sonnet` 確保主模型過載時 Job 不會直接失敗。Sonnet 在程式碼任務上能力足夠處理大部分 Jirara 流程。

新增環境變數 `FALLBACK_MODEL`，預設 `sonnet`。

### 前端 log 分類顯示

`JobDetail.jsx` 的 SSE 端點回傳 `event_type`，前端可依此分類：
- 預設顯示所有 log（現有行為不變）
- 新增篩選功能：只看 assistant 回應 / 只看 tool 操作

## Risks / Trade-offs

- **stream-json 格式可能隨 Claude Code 版本更新而變動** → 解析邏輯用 try/except fallback 為原始文字，確保不因格式變動而中斷
- **max-turns 50 可能不夠複雜 Job 使用** → 透過環境變數可即時調整，並透過 stream-json 觀察實際數據
- **fallback 到 sonnet 可能影響複雜任務品質** → Jirara 的核心操作（Jira API、git、gh）不需要最強模型，降級影響有限
- **job_logs 表 ALTER TABLE** → SQLite 支援 ADD COLUMN，無需 migration 工具，但既有 log 的新欄位會是 NULL/預設值
