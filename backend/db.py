"""SQLite database connection and initialization."""

import aiosqlite
import os

DB_DIR = os.path.expanduser("~/claude-workspace/.db")
DB_PATH = os.path.join(DB_DIR, "jobs.sqlite")

CREATE_JOBS_TABLE = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    repo_url TEXT NOT NULL,
    jira_ticket TEXT NOT NULL,
    branch TEXT DEFAULT 'main',
    extra_prompt TEXT DEFAULT '',
    requested_by TEXT DEFAULT '',
    agent_mode TEXT DEFAULT 'claude_code',
    status TEXT DEFAULT 'queued',
    exit_code INTEGER,
    pr_url TEXT,
    error_message TEXT,
    work_dir TEXT,
    parent_job_id TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT
);
"""

CREATE_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS job_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    stream TEXT DEFAULT 'stdout',
    message TEXT NOT NULL,
    event_type TEXT DEFAULT 'raw',
    metadata TEXT,
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);
"""


async def get_db() -> aiosqlite.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    db = await aiosqlite.connect(DB_PATH, timeout=30)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA busy_timeout=5000")
    return db


async def _migrate_job_logs(db):
    """Add event_type and metadata columns if missing (backward-compatible)."""
    cursor = await db.execute("PRAGMA table_info(job_logs)")
    columns = {row[1] for row in await cursor.fetchall()}
    if "event_type" not in columns:
        await db.execute("ALTER TABLE job_logs ADD COLUMN event_type TEXT DEFAULT 'raw'")
    if "metadata" not in columns:
        await db.execute("ALTER TABLE job_logs ADD COLUMN metadata TEXT")


async def _migrate_jobs_parent(db):
    """Add parent_job_id column to jobs table if missing (backward-compatible)."""
    cursor = await db.execute("PRAGMA table_info(jobs)")
    columns = {row[1] for row in await cursor.fetchall()}
    if "parent_job_id" not in columns:
        await db.execute("ALTER TABLE jobs ADD COLUMN parent_job_id TEXT")


async def _migrate_jobs_agent_mode(db):
    """Add agent_mode column to jobs table if missing (backward-compatible)."""
    cursor = await db.execute("PRAGMA table_info(jobs)")
    columns = {row[1] for row in await cursor.fetchall()}
    if "agent_mode" not in columns:
        await db.execute("ALTER TABLE jobs ADD COLUMN agent_mode TEXT DEFAULT 'claude_code'")


async def init_db():
    db = await get_db()
    try:
        await db.execute(CREATE_JOBS_TABLE)
        await db.execute(CREATE_LOGS_TABLE)
        await _migrate_job_logs(db)
        await _migrate_jobs_parent(db)
        await _migrate_jobs_agent_mode(db)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_logs_job_id ON job_logs(job_id)"
        )
        await db.commit()
    finally:
        await db.close()
