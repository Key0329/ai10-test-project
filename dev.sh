#!/bin/bash
# 本機開發環境 — 同時啟動前後端
# 使用方式：./dev.sh

trap 'kill 0' EXIT

# 清除舊資料
DB_FILE=~/claude-workspace/.db/jobs.sqlite
if [ -f "$DB_FILE" ]; then
  rm -f "$DB_FILE" "$DB_FILE-wal" "$DB_FILE-shm"
  echo "✔ 已清除舊 DB"
fi

# 釋放被佔用的 port
lsof -ti:8000 | xargs kill -9 2>/dev/null && echo "✔ 已釋放 port 8000"

# 後端
cd backend && uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload &

# 前端（確保 node_modules 已安裝）
cd frontend && [ -d node_modules ] || npm ci
npx vite &

wait
