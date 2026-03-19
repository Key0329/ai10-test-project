## Context

目前系統依照 `docs/system-spec.md` 的設計，由 `executor.py` 透過 `claude -p --dangerously-skip-permissions` 執行 Claude Code，開發 SOP 依賴各目標 repo 自行在根目錄放置 CLAUDE.md。完成回報則是透過 prompt 中指示 Claude Code curl callback API。

現狀問題：
- SOP 分散在各 repo，維護成本高且品質不一
- Callback 機制與 Jirara skill 自帶的 Jira comment + Teams 通知功能重複
- system-spec.md 仍記載 pip/requirements.txt，但專案已遷移至 uv

## Goals / Non-Goals

**Goals:**

- executor.py 改用 `--append-system-prompt-file` 注入 Jirara skill，集中管理開發 SOP
- 簡化 executor prompt，移除 callback 相關指令
- 更新 system-spec.md 反映 uv 遷移與新流程
- 保持與各 repo 既有 CLAUDE.md 的向後相容性

**Non-Goals:**

- 不修改 Jirara skill 本身的流程邏輯
- 不移除 callback router（保留供未來或其他用途），僅從 executor prompt 中移除
- 不改動前端 UI 或 Job Queue 機制

## Decisions

### 使用 --append-system-prompt-file 注入 Jirara

選擇 `--append-system-prompt-file` 而非 `--system-prompt-file`，因為 append 模式保留 Claude Code 內建 system prompt（工具能力），只在後面追加 Jirara SOP。

替代方案：
- **寫入 cloned repo 的 CLAUDE.md**：需要修改 clone 下來的檔案，侵入性高
- **整包塞進 -p prompt**：prompt 過長（~600 行），且語意上 SOP 屬於 system prompt 而非 user message
- **複製 skill 到 cloned repo 的 .claude/skills/**：skill 在 -p 模式下的自動載入行為不確定

### 直接使用含 frontmatter 的 jirara.md

不額外維護去除 frontmatter 的版本。frontmatter 僅 5 行 YAML metadata，Claude 能自然理解為 metadata 而不受干擾。維護單一檔案避免 drift 風險。

### Jirara 檔案路徑使用絕對路徑

executor.py 中以本專案的安裝路徑為基準，組合 `.claude/skills/jirara.md` 的絕對路徑傳給 `--append-system-prompt-file`。不硬編碼路徑，透過 `__file__` 或環境變數動態解析。

### 保留 callback router 但不主動呼叫

executor.py 的 prompt 不再包含 callback 指令，但 `backend/routers/callback.py` 保留不刪除。Jirara 自帶的回報機制（Jira comment + Teams 通知）成為主要完成通知管道。Job 狀態仍由 executor.py 根據 Claude Code 的 exit code 更新。

## Risks / Trade-offs

- **Jirara frontmatter 干擾** → 機率極低；若發生，executor.py 加 runtime strip 即可修復
- **Jirara.md 路徑錯誤導致 Claude Code 啟動失敗** → executor.py 啟動時驗證檔案存在
- **Job 狀態與 Jirara 回報不一致**（例如 Jirara 認為完成但 process exit code 非 0）→ 以 exit code 為準更新 DB 狀態，Jirara 的 Jira/Teams 通知作為補充通知
