## Why

目前 Job Detail 頁面的 log filter 除了 All 和 System 以外幾乎無法使用：「Tool」filter 查找不存在的 event_type（`tool_use` / `tool_result`），而「Assistant」filter 把 AI 文字回應和 tool 操作混在同一個 `assistant` type 裡。此外，在 All 視圖中所有訊息的視覺權重相同，使用者在長時間執行過程中難以快速掌握進度（如 clone 完成、PR 建立等關鍵里程碑）。

## What Changes

- 後端 event_type 分離：將非 MCP / 非 Skill 的 tool call 從 `assistant` 改為 `tool_use`，tool result 從 `user` 改為 `tool_result`，使前端 filter 能正確篩選
- Milestone 高亮：在 All 視圖中對關鍵系統訊息（clone complete、PR created、session initialized、執行完成）加上醒目的視覺樣式
- Sticky 進度條：在 log viewer 頂部固定顯示最新執行階段與經過時間，不隨 scroll 消失

## Capabilities

### New Capabilities

- `log-milestone-highlights`: Log viewer 中對關鍵里程碑訊息的視覺強調與 sticky 進度條

### Modified Capabilities

- `structured-job-output`: event_type 分類邏輯變更 — 新增 `tool_use` 與 `tool_result` 兩種 event_type，原本歸類為 `assistant` 的 tool call 和歸類為 `user` 的 tool result 將分離為獨立類型

## Impact

- 影響的後端檔案：`backend/services/executor.py`（`_extract_display_message()`）、`backend/services/copilot_executor.py`（`on_event()`）
- 影響的前端檔案：`frontend/src/pages/JobDetail.vue`（filter 邏輯、tag 樣式、milestone 高亮、sticky bar）
- 影響的測試：`backend/tests/test_stream_output.py`、`backend/tests/test_event_classify.py`
- 已有的 log 資料不受影響（歷史資料維持原 event_type，僅新產出的 log 使用新分類）
