## 1. 分離 tool_use 和 tool_result event_type（Backend）

- [x] [P] 1.1 修改 `executor.py` `_extract_display_message()` — 分離 tool_use/tool_result：非 MCP/非 Skill 的 tool_use blocks 回傳 `tool_use`；user event 回傳 `tool_result`；純 text 維持 `assistant`；混合事件依優先序 mcp > skill > tool_use > assistant（對應 spec: Preserve backward compatibility for existing event types）
- [x] [P] 1.2 修改 `copilot_executor.py` `on_event()` — Copilot executor tool event classification：`tool.execution_start`（非 MCP）→ `tool_use`；`tool.execution_complete`（非 MCP）→ `tool_result`；`tool.execution_progress`（非 MCP）→ `tool_use`；MCP tool events 維持 `mcp` 不變（對應 spec: Classify MCP tool calls as mcp event type）
- [x] 1.3 更新 `test_stream_output.py` 和 `test_event_classify.py` — 驗證新的 event_type 分類邏輯（tool_use / tool_result 分離、mixed events 優先序）

## 2. Frontend Filter 修正與 Tag 樣式

- [x] 2.1 更新 `JobDetail.vue` `tagLabel()` / `tagColor()` / `lineClass()` — 新增 `tool_use` 和 `tool_result` 的顯示樣式（tag、顏色、CSS class）

## 3. Milestone 高亮

- [x] 3.1 在 `JobDetail.vue` 新增 `isMilestone()` 判斷函數 — milestone 訊息識別與高亮，識別 milestone log entries（Clone complete、Session initialized、exited with code、執行完成等），並加上 `log-line-milestone` CSS class（對應 spec: Milestone log entries receive visual emphasis）
- [x] 3.2 新增 `.log-line-milestone` CSS 樣式 — accent 左邊框、半透明 accent 背景、粗體文字

## 4. Sticky 進度條

- [x] 4.1 在 `JobDetail.vue` 新增 `latestMilestone` computed property — 從 logs 陣列反向搜尋最後一筆符合 milestone 條件的 system 訊息（對應 spec: Sticky progress bar shows latest milestone）
- [x] 4.2 在 `.log-viewer` 內部頂端新增 sticky bar 元素 — `position: sticky; top: 0`，顯示最新 milestone message + elapsed time，無 milestone 時顯示 "Waiting for output..."
