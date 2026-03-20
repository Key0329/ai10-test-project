## Context

系統原本有一層 `API_TOKEN` Bearer auth，使用者需先在 `TokenGate` 頁面輸入 token 才能使用。此外，Claude Code 在執行 job 時會受全域設定影響（learning mode），導致中途提問；執行完成後也無法確認是否遵守了 target repo 的開發規範。

## Goals / Non-Goals

**Goals:**

- 移除不必要的 API_TOKEN 驗證層
- 確保 credentials 只來自前端使用者輸入
- CC 執行時嚴格自主，不中斷提問
- Job 完成後自動回報是否遵守 target repo 的 CLAUDE.md 和 skills

**Non-Goals:**

- 新增其他 auth 機制（這是內部工具，不需要）
- 強制擋 PR（合規檢查只回報，不阻擋）
- 解析 skill 語意（只做 code pattern keyword 比對）

## Decisions

### 移除 Bearer token auth

直接從 `main.py` 移除 `verify_token` function 和 `dependencies=[Depends(verify_token)]`，前端移除 `Authorization` header 和 `TokenGate`。

**理由：** 使用者已透過 GitHub Token / Jira Token 驗證身份，雙重驗證對內部工具無意義。

### Credential 隔離

```python
_credential_keys = {"GITHUB_TOKEN", "JIRA_API_TOKEN", "JIRA_EMAIL"}
base_env = {k: v for k, v in os.environ.items() if k not in _credential_keys}
```

**理由：** 防止 server `.env` 內的 credentials 污染 subprocess 環境，確保只吃使用者輸入。

### Prompt 自主執行規則

在 prompt header 加入明確規則，覆蓋 repo CLAUDE.md 可能的 learning mode 設定。

**理由：** Claude Code 讀到 learning mode 設定後會停下來向使用者提問，在無人監控的自動化流程中無法處理。Prompt 指令優先級高於 CLAUDE.md。

### 規範以 cwd 為準

Prompt 明確說明「cwd 就是 target repo，遵守該目錄的 CLAUDE.md 和 skills」，避免 CC 誤以為要遵守執行系統本身的規範。

**理由：** 每次 clone 的 repo 語言和規範不同，不能寫死。

### Compliance Check：git diff + keyword scan

```python
keywords = _extract_skill_keywords(skill_content)  # 從 code block 抽 token
matched = [kw for kw in keywords if kw in diff_content]
```

**理由：** `Skill()` tool 呼叫次數不等於規範有被遵守（CC 可能直接套用 pattern 而不呼叫 tool）。掃 git diff 的實際改動更能反映合規狀況。

**替代方案：** 要求 CC 自己回報驗收結果——依賴 CC 自我評估，容易被 learning mode 或其他行為干擾。

## Risks / Trade-offs

- **Keyword scan 誤判**：skill 的 keyword 可能在不相關的上下文出現 → 目前接受此誤差，回報結果僅供參考
- **git diff 為空**：若 clone 後沒有 commit（只有 working tree 變動）→ fallback 到 `git show HEAD`
- **移除 auth**：內部工具可接受，若日後需要對外開放需補上其他 auth 機制
