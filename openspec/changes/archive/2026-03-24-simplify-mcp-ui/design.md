## Context

NewJob 頁面目前有三個 MCP 相關 UI 區塊，依引擎不同分別顯示：

1. **Claude Code 模式**：藍色靜態提示條（「MCP 來自 .mcp.json，CLI 自動載入」）
2. **Copilot 模式**：紫色可展開區塊（內建 MCP checkbox 清單 + 連線測試 + token 輸入）
3. **共用**：掃描 `.mcp.json` 後動態顯示的環境變數輸入欄位

實際上兩個引擎都是從 repo `.mcp.json` 動態載入 MCP，scan 邏輯也已經共用（`watch repo_url/branch → scanRepoMcp`）。引擎分流的顯示邏輯已失去意義。

## Goals / Non-Goals

**Goals:**

- 將 MCP 區塊統一為純資料驅動的共用顯示：有偵測結果才顯示，無則隱藏
- 移除前端不再需要的內建 MCP 狀態與相關 API 呼叫
- 評估後端 MCP registry/test API 是否可一併移除

**Non-Goals:**

- 不修改兩個 executor 的 MCP 載入邏輯（`executor.py`、`copilot_executor.py`）
- 不修改 `mcp_loader.py` 的 scan/load 邏輯
- 不改變 env_overrides 的提交與處理流程

## Decisions

### 移除引擎分流的 MCP 顯示區塊

刪除 `NewJob.vue` 第 221-279 行的兩個條件區塊（Claude Code 藍色提示條 + Copilot 紫色 MCP 區塊），改為單一共用區塊。

理由：兩個引擎的 MCP 來源一致（`.mcp.json`），區分顯示無實際價值。

### 新增資料驅動的 MCP 偵測提示

利用已有的 `scanServers` 狀態，在掃描到 `.mcp.json` servers 時顯示「偵測到 N 個 MCP servers：xxx, yyy」。無 servers 時不顯示。

理由：相比靜態說明文字，動態結果能讓使用者確認偵測狀態，有 debug 價值。

### 清理前端內建 MCP 狀態

移除：`mcpList`、`mcpPresets`、`selectedMcps`、`mcpTokens`、`mcpTestResults`、`mcpExpanded`、`mcpInitTested`、`doTestMcps()`、`toggleMcp()`、`setMcpToken()`、`onMounted` 中的 `getMcpList()` 呼叫。

移除 `api.js` 中的 `getMcpList()`、`testMcps()` 函式。

理由：移除 UI 區塊後這些狀態和函式不再被引用。

### 評估移除後端 MCP registry API

確認 `/api/v1/mcp/list` 和 `/api/v1/mcp/test` 端點只被前端 NewJob 頁面使用。若無其他消費者，移除 `backend/routers/mcp.py` 中的 list/test 路由及 `backend/services/mcp.py` 中的 `BUILTIN_MCPS`/`PRESETS` 定義。

理由：避免留下 dead code。保留 `mcp_loader.py`（scan 邏輯仍在使用）。

## Risks / Trade-offs

- **[未來若需要回加內建 MCP]** → 低風險，目前兩個引擎都不依賴內建 MCP 清單，且 git history 保留了完整實作可參考
- **[後端 API 可能有非前端消費者]** → 移除前須 grep 確認無其他呼叫端；若有則保留 API，只清理前端
