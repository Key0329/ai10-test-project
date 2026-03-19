"""Job queue — polls DB for queued jobs and dispatches to executor."""

import asyncio
import logging
from db import get_db
from services.executor import execute_job

logger = logging.getLogger("queue")

POLL_INTERVAL = int(__import__("os").getenv("QUEUE_POLL_INTERVAL", "5"))

# Track the currently running task so we can cancel if needed
_current_task: asyncio.Task | None = None
_running = False


async def _get_next_job() -> dict | None:
    """Get the highest-priority queued job."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT * FROM jobs
               WHERE status = 'queued'
               ORDER BY priority ASC, created_at ASC
               LIMIT 1"""
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def _is_any_running() -> bool:
    """Check if a job is currently running."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM jobs WHERE status IN ('cloning', 'running', 'pushing')"
        )
        row = await cursor.fetchone()
        return row["cnt"] > 0
    finally:
        await db.close()


async def _recover_stale_jobs():
    """On startup, mark any 'running/cloning' jobs as failed (they were interrupted)."""
    db = await get_db()
    try:
        await db.execute(
            """UPDATE jobs SET status = 'failed', error_message = 'Server restarted during execution'
               WHERE status IN ('cloning', 'running', 'pushing')"""
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM jobs WHERE error_message = 'Server restarted during execution'"
        )
        row = await cursor.fetchone()
        if row["cnt"] > 0:
            logger.warning(f"Recovered {row['cnt']} stale job(s) on startup")
    finally:
        await db.close()


async def start_queue_worker():
    """Main loop — runs as a background task."""
    global _current_task, _running
    _running = True

    await _recover_stale_jobs()
    logger.info(f"Queue worker started (poll interval: {POLL_INTERVAL}s)")

    while _running:
        try:
            if not await _is_any_running():
                job = await _get_next_job()
                if job:
                    logger.info(f"Dispatching job {job['id']} ({job['jira_ticket']})")
                    _current_task = asyncio.create_task(
                        execute_job(
                            job_id=job["id"],
                            repo_url=job["repo_url"],
                            jira_ticket=job["jira_ticket"],
                            branch=job["branch"],
                            extra_prompt=job["extra_prompt"],
                        )
                    )
                    # Wait for the task to finish before polling again
                    try:
                        await _current_task
                    except asyncio.CancelledError:
                        logger.warning(f"Job {job['id']} was cancelled")
                    except Exception as e:
                        logger.error(f"Job {job['id']} raised: {e}")
                    finally:
                        _current_task = None
        except Exception as e:
            logger.error(f"Queue worker error: {e}")

        await asyncio.sleep(POLL_INTERVAL)


async def cancel_job(job_id: str) -> bool:
    """Cancel a running or queued job."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
        row = await cursor.fetchone()
        if not row:
            return False

        if row["status"] == "queued":
            await db.execute(
                "UPDATE jobs SET status = 'cancelled' WHERE id = ?", (job_id,)
            )
            await db.commit()
            return True

        if row["status"] in ("cloning", "running", "pushing"):
            # If this is the currently running task, cancel it
            if _current_task and not _current_task.done():
                _current_task.cancel()
            await db.execute(
                "UPDATE jobs SET status = 'cancelled' WHERE id = ?", (job_id,)
            )
            await db.commit()
            return True
    finally:
        await db.close()

    return False


def stop_queue_worker():
    global _running
    _running = False
