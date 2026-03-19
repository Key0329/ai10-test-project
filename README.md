# Claude Remote Agent

團隊共用的自動化開發系統。透過內部 Web 介面提交 Jira 工單，Mac Mini 上的 Claude Code 自動完成開發並建立 PR。

## Quick Start

```bash
# 1. Setup (安裝依賴 + build 前端 + 產生 .env)
chmod +x setup.sh && ./setup.sh

# 2. 編輯 .env (設定 Jira token、GitHub token 等)
vim .env

# 3. 啟動
cd backend
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000

# 4. 打開瀏覽器
# http://<Mac-Mini-IP>:8000
```

## Architecture

```
同事瀏覽器 → http://192.168.x.x:8000
                    │
              ┌─────┴─────── Mac Mini ──────────┐
              │                                  │
              │  React UI ──→ FastAPI Backend     │
              │                    │              │
              │              SQLite Job Queue     │
              │                    │              │
              │              subprocess           │
              │                    │              │
              │        claude -p --dangerous      │
              │        (reads repo CLAUDE.md)     │
              │                    │              │
              │            git push + PR          │
              └──────────────────────────────────┘
```

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/jobs | Create job |
| GET | /api/v1/jobs | List jobs |
| GET | /api/v1/jobs/:id | Job detail |
| GET | /api/v1/jobs/:id/logs | Stream logs (SSE) |
| POST | /api/v1/jobs/:id/cancel | Cancel job |
| POST | /api/v1/callback | Claude completion callback |
| GET | /api/v1/health | Health check |

## Project Structure

```
claude-remote-agent/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── db.py                # SQLite database
│   ├── routers/
│   │   ├── jobs.py          # Job CRUD + SSE logs
│   │   └── callback.py      # Completion callback
│   ├── services/
│   │   ├── queue.py         # Job queue scheduler
│   │   ├── executor.py      # Claude Code runner
│   │   └── validator.py     # Input validation
│   ├── models/
│   │   └── job.py           # Pydantic models
│   └── requirements.txt
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

## CLAUDE.md Template

每個目標 repo 需要在根目錄放 `CLAUDE.md`，定義 Claude Code 的自動化流程。
參考 spec 文件的 Section 5.2。

## Security

- All inputs are strictly validated (regex + whitelist)
- Never shell-concatenated — always subprocess list format
- Bearer token authentication
- Repo URL whitelist (configurable)
- Mac Mini should be behind company firewall
