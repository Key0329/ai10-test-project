## Context

系統已支援從 repo `.mcp.json` 動態讀取 MCP 設定（`dynamic-repo-mcp` change），並有 `detect_missing_env_vars()` 可偵測未定義的 `${VAR}`。但目前沒有任何機制讓使用者在送 job 前提供這些 token。

現有資料流：前端 `mcp_tokens` → `mcp_registry.build_session_config()` → executor。這條路只服務內建 MCP 的 token（如 Sentry），不處理 repo `.mcp.json` 中的 `${VAR}` 展開。

## Goals / Non-Goals

**Goals:**

- 使用者選好 repo 後，自動掃描 `.mcp.json` 需要的 token
- 動態生成 token 輸入欄位，使用者填入後隨 job 送出
- 兩種模式（Claude Code / Copilot）都能使用這些 token

**Non-Goals:**

- 不做 token 持久化儲存（不存 DB、不做加密）
- 不做 repo 的完整 clone（scan 用 GitHub API 輕量 fetch 單一檔案）
- 不改動內建 MCP 的既有 token 機制

## Decisions

### 用 GitHub API 輕量 fetch .mcp.json

新增 `POST /api/v1/mcp/scan` 端點，用 GitHub Contents API（`GET /repos/{owner}/{repo}/contents/.mcp.json`）fetch 單一檔案，不做 git clone。

需要前端傳入 `repo_url`、`branch`（可選）和 `github_token`。回傳 `missing_vars: string[]` 和 `servers: string[]`。

替代方案：做 shallow clone 再讀檔。不採用，因為 clone 即使 shallow 也比單一 API call 慢很多。

### 用 env_overrides dict 傳遞使用者填入的 token

在 `JobCreate` model 新增 `env_overrides: dict[str, str]` 欄位，與現有的 `mcp_tokens` 平行。`env_overrides` 是通用的環境變數覆蓋，key 是 `${VAR}` 中的 VAR_NAME，value 是使用者填入的值。

Copilot 模式：傳入 `convert_to_copilot_format(mcp_servers, env_overrides=...)` 展開。
Claude Code 模式：注入到子進程的 `env` dict 中。

替代方案：複用現有 `mcp_tokens`。不採用，因為 `mcp_tokens` 的 key 是 MCP server ID，而 `env_overrides` 的 key 是環境變數名稱，語意不同。

### 前端 repo 選擇後自動觸發 scan

在 `NewJob.vue` 中 watch `form.repo_url` 變化，debounce 後自動呼叫 scan API。scan 回傳的 `missing_vars` 動態渲染為 password input 欄位。

使用者填入的值存在 `envOverrides` reactive ref 中，submit 時隨 job 送出。

## Risks / Trade-offs

- [GitHub API rate limit] → 使用使用者提供的 `github_token` 認證，authenticated rate limit 為 5000/hr，足夠
- [Private repo 權限] → scan API 使用前端傳入的 `github_token`，與 clone 用同一個 token
- [.mcp.json 不存在] → scan 回傳空結果，不顯示 token 欄位，與現行行為一致
- [Branch 未指定] → 預設讀取 repo 的 default branch
