# ─── Stage 1: 建置 Vue 前端 ────────────────────────────────────────
FROM node:22-alpine AS frontend-builder

WORKDIR /build/frontend

# 先複製 package.json，讓 npm install 可被 Docker cache
COPY frontend/package*.json ./
RUN npm ci

# 複製前端原始碼並 build
COPY frontend/ ./
RUN npm run build


# ─── Stage 2: 執行 FastAPI 後端 ────────────────────────────────────
FROM python:3.13-slim

# 後端工作目錄為 /app，main.py 的 FRONTEND_DIR 計算為 /frontend/dist
# os.path.join(os.path.dirname("/app/main.py"), "..", "frontend", "dist")
# → /app/../frontend/dist → /frontend/dist
WORKDIR /app

# 安裝依賴（優先 cache，只有 pyproject.toml 改變才重跑）
RUN pip install uv --no-cache-dir
COPY backend/pyproject.toml ./
RUN uv pip install --system --no-cache \
      aiosqlite==0.20.0 \
      fastapi==0.115.6 \
      "github-copilot-sdk>=0.1.23" \
      pydantic==2.10.4 \
      pydantic-settings==2.7.1 \
      sse-starlette==2.2.1 \
      "uvicorn[standard]==0.34.0"

# 複製後端原始碼
COPY backend/ ./

# 從 Stage 1 複製 build 好的前端到正確路徑
COPY --from=frontend-builder /build/frontend/dist /frontend/dist

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
