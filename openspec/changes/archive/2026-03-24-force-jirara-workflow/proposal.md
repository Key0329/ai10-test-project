## Why

目前兩個執行引擎（Claude Code / Copilot SDK）都無法可靠地使用系統的 jirara 開發流程：

- **Claude Code**：只讀 clone 下來的 repo 的 `.claude/skills/`，如果 repo 沒有 jirara 或有自己的開發流程（如 `dev-flow`），就完全不走 jirara
- **Copilot SDK**：嘗試注入 jirara 到 `.github/skills/`，但如果 repo 已有同名目錄就跳過，且 repo 自帶的 skill 體系（如 `.claude/skills/dev-flow/`）會搶走控制權

已有 `sop-injection` spec 描述了 Claude Code 的 `--append-system-prompt-file` 機制，但尚未實作。本次 change 將同時涵蓋兩個引擎，確保所有任務強制走 jirara 流程。

## What Changes

- **Claude Code executor**：使用 `--append-system-prompt-file` 將 `jirara.md` 注入 system prompt，不依賴 repo 是否自帶 skill
- **Copilot executor**：`_inject_system_skills()` 改為強制覆蓋（即使 repo 已有 jirara 目錄），並在 prompt 中明確指定 jirara 優先於 repo 自帶的開發流程 skill
- 兩個引擎的 prompt 都加入指令：repo 自帶的其他 skill（如 api-creator、component-builder）照常使用，但開發流程以 jirara 為準

## Capabilities

### New Capabilities

- `copilot-jirara-injection`: Copilot SDK 執行引擎強制注入系統 jirara skill 並在 prompt 中指定其優先於 repo 自帶開發流程

### Modified Capabilities

- `sop-injection`: 補完 Claude Code 的 `--append-system-prompt-file` 注入實作，並加入 jirara 優先於 repo 自帶開發流程的 prompt 指令

## Impact

- 影響程式碼：
  - `backend/services/executor.py` — `build_claude_command()` 加入 `--append-system-prompt-file`
  - `backend/services/copilot_executor.py` — `_inject_system_skills()` 改為強制覆蓋、`_build_copilot_prompt()` / `_build_system_message()` 加入 jirara 優先指令
- 影響 specs：`sop-injection`（修改）、`copilot-jirara-injection`（新增）
- 不影響：前端 UI、DB schema、API 介面
