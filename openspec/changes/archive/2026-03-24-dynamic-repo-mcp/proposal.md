## Why

目前 Copilot 模式的 MCP 是硬編碼在 `services/mcp.py`（4 個內建 MCP），使用者必須在前端手動勾選。Claude Code 模式則完全沒有 MCP 相關處理。這導致：

1. 每次新增或修改 MCP 都需要改後端程式碼並重新部署
2. 不同 repo 無法各自定義需要的 MCP 工具組合
3. Copilot 模式 rerun 時 MCP 設定會遺失（DB 未儲存）
4. Copilot 模式的 MCP tool 使用無法在 log 中被追蹤和過濾

改為從 repo 的 `.mcp.json` 動態讀取 MCP 設定，讓 MCP 配置跟著 repo 走，同時補齊 Copilot 模式的 MCP 使用追蹤能力。

## What Changes

- 新增 `mcp_loader` 模組：讀取 repo `.mcp.json` 並轉換為 Copilot SDK 格式（`stdio` → `local`、`sse`/`streamable-http` → `http`），支援 `${VAR}` 環境變數展開
- Copilot executor clone 後自動讀取 repo `.mcp.json`，與使用者手動勾選的補充 MCP 合併（repo 優先），注入 session
- Claude Code executor 與 Copilot executor 的 repo 驗證函數增加 `.mcp.json` 偵測 log
- Copilot executor 的 `on_event` handler 增加 MCP tool call 偵測（`mcp__` 前綴），正確標記 `event_type="mcp"`
- Copilot executor 任務完成時統計實際使用的 MCP server，輸出格式與 Claude Code 一致
- 前端 MCP 區塊從「主要選擇」改為「額外補充 repo 設定」角色

## Capabilities

### New Capabilities

- `repo-mcp-loading`: 從 clone 下來的 repo 動態讀取 `.mcp.json` 並轉換格式，支援 Copilot SDK 注入

### Modified Capabilities

- `job-execution-summary`: Copilot 模式新增 MCP 使用追蹤與統計（`event_type="mcp"` 分類 + summary 統計）
- `vue-frontend`: MCP 設定 UI 從「主要選擇」改為「額外補充」角色，加入 repo 自動載入說明

## Impact

- 受影響的程式碼：
  - `backend/services/mcp_loader.py`（新建）
  - `backend/services/copilot_executor.py`（MCP 讀取 + 合併 + 追蹤）
  - `backend/services/executor.py`（`.mcp.json` 偵測 log）
  - `frontend/src/pages/NewJob.vue`（UI 調整）
- `backend/services/mcp.py` 保留不改，作為補充 MCP 來源
- 不需要 DB schema 變更（MCP config 不再需要持久化）
- Rerun 問題自動解決（重新 clone 時從 repo 讀取）
