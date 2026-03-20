"""Job queue — polls DB for queued jobs and dispatches to executor."""

import asyncio
import logging
import os
from db import get_db
from services.executor import execute_job

logger = logging.getLogger("queue")

POLL_INTERVAL = int(os.getenv("QUEUE_POLL_INTERVAL", "5"))
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "5"))

# Track running tasks: job_id → asyncio.Task
_running_tasks: dict[str, asyncio.Task] = {}
_running = False


async def _get_next_jobs(limit: int) -> list[dict]:
    """Get the highest-priority queued jobs up to limit."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT * FROM jobs
               WHERE status = 'queued'
               ORDER BY priority ASC, created_at ASC
               LIMIT ?""",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def _count_running() -> int:
    """Count currently running jobs in DB."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM jobs WHERE status IN ('cloning', 'running')"
        )
        row = await cursor.fetchone()
        return row["cnt"]
    finally:
        await db.close()


async def _recover_stale_jobs():
    """On startup, mark any 'running/cloning' jobs as failed (they were interrupted)."""
    db = await get_db()
    try:
        await db.execute(
            """UPDATE jobs SET status = 'failed', error_message = 'Server restarted during execution'
               WHERE status IN ('cloning', 'running')"""
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


def _on_task_done(job_id: str, task: asyncio.Task):
    """Callback when a job task finishes."""
    _running_tasks.pop(job_id, None)
    try:
        exc = task.exception()
        if exc:
            logger.error(f"Job {job_id} raised: {exc}")
    except asyncio.CancelledError:
        logger.warning(f"Job {job_id} was cancelled")


async def start_queue_worker():
    """Main loop — runs as a background task."""
    global _running
    _running = True

    await _recover_stale_jobs()
    logger.info(f"Queue worker started (poll interval: {POLL_INTERVAL}s, max concurrent: {MAX_CONCURRENT})")

    while _running:
        try:
            # Clean up finished tasks
            done_ids = [jid for jid, t in _running_tasks.items() if t.done()]
            for jid in done_ids:
                _running_tasks.pop(jid, None)

            # How many slots available?
            slots = MAX_CONCURRENT - len(_running_tasks)
            if slots > 0:
                jobs = await _get_next_jobs(slots)
                for job in jobs:
                    jid = job["id"]
                    if jid in _running_tasks:
                        continue
                    logger.info(f"Dispatching job {jid} ({job['jira_ticket']}) [{len(_running_tasks)+1}/{MAX_CONCURRENT}]")
                    task = asyncio.create_task(
                        execute_job(
                            job_id=jid,
                            repo_url=job["repo_url"],
                            jira_ticket=job["jira_ticket"],
                            branch=job["branch"],
                            extra_prompt=job["extra_prompt"],
                        )
                    )
                    task.add_done_callback(lambda t, j=jid: _on_task_done(j, t))
                    _running_tasks[jid] = task
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

        if row["status"] in ("cloning", "running"):
            task = _running_tasks.get(job_id)
            if task and not task.done():
                task.cancel()
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
    for task in _running_tasks.values():
        task.cancel()
