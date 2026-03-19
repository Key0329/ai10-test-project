# Claude Remote Agent — System Specification

| 項目 | 內容 |
|------|------|
| 文件版本 | 1.0 |
| 建立日期 | 2026-03-19 |
| 狀態 | **Draft** |
| 目標讀者 | 開發團隊 / 技術主管 |

---

## 1. 專案概述

本系統旨在為團隊提供一個共用的自動化開發平台。團隊成員透過內部 Web 介面提交 Jira 工單資訊，系統會自動在 Mac Mini 上執行 Claude Code CLI，依據 repo 內預定義的開發流程（CLAUDE.md / Skills），完成從讀取需求、撰寫程式碼、執行測試到建立 Pull Request 的全自動開發流程。

### 1.1 目標

- **降低重複性開發工作：** 讓 AI 處理結構明確、規格清楚的 Jira 工單，釋放開發者時間。
- **統一開發流程：** 透過 CLAUDE.md 定義標準開發 SOP，確保每次自動開發的產出品質一致。
- **不改變現有工作流：** 同事在熟悉的 Web 介面操作，結果以 Pull Request 形式進入正常 code review 流程。

### 1.2 非目標（Scope 外）

- 本系統不會取代 code review，也不會直接 merge PR。
- 本系統不處理需求模糊或需要大量討論的工單。
- 本系統不負責 Jira 工單的建立與管理。

---

## 2. 系統架構

採用方案一：前後端全部部署在同一台 Mac Mini 上。Mac Mini 同時扮演 Web Server、Job Scheduler 與 Claude Code 執行器三個角色。

### 2.1 架構總覽

```
同事瀏覽器 → 前端 (React) → 後端 API (FastAPI) → Job Queue → Claude Code CLI → GitHub PR
```

```
┌─ 同事 A/B/C 的瀏覽器 ──┐
│  http://192.168.x.x:8000 │
└───────────┬──────────────┘
            │
┌───────────▼──────────────────────────────────┐
│              Mac Mini (192.168.x.x)           │
│                                               │
│  ┌─────────────┐    ┌──────────────────┐      │
│  │ React 前端   │───→│ FastAPI 後端      │      │
│  │ (靜態檔案)   │    │ (port 8000)      │      │
│  └─────────────┘    └────────┬─────────┘      │
│                              │                │
│                     ┌────────▼─────────┐      │
│                     │ SQLite Job Queue  │      │
│                     └────────┬─────────┘      │
│                              │ subprocess     │
│                     ┌────────▼─────────┐      │
│                     │ Claude Code CLI   │      │
│                     │ -p --dangerous    │      │
│                     └────────┬─────────┘      │
│                              │                │
│                     ┌────────▼─────────┐      │
│                     │ git push + PR     │      │
│                     └──────────────────┘      │
└───────────────────────────────────────────────┘
```

### 2.2 技術選型

| 層級 | 技術 | 選型理由 |
|------|------|----------|
| 前端 | React + Vite | 輕量、build 後為靜態檔案，由後端 serve |
| 後端 | Python FastAPI | async 支援好、自動產生 API docs、型別安全 |
| Job Queue | SQLite + asyncio | 零外部依賴、單機佇列管理、資料持久化不怕重啟 |
| CLI 執行 | Claude Code (-p mode) | Max 訂閱的 CLI，non-interactive print mode |
| 版本控制 | git + GitHub CLI (gh) | 自動 clone、push、建 PR |
| 套件管理 | uv | 取代 pip/requirements.txt，速度快、支援 lockfile、相容 pyproject.toml |
| 即時通知 | Server-Sent Events (SSE) | 單向推送 job 狀態更新到前端 |

### 2.3 部署環境

