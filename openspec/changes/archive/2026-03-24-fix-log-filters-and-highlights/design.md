## Context

Job Detail 頁面的 log viewer 有兩類問題：（1）filter 按鈕除 All / System 外無法正常運作，原因是 backend event_type 分類與前端 filter 預期不一致；（2）All 視圖中所有訊息視覺權重相同，長時間執行時難以快速掌握進度。

現有架構：
- Backend 透過 `_extract_display_message()`（Claude Code）和 `on_event()`（Copilot）將 stream-json 事件分類為 `assistant` / `mcp` / `skill` / `user` / `system` / `result` / `raw`
- Frontend 透過 SSE 接收 log entries，以 `event_type` 和 `stream` 欄位做 filter / 樣式
- 兩個 executor 共用相同的 `_log()` 寫入 `job_logs` table

## Goals / Non-Goals

**Goals:**

- 前端所有 filter 按鈕都能正確篩選對應類型的訊息
- 在 All 視圖中，關鍵里程碑訊息有醒目的視覺區分
- Log viewer 頂部有 sticky 進度條，即時顯示最新階段

**Non-Goals:**

- 不改動 DB schema（不新增欄位，只改 event_type 的值）
- 不做 error toast（B3，後續再議）
- 不改 SSE streaming 機制
- 不處理歷史 log 資料的回填（舊資料維持原 event_type）

## Decisions

### 分離 tool_use 和 tool_result event_type

將非 MCP / 非 Skill 的 tool call 從 `assistant` 分離為 `tool_use`，tool result 從 `user` 分離為 `tool_result`。

**替代方案考量：**
- 在前端 filter 端做映射（`assistant` 中判斷 message 前綴 `[tool]`）→ 太脆弱，依賴字串格式
- 新增 sub_type 欄位 → 過度設計，改 event_type 值足夠

**executor.py `_extract_display_message()` 變更：**
- 當 assistant event 只包含 tool_use blocks（無 text blocks、無 MCP、無 Skill）→ refined_type = `tool_use`
- user event（tool result）→ 直接回傳 `tool_result` 而非 `user`

**copilot_executor.py `on_event()` 變更：**
- `tool.execution_start`（非 MCP）→ event_type = `tool_use`
- `tool.execution_complete`（非 MCP）→ event_type = `tool_result`
- `tool.execution_progress` → event_type = `tool_use`（屬於 tool 執行過程）

### Milestone 訊息識別與高亮

在前端以 pattern matching 識別里程碑訊息，加上 `log-line-milestone` CSS class。

**識別規則（基於 message 內容）：**
- `Clone complete`
- `Session initialized`
- `PR base branch`
- `Running claude -p` / `Starting SDK session`
- `exited with code` / `執行完成`
- message 包含 `PR created` 或 `pr_url`

**視覺樣式：**
- 左邊加 3px 粗色條（accent color）
- 背景略亮（半透明 accent）
- 字體加粗

### Sticky 進度條

在 `.log-viewer` 內部頂端加一個 `position: sticky; top: 0` 的 bar，內容為最新一筆 milestone 訊息 + elapsed time。

**資料來源：** 從 `logs` 陣列中反向搜尋最後一筆符合 milestone 條件的 system 訊息。
**更新時機：** 每次有新 log push 進來時重新計算（computed property）。
**顯示格式：** `📍 {milestone message} · {elapsed time}`

## Risks / Trade-offs

- **[Risk] 混合事件的 event_type 選擇** — 一個 assistant event 可能同時包含 text block 和 tool_use block。→ 沿用現有優先序：mcp > skill > tool_use > assistant。若同時有 text 和 tool_use，歸類為 `tool_use`（工具操作比純文字更重要）。
- **[Risk] Milestone pattern 維護成本** — 前端硬編碼 pattern 字串。→ 可接受，這些 system 訊息由我們自己的 backend 產出，格式穩定。
- **[Risk] Sticky bar 佔用 log viewer 空間** — → bar 高度固定約 32px，影響可忽略。背景設為不透明避免文字重疊。
