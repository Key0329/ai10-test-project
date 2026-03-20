## 1. 霧藍冷色調 CSS 變數

- [x] [P] 1.1 更新 `frontend/src/app.css` `:root` 變數為霧藍冷色調（light-dark mixed theme with dual font strategy），包含 `--bg`、`--surface`、`--surface-hover`、`--border`、`--border-hover`、`--text-dim`、`--text-hint`

## 2. Backend event_type 擴充：mcp 和 skill

- [x] [P] 2.1 修改 `backend/services/executor.py` 的 `_extract_display_message`，classify MCP tool calls as mcp event type（`mcp__` 前綴 → `event_type = "mcp"`、`[mcp]` 前綴）
- [x] [P] 2.2 修改 `_extract_display_message`，classify Skill tool calls as skill event type（`Skill` → `event_type = "skill"`、`[skill]` 前綴）
- [x] 2.3 處理 multiple tool_use blocks with mixed types 的優先級邏輯（`mcp` > `skill` > `assistant`），確保 preserve backward compatibility for existing event types

## 3. 執行摘要 log

- [x] 3.1 新增 `_emit_summary(job_id)` 函式，parse token and cost data from result event（`total_cost_usd`、`usage.input_tokens`、`usage.output_tokens`、`usage.cache_read_input_tokens`、`num_turns`）
- [x] 3.2 在 `_emit_summary` 中 collect MCP server names from logs（查詢 `event_type = "mcp"` 的 log，用 regex 提取 server 名稱）
- [x] 3.3 在 `_emit_summary` 中 collect skill names from logs（查詢 `event_type = "skill"` 的 log，提取 skill 名稱）
- [x] 3.4 組合摘要字串並以 `event_type = "system"` 插入 `job_logs`，在 `execute_job` 結束前呼叫（emit execution summary log on job completion）

## 4. 前端 log viewer 顏色：MCP/Skill 樣式

- [x] [P] 4.1 在 `frontend/src/app.css` 新增 `.log-line-mcp`（青色 `#5ec4d0`）和 `.log-line-skill`（金色 `#e0a854`）CSS class，以及對應 `.log-tag` 底色（MCP and Skill log line colors）
- [x] [P] 4.2 修改 `frontend/src/pages/JobDetail.vue`，根據 `event_type` 為 `mcp` 和 `skill` 套用對應 CSS class 和 tag 標籤
- [x] 4.3 在 JobDetail.vue log filter 按鈕中新增 MCP 和 Skill 選項（log filter includes MCP and Skill options）

## 5. 測試

- [x] 5.1 撰寫 `_extract_display_message` 的單元測試，驗證 mcp/skill event_type 分類和 backward compatibility
- [x] 5.2 撰寫 `_emit_summary` 的單元測試，驗證 token/cost 解析、MCP/Skill 收集、missing result metadata 處理
