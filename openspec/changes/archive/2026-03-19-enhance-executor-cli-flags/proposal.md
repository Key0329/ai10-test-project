## Why

目前 executor 執行 `claude -p` 時只使用基本旗標，缺乏結構化輸出、安全輪數限制和模型降級機制。前端 log 只能顯示原始文字，無法追蹤 token 用量和工具呼叫；Job 卡住時只靠硬性 timeout 強制終止，可能在關鍵操作（git push、PR 建立）中途被殺；API 過載時 Job 直接失敗，沒有自動恢復能力。

## What Changes

- executor CLI 命令加入 `--output-format stream-json`，輸出結構化 JSON 事件流
- executor CLI 命令加入 `--max-turns 50`，限制 agent 輪數作為軟性安全上限
- executor CLI 命令加入 `--fallback-model sonnet`，API 過載時自動降級
- executor 的 `_stream_output` 改為解析 JSON 事件，分類儲存（tool call、assistant message、system info）
- 前端 Job log 顯示邏輯配合結構化資料調整，支援分類檢視

## Capabilities

### New Capabilities

- `structured-job-output`: executor 輸出結構化 JSON 事件流，支援 tool call、token 用量、cost 等分類資料的解析與儲存

### Modified Capabilities

- `sop-injection`: CLI 命令新增 `--max-turns`、`--fallback-model` 旗標，擴展現有注入機制

## Impact

- 影響的 spec：`structured-job-output`（新增）、`sop-injection`（修改）
- 影響的程式碼：
  - `backend/services/executor.py` — `build_claude_command`、`_stream_output`
  - `backend/routers/jobs.py` — SSE log 端點可能需調整回傳格式
  - `frontend/src/pages/JobDetail.jsx` — log 顯示邏輯
  - `backend/db.py` — `job_logs` 表可能需新增欄位（event_type、metadata）
