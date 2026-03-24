## Context

系統有兩種執行模式：Claude Code（CLI 子進程）和 Copilot（SDK session）。目前 MCP 設定硬編碼在 `backend/services/mcp.py` 的 `BUILTIN_MCPS`，僅 Copilot 模式使用，且需要前端手動勾選。Claude Code 模式完全無 MCP 處理。

現有 MCP 追蹤方面，Claude Code executor 已有完整的 `mcp__` 前綴偵測（`executor.py:129-181`）和 summary 統計（`executor.py:431-442`），但 Copilot executor 把所有 tool 事件統一標為 `event_type="assistant"`，前端 MCP filter 無法過濾。

## Goals / Non-Goals

**Goals:**

- Clone repo 後自動讀取 `.mcp.json`，Copilot 模式自動注入 session
- 保留內建 MCP Registry 作為手動補充來源
- 兩個 executor 的 repo 驗證都能偵測並 log `.mcp.json` 狀態
- Copilot 模式的 MCP tool call 能被正確分類追蹤

**Non-Goals:**

- 不修改 Claude Code CLI 的 MCP 處理方式（CLI 已自動讀取 `.mcp.json`）
- 不變更 DB schema 或持久化 MCP config
- 不移除內建 MCP Registry

## Decisions

### 新建 mcp_loader 模組處理格式轉換

建立 `backend/services/mcp_loader.py` 專責讀取 `.mcp.json` 並轉換為 Copilot SDK 格式。

轉換規則：`stdio` → `local`、`sse`/`streamable-http` → `http`，自動加 `tools: ["*"]`，展開 `${VAR}` 環境變數引用。

替代方案：直接在 `copilot_executor.py` 內寫轉換邏輯。不採用，因為獨立模組更易測試且可被其他模組重用。

### Repo MCP 與補充 MCP 的合併策略

合併順序：先載入 repo `.mcp.json`，再疊加使用者從前端勾選的補充 MCP。同名時 repo 版本優先（不覆蓋）。

理由：repo 的 `.mcp.json` 是團隊共識的標準配置，應該是權威來源。使用者手動補充的是個人開發環境的額外工具（如 figma、chrome-devtools）。

### Copilot MCP 追蹤對齊 Claude Code 邏輯

在 `copilot_executor.py` 的 `on_event` handler 中，對 `tool.execution_start` 和 `tool.execution_complete` 事件的 `tool_name` 偵測 `mcp__` 前綴，標記為 `event_type="mcp"`。

任務結束時查詢 `event_type='mcp'` 的 log 統計實際使用的 MCP server，格式與 Claude Code 的 `_emit_summary()` 一致。

替代方案：在 Copilot executor 啟動時記錄注入的 MCP server 清單，然後 diff。不採用，因為「注入」和「實際使用」是不同概念，應追蹤實際使用。

## Risks / Trade-offs

- [`.mcp.json` 不存在] → Copilot fallback 到使用者手動勾選的補充 MCP，與現行行為一致
- [Copilot SDK tool_name 不帶 `mcp__` 前綴] → 需要實際測試確認；若不帶前綴，需改為比對 session 注入的 MCP server tool 清單
- [`.mcp.json` 中引用的 `${VAR}` 環境變數未定義] → `detect_missing_env_vars()` 會回報，log 中警告使用者
- [Docker 環境缺少 MCP runtime（如 npx）] → 已是現有問題，不因本次改動惡化
