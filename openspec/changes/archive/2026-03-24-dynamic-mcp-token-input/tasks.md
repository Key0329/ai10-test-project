## 1. 後端：用 GitHub API 輕量 fetch .mcp.json

- [x] [P] 1.1 在 `backend/services/mcp_loader.py` 新增 `scan_repo_mcp_json(repo_url, branch, github_token)` 函數，用 GitHub Contents API fetch `.mcp.json` 並回傳 `missing_vars` 和 `servers`（涵蓋 Scan repo .mcp.json via GitHub API）
- [x] [P] 1.2 在 `backend/routers/mcp.py` 新增 `POST /api/v1/mcp/scan` 端點，呼叫 scan 函數並回傳結果

## 2. 後端：用 env_overrides dict 傳遞使用者填入的 token

- [x] 2.1 在 `backend/models/job.py` 的 `JobCreate` model 新增 `env_overrides: dict[str, str]` 欄位（涵蓋 Accept env_overrides for variable expansion）
- [x] 2.2 修改 `backend/routers/jobs.py`，將 `payload.env_overrides` 傳遞到 executor
- [x] 2.3 修改 `backend/services/copilot_executor.py`，將 `env_overrides` 傳入 `convert_to_copilot_format()` 展開（Copilot mode with env_overrides）
- [x] 2.4 修改 `backend/services/executor.py`，將 `env_overrides` 注入 Claude Code 子進程的環境變數（Claude Code mode with env_overrides）

## 3. 前端 repo 選擇後自動觸發 scan 並動態生成 token 欄位

- [x] 3.1 在 `frontend/src/api.js` 新增 `scanRepoMcp(repo_url, branch, github_token)` API 呼叫
- [x] 3.2 修改 `frontend/src/pages/NewJob.vue`，watch repo_url 變化後 debounce 呼叫 scan API（涵蓋 Frontend auto-scans on repo selection）
- [x] 3.3 根據 scan 結果動態渲染 Dynamic MCP token input fields（password input，label 為變數名稱）
- [x] 3.4 submit 時將使用者填入的值作為 `env_overrides` 送出（涵蓋 Both modes show token fields）

## 4. 測試

- [x] [P] 4.1 為 `scan_repo_mcp_json()` 撰寫單元測試（mock GitHub API）
- [x] [P] 4.2 為 env_overrides 在兩種 executor 模式下的注入撰寫測試
