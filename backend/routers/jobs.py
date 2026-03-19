"""Job management routes."""

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from db import get_db
from models.job import JobCreate, JobResponse, JobListResponse
from services.queue import cancel_job

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.post("", status_code=202, response_model=JobResponse)
async def create_job(payload: JobCreate):
    """Create a new development job."""
    db = await get_db()
    try:
        # Check for duplicate (same ticket already running/queued)
        cursor = await db.execute(
            """SELECT id FROM jobs
               WHERE jira_ticket = ? AND status IN ('queued', 'cloning', 'running', 'pushing')""",
            (payload.jira_ticket,),
        )
        existing = await cursor.fetchone()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Ticket {payload.jira_ticket} already has an active job: {existing['id']}",
            )

        now = datetime.now(timezone.utc).isoformat()
        job_id = f"{payload.jira_ticket}-{int(datetime.now(timezone.utc).timestamp())}"

        await db.execute(
            """INSERT INTO jobs (id, repo_url, jira_ticket, branch, extra_prompt,
                                priority, requested_by, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', ?)""",
            (
                job_id,
                payload.repo_url,
                payload.jira_ticket,
                payload.branch,
                payload.extra_prompt,
                payload.priority,
                payload.requested_by,
                now,
            ),
        )
        await db.commit()

        # Get queue position
        cursor = await db.execute(
            """SELECT COUNT(*) as pos FROM jobs
               WHERE status = 'queued'
               AND (priority < ? OR (priority = ? AND created_at < ?))""",
            (payload.priority, payload.priority, now),
        )
        pos_row = await cursor.fetchone()
    finally:
        await db.close()

    return JobResponse(
        job_id=job_id,
        repo_url=payload.repo_url,
        jira_ticket=payload.jira_ticket,
        branch=payload.branch,
        extra_prompt=payload.extra_prompt,
        priority=payload.priority,
        requested_by=payload.requested_by,
        status="queued",
        exit_code=None,
        pr_url=None,
        error_message=None,
        created_at=now,
        started_at=None,
        finished_at=None,
        position=pos_row["pos"] + 1,
    )


@router.get("", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = Query(None, pattern="^(queued|cloning|running|pushing|completed|failed|cancelled)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List all jobs with optional status filter."""
    db = await get_db()
    try:
        where = "WHERE status = ?" if status else ""
        params = (status,) if status else ()

        cursor = await db.execute(
            f"SELECT * FROM jobs {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        )
        rows = await cursor.fetchall()

        cursor = await db.execute(f"SELECT COUNT(*) as cnt FROM jobs {where}", params)
        total = (await cursor.fetchone())["cnt"]

        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM jobs WHERE status IN ('cloning', 'running', 'pushing')"
        )
        running = (await cursor.fetchone())["cnt"]

        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM jobs WHERE status = 'queued'"
        )
        queued = (await cursor.fetchone())["cnt"]
    finally:
        await db.close()

    jobs = [
        JobResponse(
            job_id=r["id"],
            repo_url=r["repo_url"],
            jira_ticket=r["jira_ticket"],
            branch=r["branch"],
            extra_prompt=r["extra_prompt"],
            priority=r["priority"],
            requested_by=r["requested_by"],
            status=r["status"],
            exit_code=r["exit_code"],
            pr_url=r["pr_url"],
            error_message=r["error_message"],
            created_at=r["created_at"],
            started_at=r["started_at"],
            finished_at=r["finished_at"],
        )
        for r in rows
    ]

    return JobListResponse(jobs=jobs, total=total, running=running, queued=queued)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """Get a single job's details."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        r = await cursor.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Job not found")
    finally:
        await db.close()

    return JobResponse(
        job_id=r["id"],
        repo_url=r["repo_url"],
        jira_ticket=r["jira_ticket"],
        branch=r["branch"],
        extra_prompt=r["extra_prompt"],
        priority=r["priority"],
        requested_by=r["requested_by"],
        status=r["status"],
        exit_code=r["exit_code"],
        pr_url=r["pr_url"],
        error_message=r["error_message"],
        created_at=r["created_at"],
        started_at=r["started_at"],
        finished_at=r["finished_at"],
    )


@router.get("/{job_id}/logs")
async def stream_logs(job_id: str):
    """Stream job logs via SSE."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM jobs WHERE id = ?", (job_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Job not found")
    finally:
        await db.close()

    async def event_generator():
        last_id = 0
        while True:
            db = await get_db()
            try:
                cursor = await db.execute(
                    """SELECT id, timestamp, stream, message, event_type, metadata FROM job_logs
                       WHERE job_id = ? AND id > ?
                       ORDER BY id ASC""",
                    (job_id, last_id),
                )
                rows = await cursor.fetchall()

                for row in rows:
                    last_id = row["id"]
                    yield {
                        "event": "log",
                        "data": json.dumps({
                            "stream": row["stream"],
                            "message": row["message"],
                            "event_type": row["event_type"] or "raw",
                            "metadata": row["metadata"],
                        }, ensure_ascii=False),
                    }

                # Check if job is finished
                cursor = await db.execute(
                    "SELECT status FROM jobs WHERE id = ?", (job_id,)
                )
                job = await cursor.fetchone()
                if job and job["status"] in ("completed", "failed", "cancelled"):
                    yield {"event": "done", "data": job["status"]}
                    return
            finally:
                await db.close()

            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())


@router.post("/{job_id}/cancel")
async def cancel_job_route(job_id: str):
    """Cancel a running or queued job."""
    success = await cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled")
    return {"status": "cancelled", "job_id": job_id}
