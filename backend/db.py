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
    priority INTEGER DEFAULT 3,
    requested_by TEXT DEFAULT '',
    status TEXT DEFAULT 'queued',
    exit_code INTEGER,
    pr_url TEXT,
    error_message TEXT,
    work_dir TEXT,
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
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);
"""


async def get_db() -> aiosqlite.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    db = await get_db()
    try:
        await db.execute(CREATE_JOBS_TABLE)
        await db.execute(CREATE_LOGS_TABLE)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_logs_job_id ON job_logs(job_id)"
        )
        await db.commit()
    finally:
        await db.close()
