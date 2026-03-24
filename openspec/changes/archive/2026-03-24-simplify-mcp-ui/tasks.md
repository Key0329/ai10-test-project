## 1. 前端 MCP UI 清理

- [x] [P] 1.1 移除引擎分流的 MCP 顯示區塊：刪除 NewJob.vue 中 Claude Code 藍色提示條（第 221-222 行）與 Copilot 紫色「MCP section displays supplemental role label」可展開區塊（第 224-279 行）
- [x] [P] 1.2 清理前端內建 MCP 狀態（移除 Dynamic MCP token input fields 相關）：清理 `mcpList`、`mcpPresets`、`selectedMcps`、`mcpTokens`、`mcpTestResults`、`mcpExpanded`、`mcpInitTested`、`doTestMcps()`、`toggleMcp()`、`setMcpToken()`、`onMounted` 中的 `getMcpList()` 呼叫

## 2. 新增資料驅動的 MCP 偵測提示

- [x] 2.1 新增共用 MCP 偵測摘要區塊：當 `scanServers` 有資料時顯示「偵測到 N 個 MCP servers：xxx, yyy」，實作 MCP section displays supplemental role label 的新行為（engine-agnostic），且 scan result displays server summary 須與 env vars 區塊共存
- [x] 2.2 確認 Frontend auto-scans on repo selection 的 debounce 行為在兩種引擎模式下一致運作（涵蓋 Scan repo .mcp.json via GitHub API 的前端整合）

## 3. 清理前端 API 層

- [x] 3.1 移除 `api.js` 中的 `getMcpList()`、`testMcps()` 函式（評估移除後端 MCP registry API 的前端部分）

## 4. 評估移除後端 MCP registry API

- [x] 4.1 確認 `/api/v1/mcp/list` 和 `/api/v1/mcp/test` 無其他消費者，若無則移除 `backend/routers/mcp.py` 中的 list/test 路由及 `backend/services/mcp.py` 中的 `BUILTIN_MCPS`/`PRESETS`（保留 scan 端點與 `mcp_loader.py`）
