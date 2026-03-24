## Why

目前 NewJob 頁面的 MCP 顯示區塊依照引擎（Claude Code / Copilot）分成三塊不同的 UI，但實際上兩個引擎都是從 repo 的 `.mcp.json` 動態載入 MCP，只有需要 token 的環境變數才需要使用者介入。引擎分流的 UI 造成不必要的複雜度，且「額外內建 MCP」勾選區塊在 `.mcp.json` 已成為標準後失去存在意義。

## What Changes

- 移除 Claude Code 模式的藍色靜態提示條（「MCP 來自 .mcp.json，CLI 自動載入」）
- 移除 Copilot 模式的紫色「額外 MCP（補充 repo 設定）」可展開區塊（含 checkbox 清單、連線測試、token 輸入）
- 新增共用的動態 MCP 偵測提示：掃描到 `.mcp.json` 時顯示「偵測到 N 個 MCP servers：xxx, yyy」，無 `.mcp.json` 則不顯示
- 保留既有的「🔑 Repo MCP 需要的環境變數」區塊（已是共用邏輯，不需修改）
- 清理前端不再使用的狀態：`mcpList`、`mcpPresets`、`selectedMcps`、`mcpTokens`、`mcpTestResults`、`mcpExpanded`、`mcpInitTested` 及相關函式
- 評估後端 MCP registry API（`/mcp/list`、`/mcp/test`）是否仍有其他使用者，若無則一併移除

## Capabilities

### New Capabilities

（無 — 此變更為既有 UI 的簡化重構）

### Modified Capabilities

- `vue-frontend`: NewJob 頁面 MCP 區塊從引擎分流改為共用資料驅動顯示
- `mcp-token-scan`: scan 結果的 `servers` 欄位改為在前端動態顯示偵測到的 server 清單

## Impact

- 前端：`frontend/src/pages/NewJob.vue`（主要變更）、`frontend/src/api.js`（可能移除 MCP 相關 API 呼叫）
- 後端：`backend/routers/mcp.py`、`backend/services/mcp.py`（若確認無其他使用者則移除 registry/test 端點）
- 不影響執行邏輯：兩個 executor 的 MCP 載入流程不變
