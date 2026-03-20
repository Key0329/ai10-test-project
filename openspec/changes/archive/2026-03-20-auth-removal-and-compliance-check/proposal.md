## Why

1. **Auth 移除**：原本系統需要輸入 `API_TOKEN` 才能使用前端，但這是內部工具，使用者憑證（GitHub Token、Jira Token、Jira Email）由前端表單輸入即足夠，不需要額外一層 Bearer token 驗證。

2. **Credentials 來源釐清**：`GITHUB_TOKEN`、`JIRA_API_TOKEN`、`JIRA_EMAIL` 應只來自使用者在前端的輸入，不應受 server 端 `.env` 影響。

3. **自主執行指令**：Claude Code 在自動化流程中居然會停下來向使用者提問（learning mode 觸發），造成任務無法自動完成。

4. **規範合規驗收**：Job 執行完成後無法知道 Claude Code 是否有遵守 clone repo 內的 CLAUDE.md 和 skills 規範。

## What Changes

- 移除後端 `verify_token` Bearer auth，所有 API route 不再需要 token
- 移除前端 `TokenGate` 登入頁、`router.beforeEach` guard、`Authorization` header
- Executor subprocess 明確排除 `GITHUB_TOKEN`、`JIRA_API_TOKEN`、`JIRA_EMAIL` 從 `os.environ` 繼承
- Prompt 加入強制自主執行規則（不得提問、不呈現方案）
- Prompt 明確指定以 cwd（clone 下來的 target repo）的 CLAUDE.md 和 skills 為規範
- Skills 驗證邏輯改為辨識 folder/SKILL.md 格式
- 新增 `_emit_compliance_check`：執行完成後掃 `git diff HEAD`，對照每個 skill 的 code pattern 回報合規結果

## Capabilities

### New Capabilities

- `compliance-check`：Job 完成後自動掃 git diff，對照 repo skills pattern 回報驗收結果
- `autonomous-prompt`：強制 CC 自主執行，不中斷等待使用者輸入

### Modified Capabilities

- `auth`：移除 API_TOKEN Bearer token 驗證層
- `credential-isolation`：Subprocess 環境變數明確排除 server 端 credentials
- `skill-discovery`：支援 folder/SKILL.md 格式的 skills 辨識
- `repo-config-verify`：改為驗收執行結果，而非只檢查檔案是否存在

## Impact

- 受影響的程式碼：
  - `backend/main.py` — 移除 `verify_token`、`API_TOKEN`、`Depends`
  - `backend/services/executor.py` — credential 隔離、prompt 規則、合規驗收
  - `frontend/src/api.js` — 移除 Bearer token、`setToken`、`getStoredToken`
  - `frontend/src/router.js` — 移除 `TokenGate`、`beforeEach` guard
- 不影響：DB schema、Queue、Job 流程、PR 推送
