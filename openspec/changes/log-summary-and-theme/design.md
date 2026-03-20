## Context

目前前端使用暖色調主題（`--bg: #f8f7f4`），log viewer 中所有工具呼叫統一顯示為 `assistant` event_type。Job 執行完成後，使用者無法從 log 中直接看到 token 用量、成本、MCP/Skills 使用情況。

Backend executor 已使用 `--output-format stream-json` 執行 Claude Code，`result` 事件的 metadata 中包含 `total_cost_usd`、`usage`（input/output tokens）、`modelUsage`、`num_turns` 等欄位。工具呼叫的名稱在 `assistant` 事件的 `content[].name` 中，MCP 工具以 `mcp__<server>__<tool>` 命名，Skill 工具名稱為 `Skill`。

## Goals / Non-Goals

**Goals:**

- 將 CSS 主題從暖色調改為霧藍冷色調
- Job 結束時自動插入一筆摘要 system log（token、成本、MCP、Skills）
- MCP 和 Skill 工具呼叫在 log viewer 中以獨立顏色呈現

**Non-Goals:**

- 不改動 log viewer 的深色背景
- 不新增 DB 表，摘要以普通 log 行寫入 `job_logs`
- 不追蹤歷史趨勢或跨 job 統計

## Decisions

### 霧藍冷色調 CSS 變數

將 `:root` 變數從暖色系統一改為冷色：

| 變數 | 現值 | 新值 |
|------|------|------|
| `--bg` | `#f8f7f4` | `#e8ecf1` |
| `--surface` | `#ffffff` | `#f4f6f9` |
| `--surface-hover` | `#f5f4f1` | `#eaedf2` |
| `--border` | `#e8e5df` | `#d0d5dd` |
| `--border-hover` | `#d4d0c8` | `#b8bfc9` |
| `--text-dim` | `#6b6560` | `#5a6270` |
| `--text-hint` | `#a09890` | `#8a92a0` |

其他變數（`--text`、`--accent`、`--green`、`--amber`、`--red`、`--blue`、字體、`--radius`）不變。

**理由**：只動背景和邊框色系，保持功能色（accent、green、red 等）不變，最小化改動範圍。

### event_type 擴充：mcp 和 skill

在 `_extract_display_message` 中，根據 tool_use block 的 `name` 欄位分類：

- `name` 以 `mcp__` 開頭 → `event_type = "mcp"`，訊息前綴改為 `[mcp]`
- `name` 為 `Skill` → `event_type = "skill"`，訊息前綴改為 `[skill]`
- 其他 → 維持 `event_type = "assistant"`，前綴不變 `[tool]`

一個 assistant 事件可能包含多種 tool_use block，此時以最後一個 tool block 的分類為準（因為 `_extract_display_message` 回傳的是整個事件的合併訊息，event_type 取最高優先級：`mcp` > `skill` > `assistant`）。

**理由**：不改 DB schema，只是多了兩個 event_type 值，向後相容。

### 前端 log viewer 顏色

新增 CSS class：

- `.log-line-mcp` — 青色 `#5ec4d0`
- `.log-line-skill` — 金色 `#e0a854`
- `.log-tag` 對應底色也新增 MCP（青底）、SKL（金底）

前端 JobDetail.vue 在渲染 log line 時，根據 `event_type` 套用對應 class，filter 按鈕新增 MCP 和 Skill 選項。

### 執行摘要 log

在 `execute_job` 結束後（status 更新前），新增 `_emit_summary(job_id)` 函式：

1. 查詢該 job 的 `result` event metadata → 解析 `total_cost_usd`、`usage.output_tokens`、`usage.input_tokens`、`usage.cache_read_input_tokens`、`num_turns`
2. 查詢該 job 所有 `mcp` event_type logs → 用 regex `mcp__(\w+)__` 提取不重複的 server 名稱
3. 查詢該 job 所有 `skill` event_type logs → 從 message 提取 skill 名稱
4. 組合為格式化摘要字串，以 `event_type = "system"` 插入 `job_logs`

**理由**：摘要就是一筆 system log，前端不需要任何改動就能顯示。

## Risks / Trade-offs

- [Risk] 冷色調可能影響既有 badge 和 accent 色的視覺對比 → Mitigation：功能色不變，只調背景系，且霧藍 `#e8ecf1` 足夠淺，對比度不會有問題
- [Risk] 一個 assistant 事件含多種 tool_use 時，event_type 只能標一個 → Mitigation：以優先級取最高的（mcp > skill > assistant），且 metadata 裡完整 JSON 仍可追溯
- [Risk] Claude Code stream-json 格式未來可能變動 → Mitigation：摘要解析用 `.get()` 安全取值，缺少欄位時顯示 `N/A`
