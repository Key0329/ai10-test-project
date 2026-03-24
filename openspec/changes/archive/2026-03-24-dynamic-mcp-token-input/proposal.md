## Why

Repo 的 `.mcp.json` 可能引用 `${VAR}` 環境變數作為 token（例如 `${SENTRY_TOKEN}`），但不同 repo 需要不同的 token 值。系統 `.env` 不能 commit 到 git，也只能放一組值，無法依 repo 區分。目前使用者沒有任何方式在送 job 時針對 repo 需要的 token 動態填入。

## What Changes

- 新增 API 端點 `POST /api/v1/mcp/scan`：接收 repo URL + branch + GitHub token，輕量 fetch repo 的 `.mcp.json`（不做完整 clone），解析並回傳需要的 `${VAR}` 清單
- 前端 NewJob 表單在使用者選好 repo 後，自動呼叫 scan API，偵測到未定義的 `${VAR}` 時動態生成 token 輸入欄位
- 使用者填入的 token 作為 `env_overrides` 隨 job 送出，executor 在 `convert_to_copilot_format()` 時展開
- 兩種模式（Claude Code / Copilot）都支援：Claude Code 透過子進程環境變數注入，Copilot 透過 `env_overrides` 展開

## Capabilities

### New Capabilities

- `mcp-token-scan`: 輕量掃描 repo `.mcp.json`，回傳所需的環境變數清單，並在前端動態生成 token 輸入欄位

### Modified Capabilities

- `repo-mcp-loading`: executor 接收 `env_overrides` 並在格式轉換時展開 `${VAR}`
- `vue-frontend`: NewJob 表單新增動態 MCP token 輸入區塊

## Impact

- 受影響的程式碼：
  - `backend/routers/mcp.py`（新增 scan 端點）
  - `backend/services/mcp_loader.py`（新增 scan 函數，從遠端 fetch `.mcp.json`）
  - `backend/models/job.py`（新增 `env_overrides` 欄位）
  - `backend/routers/jobs.py`（傳遞 `env_overrides` 到 executor）
  - `backend/services/copilot_executor.py`（接收並使用 `env_overrides`）
  - `backend/services/executor.py`（Claude Code 模式注入環境變數）
  - `frontend/src/api.js`（新增 scanRepoMcp API）
  - `frontend/src/pages/NewJob.vue`（動態 token 輸入 UI）
