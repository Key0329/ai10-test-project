## Context

系統有兩個執行引擎：Claude Code（CLI）和 Copilot SDK，各自有不同的 skill 載入機制：

- **Claude Code**：以 subprocess 執行 `claude -p`，cwd 為 clone 下來的 repo，CLI 自動掃描 `.claude/skills/` 和 `~/.claude/skills/`
- **Copilot SDK**：透過 `CopilotClient` 建立 session，以 `skill_directories` 參數指定 skill 路徑

目前 Claude Code 完全不注入系統 jirara（雖然 `sop-injection` spec 已描述此需求但未實作）。Copilot 嘗試注入但採「不覆蓋」策略，當 repo 自帶 skill 體系時會被繞過。

系統的 jirara skill 位於 `.github/skills/jirara/jirara.md`（相對於專案根目錄）。

## Goals / Non-Goals

**Goals:**

- 兩個引擎都強制使用系統 jirara 作為開發流程
- Repo 自帶的其他 skill（如 api-creator、component-builder）不受影響
- 若 repo 有自己的開發流程 skill（如 dev-flow），jirara 優先

**Non-Goals:**

- 不加 UI toggle（先強制，未來有需要再加）
- 不改 DB schema 或 API 介面
- 不改 jirara.md 本身的內容

## Decisions

### Claude Code：使用 --append-system-prompt-file 注入 jirara

在 `build_claude_command()` 加入 `--append-system-prompt-file <path>` 參數，將 jirara.md 全文注入 system prompt。

**替代方案**：
- 將 jirara 內容塞進 user prompt → 佔用 user prompt 空間，且語意上 SOP 屬於 system 層級指令
- 複製 jirara.md 到 clone 的 repo 內 → 污染 work_dir，可能被 commit 進 repo

選擇 `--append-system-prompt-file` 是因為：不修改 repo、語意正確（SOP 是系統指令）、且 `sop-injection` spec 已定義此機制。

### Copilot SDK：強制覆蓋注入 + prompt 指定優先級

`_inject_system_skills()` 改為：若 target repo 的 `.github/skills/jirara/` 已存在，先刪除再重新複製系統版本（確保使用最新版）。

`_build_copilot_prompt()` 和 `_build_system_message()` 加入明確指令：

- 「jirara skill 為最高優先的開發流程，repo 自帶的開發流程 skill（如 dev-flow）不得覆蓋 jirara 步驟」
- 「repo 自帶的其他 skill（非開發流程類）照常套用」

### Jirara 檔案路徑：從專案根目錄動態解析

兩個引擎共用的 jirara.md 路徑從 `_PROJECT_ROOT` 動態解析（`copilot_executor.py` 已有此變數），`executor.py` 也新增同樣的路徑解析，指向 `.github/skills/jirara/jirara.md`。

## Risks / Trade-offs

- **[Risk] repo 自帶 skill 與 jirara 有功能重疊導致 LLM 混淆** → 在 prompt 中明確指定「jirara 為開發流程主幹，其他 skill 為輔助」，降低衝突
- **[Risk] Copilot SDK 強制覆蓋可能在 commit 時把系統 jirara 帶進 repo** → jirara 注入到 `.github/skills/`，而 Copilot 的 dev-flow 通常用 `.claude/skills/`，且 jirara 流程本身有明確的 git add 指令不會加入不相關檔案
- **[Trade-off] 無 toggle 代表無法讓特定 repo 用自己的流程** → 先以強制模式收集回饋，未來有需求再加 `skill_mode` toggle
