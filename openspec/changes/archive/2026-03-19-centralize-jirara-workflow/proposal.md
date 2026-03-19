## Why

目前各 repo 需要自行在根目錄放置 CLAUDE.md 來定義自動化開發 SOP，導致流程定義分散、維護成本高。同時專案已從 pip/requirements.txt 遷移至 uv，system-spec.md 需要同步更新。透過 Claude Code CLI 的 `--append-system-prompt-file` 旗標，可以將 Jirara skill 集中注入，實現零侵入的統一開發流程。

## What Changes

- **executor.py 改用 `--append-system-prompt-file`**：執行 Claude Code 時注入 `jirara.md` 作為開發 SOP，取代依賴各 repo 自備 CLAUDE.md 的方式
- **簡化 executor prompt**：移除 callback API 相關指令（Jirara 自身已包含 Jira comment + Teams 通知的回報機制）
- **更新 system-spec.md**：反映 Python 改用 uv、開發流程改用 Jirara skill 注入、部署步驟調整
- **移除或簡化 callback router**：executor prompt 不再指示 Claude Code 呼叫 callback，改由 Jirara 的 Step 5-6/5-7 負責回報

## Capabilities

### New Capabilities

- `sop-injection`: 透過 `--append-system-prompt-file` 將集中管理的 Jirara skill 注入 Claude Code 執行環境，實現三層指令疊加（內建 system prompt → Jirara SOP → repo CLAUDE.md）

### Modified Capabilities

（無既有 specs）

## Impact

- **受影響程式碼**：`backend/services/executor.py`（CLI 呼叫方式）、`backend/routers/callback.py`（可能簡化或移除）
- **受影響文件**：`docs/system-spec.md`（技術選型、執行細節、部署步驟）
- **依賴變更**：Python 套件管理從 pip 改為 uv（已完成遷移，需更新文件）
- **向後相容**：各 repo 既有的 CLAUDE.md 仍會被 Claude Code 自動讀取，與 Jirara 注入內容並存，不會衝突
