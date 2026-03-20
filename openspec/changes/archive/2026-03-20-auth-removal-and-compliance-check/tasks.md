## 1. Auth 移除

- [x] 1.1 移除 `backend/main.py` 的 `API_TOKEN`、`verify_token` function、`Depends(verify_token)` 依賴
- [x] 1.2 移除 `frontend/src/api.js` 的 `getToken`、`setToken`、`getStoredToken`、`Authorization` header、SSE token query param
- [x] 1.3 移除 `frontend/src/router.js` 的 `TokenGate` import、`/login` route、`beforeEach` guard

## 2. Credential 隔離

- [x] 2.1 在 `executor.py` 的 subprocess env 建立前，明確從 `os.environ` 排除 `GITHUB_TOKEN`、`JIRA_API_TOKEN`、`JIRA_EMAIL`

## 3. Prompt 規則強化

- [x] 3.1 加入自主執行規則（不得提問、不呈現方案、不確定時取最保守做法）
- [x] 3.2 加入規範遵守規則（以 cwd 的 CLAUDE.md 和 skills 為準，開始前先閱讀，不可假設）

## 4. Skills 辨識修正

- [x] 4.1 `_verify_repo_config` 支援 folder/SKILL.md 格式（不只是直接放 .md）
- [x] 4.2 `_emit_compliance_check` 同步支援 folder 格式

## 5. 合規驗收

- [x] 5.1 新增 `_read_skill_content` — 讀取 skill 的 description 和完整內容
- [x] 5.2 新增 `_extract_skill_keywords` — 從 skill code block 抽取關鍵 pattern tokens
- [x] 5.3 `_emit_compliance_check` 執行 `git diff HEAD` 取得本次改動
- [x] 5.4 掃 diff 與每個 skill 的 keywords 交叉比對，輸出 ✅/⚠️ 驗收結果
