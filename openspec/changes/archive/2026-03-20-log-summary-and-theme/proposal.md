## Why

目前前端背景為暖色調米白（`#f8f7f4`），使用者希望改為藍灰冷色調以提升專業感。同時，Job 執行完成後缺乏使用量摘要（token、成本、MCP、Skills），使用者需要在 log viewer 結尾快速掌握每次執行的資源消耗。此外，MCP 與 Skill 工具呼叫在 log 中與一般工具混在一起，無法一眼辨識。

## What Changes

- 將 CSS 主題從暖色淺底改為霧藍冷色調（`--bg: #e8ecf1`），連帶調整 `--surface`、`--border`、`--surface-hover` 等變數
- Executor 在 job 結束後，從 `result` event metadata 解析 token/cost 資訊，從 assistant logs 提取 MCP server 與 Skill 使用紀錄，插入一筆 system log 作為執行摘要
- 新增 `mcp` 和 `skill` 兩種 event_type，backend 解析 tool_use 時依工具名稱前綴分類，前端 log viewer 以不同顏色呈現

## Capabilities

### New Capabilities

- `job-execution-summary`: Job 完成時自動產生執行摘要 log，包含 token 用量、成本、使用到的 MCP servers 與 Skills

### Modified Capabilities

- `vue-frontend`: CSS 主題改為霧藍冷色調；log viewer 新增 MCP/Skill 顏色樣式
- `structured-job-output`: 新增 `mcp`、`skill` event_type 分類；executor 結尾插入摘要 log

## Impact

- 受影響的 specs：`vue-frontend`、`structured-job-output`、`job-execution-summary`（新增）
- 受影響的程式碼：
  - `frontend/src/app.css` — 主題色彩變數 + log viewer 新樣式
  - `frontend/src/pages/JobDetail.vue` — log line 顏色對應
  - `backend/services/executor.py` — event_type 分類邏輯 + 摘要產生
