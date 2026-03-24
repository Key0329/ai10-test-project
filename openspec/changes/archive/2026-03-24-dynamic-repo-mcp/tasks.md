## 1. 新建 mcp_loader 模組處理格式轉換

- [x] [P] 1.1 建立 `backend/services/mcp_loader.py`，實作 `load_repo_mcp_config(work_dir)` 讀取 `.mcp.json` 並回傳 `mcpServers` dict（涵蓋 Load MCP configuration from repo .mcp.json）
- [x] [P] 1.2 實作 `convert_to_copilot_format(mcp_servers, env_overrides)` 格式轉換，處理 stdio→local、sse/streamable-http→http 映射（涵蓋 Convert .mcp.json format to Copilot SDK format）
- [x] [P] 1.3 實作 `${VAR}` 環境變數展開邏輯，支援 args、env values、url 欄位（涵蓋 Expand environment variable references）
- [x] [P] 1.4 實作 `detect_missing_env_vars(mcp_servers)` 回傳未定義的環境變數清單（涵蓋 Detect missing environment variables）

## 2. Executor repo 驗證增加 .mcp.json 偵測

- [x] [P] 2.1 修改 `backend/services/executor.py` 的 `_verify_repo_config()`，增加 `.mcp.json` 偵測 log，顯示 server 數量和名稱（涵蓋 Log .mcp.json detection in repo verification）
- [x] [P] 2.2 修改 `backend/services/copilot_executor.py` 的 `_verify_copilot_repo_config()`，增加相同的 `.mcp.json` 偵測 log

## 3. Copilot Executor 整合 repo MCP 載入

- [x] 3.1 在 `backend/services/copilot_executor.py` clone 後呼叫 `load_repo_mcp_config()` + `convert_to_copilot_format()`，取得 repo MCP config
- [x] 3.2 實作 repo MCP 與補充 MCP 的合併策略：Merge repo MCP config with supplemental MCP 合併邏輯（repo 優先），注入 `session_config["mcp_servers"]`
- [x] 3.3 Log 最終載入的 MCP 清單（含 repo 來源和補充來源）

## 4. Copilot MCP 追蹤對齊 Claude Code 邏輯

- [x] 4.1 修改 `copilot_executor.py` 的 `on_event` handler，在 `tool.execution_start` / `tool.execution_complete` 偵測 `mcp__` 前綴，標記 `event_type="mcp"`（涵蓋 Copilot executor classifies MCP tool events）
- [x] 4.2 在 Copilot executor 任務完成時，實作 Collect MCP server names from logs 統計，輸出格式與 Claude Code 的 `_emit_summary()` 一致（涵蓋 Copilot executor emits MCP summary + Emit execution summary log on job completion）

## 5. 前端 UI 調整

- [x] 5.1 修改 `frontend/src/pages/NewJob.vue`，Copilot 模式的 MCP section 標題改為「額外 MCP（補充 repo 設定）」（涵蓋 MCP section displays supplemental role label）
- [x] 5.2 Claude Code 模式下顯示 MCP 自動載入提示文字（涵蓋 Claude Code mode MCP info）

## 6. 測試

- [x] [P] 6.1 為 `mcp_loader.py` 撰寫單元測試：讀取、格式轉換、env 展開、missing var 偵測
- [x] [P] 6.2 為 Copilot MCP event 分類邏輯撰寫測試：`mcp__` 前綴偵測
