"""Claude Remote Agent — FastAPI entry point."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from db import init_db
from routers import jobs, callback, mcp
from services.scheduler import start_log_cleaner
# from services.queue import start_queue_worker, stop_queue_worker  # 暫時停用 queue worker

# ─── Logging ───────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")

# ─── Config ────────────────────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")


# ─── App lifecycle ─────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Database initialized")

    # queue_task = asyncio.create_task(start_queue_worker())  # 暫時停用：job 直接執行不透過 queue
    # logger.info("Queue worker started")

    cleaner_task = asyncio.create_task(start_log_cleaner())
    logger.info("Log cleaner scheduled")

    yield

    # stop_queue_worker()                                      # 暫時停用：queue worker 關閉
    # queue_task.cancel()
    # try:
    #     await queue_task
    # except asyncio.CancelledError:
    #     pass
    cleaner_task.cancel()
    try:
        await cleaner_task
    except asyncio.CancelledError:
        pass
    logger.info("Shutdown complete")


# ─── App ───────────────────────────────────────────────────────────
app = FastAPI(
    title="Claude Remote Agent",
    version="1.0.0",
    lifespan=lifespan,
)


# ─── Routes ────────────────────────────────────────────────────────
app.include_router(jobs.router)
app.include_router(callback.router)
app.include_router(mcp.router)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "service": "claude-remote-agent"}


# ─── CORS (for local dev) ─────────────────────────────────────────
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Serve frontend static files ──────────────────────────────────
if os.path.isdir(FRONTEND_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """SPA fallback — serve index.html for all non-API routes."""
        file_path = os.path.join(FRONTEND_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
else:
    @app.get("/")
    async def no_frontend():
        return JSONResponse(
            {"message": "Frontend not built yet. Run: cd frontend && npm run build"},
            status_code=200,
        )