| 項目 | 規格 |
|------|------|
| 機器 | Mac Mini (Apple Silicon) |
| OS | macOS Sonoma 或以上 |
| Python | 3.11+（需安裝 [uv](https://docs.astral.sh/uv/) 做套件管理） |
| Node.js | 20+ (for Claude Code CLI) |
| 網路 | 固定內網 IP，防火牆開放 port 8000 |
| 存取方式 | `http://192.168.x.x:8000`（內網） |

---

## 3. API 設計

所有 API 路徑以 `/api/v1` 為前綴。前端靜態檔案由根路徑 `/` serve。

### 3.1 端點總覽

| Method | Path | 說明 | 認證 |
|--------|------|------|------|
| POST | /api/v1/jobs | 建立新的開發 Job | Bearer Token |
| GET | /api/v1/jobs | 列出所有 Jobs（支援分頁） | Bearer Token |
| GET | /api/v1/jobs/{id} | 取得單一 Job 詳情 | Bearer Token |
| GET | /api/v1/jobs/{id}/logs | 串流 Job 即時 log（SSE） | Bearer Token |
| POST | /api/v1/jobs/{id}/cancel | 取消執行中的 Job | Bearer Token |
| POST | /api/v1/callback | Claude Code 完成回呼 | Internal |
| GET | /api/v1/health | 健康檢查 | 無 |

### 3.2 建立 Job — POST /api/v1/jobs

**Request Body:**

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| repo_url | string | 是 | Git repo 完整 URL |
| jira_ticket | string | 是 | Jira 工單編號（如 JRA-123） |
| branch | string | 否 | 指定 clone 的 branch，預設 main |
| extra_prompt | string | 否 | 額外指令（附加在主 prompt 之後） |
| priority | integer | 否 | 優先級 1-5，預設 3（數字越小越優先） |
| requested_by | string | 否 | 提交者名稱（前端自動帶入） |

**Response (202 Accepted):**

| 欄位 | 型別 | 說明 |
|------|------|------|
| job_id | string | 唯一 Job ID（格式：JRA-123-1710000000） |
| status | string | 初始狀態：queued |
| position | integer | 在 queue 中的位置 |
| created_at | string | ISO 8601 時間戳 |

### 3.3 Job 狀態流轉

```
queued → cloning → running → pushing → completed
                                    ↘ failed
            （任何階段都可能轉為 failed 或 cancelled）
```

| 狀態 | 說明 | 可轉換至 |
|------|------|----------|
| queued | 已排入佇列，等待執行 | cloning, cancelled |
| cloning | 正在 git clone repo | running, failed |
| running | Claude Code 正在執行開發流程 | pushing, failed, cancelled |
| pushing | 正在 git push 並建立 PR | completed, failed |
| completed | 已完成，PR 已建立 | （終態） |
| failed | 執行過程中發生錯誤 | （終態） |
| cancelled | 被使用者手動取消 | （終態） |

---

## 4. Job Queue 設計

### 4.1 排隊機制

由於 Claude Code Max 訂閱有 rate limit，系統一次只執行一個 Job，其餘排隊等待。

**排隊規則：**

1. 按 priority 由小到大排序（1 最優先）。
2. 相同 priority 按 created_at 先進先出（FIFO）。
3. 同一個 Jira 工單不能重複排隊（檢查 running + queued 中是否已存在）。

### 4.2 持久化

使用 SQLite 存放 Job 資料，確保 server 重啟後不遺失佇列。資料庫檔案位於 `~/claude-workspace/.db/jobs.sqlite`。

### 4.3 超時與重試

| 參數 | 預設值 | 說明 |
|------|--------|------|
| JOB_TIMEOUT | 30 分鐘 | 單一 Job 最大執行時間，超時自動 kill 並標記 failed（硬性限制） |
| MAX_TURNS | 50 | Claude agent 最大輪數，達到時優雅停止（軟性限制） |
| CLONE_TIMEOUT | 2 分鐘 | git clone 超時 |
| FALLBACK_MODEL | sonnet | API 過載時自動降級的模型 |
| MAX_RETRIES | 0 | 預設不重試（Claude Code 的結果不具冪等性） |
| QUEUE_POLL_INTERVAL | 5 秒 | 檢查 queue 的間隔 |

---

## 5. Claude Code 執行細節

### 5.1 指令格式

系統實際執行的 shell 指令：

```bash
claude -p --dangerously-skip-permissions \
  --output-format stream-json \
  --max-turns ${MAX_TURNS:-50} \
  --fallback-model ${FALLBACK_MODEL:-sonnet} \
  --append-system-prompt-file <path-to-jirara.md> \
  "請處理 Jira 單 {jira_ticket}"
```

**CLI 旗標說明：**

| 旗標 | 用途 |
|------|------|
| `--output-format stream-json` | 輸出結構化 JSON 事件流，支援前端分類顯示和 token/cost 追蹤 |
| `--max-turns` | 限制 agent 輪數（軟性上限），達到時優雅停止，避免無限迴圈 |
| `--fallback-model` | API 過載時自動降級到指定模型，避免 Job 直接失敗 |

**Prompt 組成：**

1. 主指令：`請處理 Jira 單 {jira_ticket}`（僅此一句，開發 SOP 由 Jirara skill 透過 `--append-system-prompt-file` 注入）
2. Extra prompt：使用者自訂的額外指示（如有）

### 5.2 開發 SOP 注入方式

開發 SOP（讀取 Jira 單、建立 branch、撰寫程式碼與測試、建立 PR 等完整流程）現在由集中管理的 **Jirara skill** 透過 `--append-system-prompt-file` 統一注入，不再依賴各 repo 自備 CLAUDE.md 作為 SOP 主要來源。

**各 repo 的 CLAUDE.md：**

- 仍可存在，Claude Code 啟動時會自動讀取
- 用途改為補充該 repo 的團隊特殊規範（如 coding style、測試框架偏好、特定 lint 設定等）
- 不需要再包含完整的開發流程步驟，因為 Jirara skill 已涵蓋標準 SOP

### 5.3 環境變數

| 變數名稱 | 用途 | 範例 |
|----------|------|------|
| JIRA_BASE_URL | Jira API 根路徑 | `https://team.atlassian.net` |
| JIRA_TOKEN | Jira API Token（Base64 encoded） | `dXNlckBleGFtcGxlLmNvbTp...` |
| GITHUB_TOKEN | GitHub Personal Access Token | `ghp_xxxxxxxxxxxx` |
| JIRARA_SKILL_PATH | （可選）Jirara skill 檔案路徑，預設由專案路徑自動解析 | `/path/to/jirara.md` |
| MAX_TURNS | （可選）Claude agent 最大輪數 | `50` |
| FALLBACK_MODEL | （可選）API 過載時的降級模型 | `sonnet` |

---

## 6. 前端設計

### 6.1 頁面結構

| 頁面 | 路徑 | 功能 |
|------|------|------|
| Dashboard | / | Job 列表 + 即時狀態 + 統計數據 |
| New Job | /new | 建立新 Job 的表單 |
| Job Detail | /jobs/:id | 單一 Job 詳情 + 即時 log 串流 |

### 6.2 Dashboard 顯示資訊

- 頂部統計：目前 running 數量、queued 數量、今日完成數、成功率
- Job 列表：顯示 Jira 工單號、狀態 badge、提交者、時間、耗時
- 即時更新：透過 SSE 推送，不需要手動 refresh
- 篩選：按狀態 filter（All / Running / Queued / Completed / Failed）

### 6.3 New Job 表單欄位

| 欄位 | 類型 | 必填 | 驗證規則 |
|------|------|------|----------|
| Jira Ticket | text input | 是 | 格式：`[A-Z]+-[0-9]+`（如 JRA-123） |
| Repository | dropdown / text | 是 | 預設下拉選單 + 可手動輸入 |
| Branch | text input | 否 | 預設為空（使用 repo 的 default branch） |
| Extra Prompt | textarea | 否 | 最大 2000 字元 |
| Priority | select 1-5 | 否 | 預設 3（Normal） |

---

## 7. 安全設計

### 7.1 認證

- **Phase 1（MVP）：** 共用 Bearer Token。所有同事使用同一個 token 存在前端環境變數中。簡單但夠用。
- **Phase 2（正式）：** 可整合公司 SSO / LDAP，或使用簡易帳號密碼登入 + JWT。

### 7.2 輸入驗證（防 Shell Injection）

這是最關鍵的安全防線，因為系統使用 `--dangerously-skip-permissions`：

- **repo_url：** 只允許 `https://` 開頭，白名單限定允許的 GitHub org
- **jira_ticket：** 嚴格正則驗證 `^[A-Z]{1,10}-\d{1,6}$`
- **branch：** 只允許 `^[a-zA-Z0-9._/-]+$`
- **extra_prompt：** 長度限制 + 禁止含有 shell 特殊字元
- **所有參數絕不拼接到 shell 指令中**，一律使用 subprocess 的 list 格式傳遞

### 7.3 Repo 白名單

在後端設定允許的 GitHub organization 或 repo 列表，拒絕不在白名單內的 repo URL。避免被利用 clone 惡意 repo。

### 7.4 網路安全

- **內網存取：** server bind 0.0.0.0 但依賴公司防火牆限制外部存取
- **外網存取（如需要）：** 加上 Cloudflare Tunnel + Access 或 Tailscale
- **Mac Mini 防火牆：** 允許 port 8000 的 incoming connection

---

## 8. 部署與維運

### 8.1 首次部署步驟

1. Mac Mini 設定固定內網 IP
2. 關閉自動休眠（系統設定 → 能源）
3. 安裝 Python 3.11+ 與 uv、Node.js 20+、git、gh CLI
4. 安裝 Claude Code CLI 並登入 Max 帳號
5. Clone 本系統 repo，執行 `uv sync` 安裝依賴
6. 設定 .env 檔案（API token、Jira 認證等）
7. Build 前端靜態檔案
8. 啟動 server 並設定 launchd 開機自啟

### 8.2 自動啟動（launchd）

使用 macOS LaunchAgent 設定 server 開機自動啟動 + crash 後自動重啟（KeepAlive: true）。plist 檔案位於 `~/Library/LaunchAgents/com.claude-remote-agent.plist`。

### 8.3 日誌與監控

| 日誌類型 | 位置 | 說明 |
|----------|------|------|
| Server log | `~/claude-workspace/.logs/server.log` | FastAPI 的 request/response log |
| Job log | `~/claude-workspace/.logs/{job_id}.log` | 每個 Job 的完整 stdout/stderr |
| Claude output | （存在 Job log 內） | Claude Code 的完整輸出 |

### 8.4 磁碟空間管理

每個 Job 會 clone 一份 repo，長期會佔用大量空間。建議：

- Job 完成/失敗後，保留 workspace 24 小時供 debug，之後自動清除
- 可設定 cron job 定期清理 `~/claude-workspace` 下超過 N 天的資料夾

---

## 9. 已知限制與風險

| 風險 | 影響 | 緩解措施 |
|------|------|----------|
| Claude Code Max 為個人訂閱 | 多人共用可能違反 Anthropic 使用條款 | 確認授權合規性；或改用 API + Team plan |
| Rate limit | 同時多人送單時排隊時間可能很長 | Job queue 排隊 + 前端顯示預估等待時間 |
| AI 產出品質 | Claude 可能產出有 bug 的程式碼 | 所有產出必經 code review，不自動 merge |
| --dangerously-skip-permissions | Claude 可在 Mac Mini 上執行任意指令 | 嚴格輸入驗證 + repo 白名單 + 獨立使用者帳號 |
| 單點故障 | Mac Mini 故障 = 整個系統停擺 | Phase 2 可考慮備援機器或雲端 worker |

---

## 10. 開發里程碑

| Phase | 範圍 | 預估時間 |
|-------|------|----------|
| Phase 1 — MVP | 後端 API + Job Queue + 基本前端 + 單一 repo 驗證 | 1 週 |
| Phase 2 — 強化 | SSE 即時 log + 多 repo + Slack 通知 + 磁碟清理 | 1 週 |
| Phase 3 — 正式 | 使用者認證 + Jira Webhook 入口 + 監控 dashboard | 1-2 週 |

---

## 11. 附錄：目錄結構

```
claude-remote-agent/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── db.py                # SQLite connection
│   ├── routers/
│   │   ├── jobs.py          # /api/v1/jobs routes
│   │   └── callback.py      # /api/v1/callback route
│   ├── services/
│   │   ├── queue.py         # Job queue + scheduler
│   │   ├── executor.py      # Claude Code subprocess runner
│   │   └── validator.py     # Input validation + sanitization
│   ├── models/
│   │   └── job.py           # Job data model + DB schema
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── NewJob.jsx
│   │   │   └── JobDetail.jsx
│   │   └── components/
│   │       ├── TokenGate.jsx
│   │       └── StatusBadge.jsx
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── .env.example
├── setup.sh
└── README.md
```
