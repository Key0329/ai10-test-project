"""Job management routes."""

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from db import get_db
from models.job import JobCreate, JobResponse, JobListResponse, RerunRequest
from services.executor import execute_job
from services.copilot_executor import execute_copilot_job
from services.queue import cancel_job, _running_tasks, _on_task_done

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


def _row_to_response(r, **overrides) -> JobResponse:
    """Convert a DB row to JobResponse, with optional field overrides."""
    data = {
        "job_id": r["id"],
        "repo_url": r["repo_url"],
        "jira_ticket": r["jira_ticket"],
        "branch": r["branch"],
        "extra_prompt": r["extra_prompt"],
        "priority": r["priority"],
        "requested_by": r["requested_by"],
        "agent_mode": r["agent_mode"] if r["agent_mode"] else "claude_code",
        "status": r["status"],
        "exit_code": r["exit_code"],
        "pr_url": r["pr_url"],
        "error_message": r["error_message"],
        "created_at": r["created_at"],
        "started_at": r["started_at"],
        "finished_at": r["finished_at"],
        "parent_job_id": r["parent_job_id"],
    }
    data.update(overrides)
    return JobResponse(**data)


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
                                priority, requested_by, agent_mode, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?)""",
            (
                job_id,
                payload.repo_url,
                payload.jira_ticket,
                payload.branch,
                payload.extra_prompt,
                payload.priority,
                payload.requested_by,
                payload.agent_mode,
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

    # 直接執行，不透過 queue worker（queue worker 已暫時停用）
    executor_kwargs = dict(
        job_id=job_id,
        repo_url=payload.repo_url,
        jira_ticket=payload.jira_ticket,
        branch=payload.branch,
        extra_prompt=payload.extra_prompt,
        github_token=payload.github_token,
        jira_api_token=payload.jira_api_token,
        jira_email=payload.jira_email,
    )
    if payload.agent_mode == "copilot":
        task = asyncio.create_task(execute_copilot_job(**executor_kwargs))
    else:
        task = asyncio.create_task(execute_job(**executor_kwargs))
    task.add_done_callback(lambda t, j=job_id: _on_task_done(j, t))
    _running_tasks[job_id] = task

    return JobResponse(
        job_id=job_id,
        repo_url=payload.repo_url,
        jira_ticket=payload.jira_ticket,
        branch=payload.branch,
        extra_prompt=payload.extra_prompt,
        priority=payload.priority,
        requested_by=payload.requested_by,
        agent_mode=payload.agent_mode,
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
        _row_to_response(r)
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

    return _row_to_response(r)


@router.get("/{job_id}/chain")
async def get_chain(job_id: str):
    """Get the full rerun chain for a job."""
    db = await get_db()
    try:
        return await _get_chain_impl(job_id, db)
    finally:
        await db.close()


async def _get_chain_impl(job_id: str, db) -> list[dict]:
    """Get ordered rerun chain (first to latest) for any job in the chain."""
    cursor = await db.execute("SELECT id FROM jobs WHERE id = ?", (job_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Job not found")

    # Walk up to find the root (first job with no parent)
    current_id = job_id
    while True:
        cursor = await db.execute(
            "SELECT parent_job_id FROM jobs WHERE id = ?", (current_id,)
        )
        row = await cursor.fetchone()
        if not row or not row["parent_job_id"]:
            break
        current_id = row["parent_job_id"]

    # Walk down from root collecting the chain
    chain = []
    visit_id = current_id
    while visit_id:
        cursor = await db.execute(
            "SELECT id, status FROM jobs WHERE id = ?", (visit_id,)
        )
        row = await cursor.fetchone()
        if not row:
            break
        chain.append({"job_id": row["id"], "status": row["status"]})
        # Find child
        cursor = await db.execute(
            "SELECT id FROM jobs WHERE parent_job_id = ?", (visit_id,)
        )
        child = await cursor.fetchone()
        visit_id = child["id"] if child else None

    return chain


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


@router.post("/{job_id}/rerun", status_code=202, response_model=JobResponse)
async def rerun_job(job_id: str, payload: RerunRequest):
    """Rerun a completed or failed job by creating a new job with the same parameters."""
    db = await get_db()
    try:
        return await _rerun_job_impl(job_id, db, payload)
    finally:
        await db.close()


async def _rerun_job_impl(job_id: str, db, payload: RerunRequest) -> JobResponse:
    """Core rerun logic, extracted for testability."""
    cursor = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    original = await cursor.fetchone()
    if not original:
        raise HTTPException(status_code=404, detail="Job not found")

    active_statuses = ("queued", "cloning", "running", "pushing")
    if original["status"] in active_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Job is still active (status: {original['status']}). Cannot rerun.",
        )

    # Check for duplicate active job with same ticket
    cursor = await db.execute(
        """SELECT id FROM jobs
           WHERE jira_ticket = ? AND status IN ('queued', 'cloning', 'running', 'pushing')""",
        (original["jira_ticket"],),
    )
    existing = await cursor.fetchone()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Ticket {original['jira_ticket']} already has an active job: {existing['id']}",
        )

    now = datetime.now(timezone.utc).isoformat()
    new_job_id = f"{original['jira_ticket']}-{int(datetime.now(timezone.utc).timestamp())}"

    original_agent_mode = original["agent_mode"] if original["agent_mode"] else "claude_code"

    await db.execute(
        """INSERT INTO jobs (id, repo_url, jira_ticket, branch, extra_prompt,
                            priority, requested_by, agent_mode, status, parent_job_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?)""",
        (
            new_job_id,
            original["repo_url"],
            original["jira_ticket"],
            original["branch"],
            original["extra_prompt"],
            original["priority"],
            original["requested_by"],
            original_agent_mode,
            job_id,
            now,
        ),
    )
    await db.commit()

    cursor = await db.execute(
        """SELECT COUNT(*) as pos FROM jobs
           WHERE status = 'queued'
           AND (priority < ? OR (priority = ? AND created_at < ?))""",
        (original["priority"], original["priority"], now),
    )
    pos_row = await cursor.fetchone()

    # 直接執行，不透過 queue worker（queue worker 已暫時停用）
    # rerun 沿用原始 job 的 agent_mode
    rerun_kwargs = dict(
        job_id=new_job_id,
        repo_url=original["repo_url"],
        jira_ticket=original["jira_ticket"],
        branch=original["branch"],
        extra_prompt=original["extra_prompt"],
        github_token=payload.github_token,
        jira_api_token=payload.jira_api_token,
        jira_email=payload.jira_email,
    )
    if original_agent_mode == "copilot":
        task = asyncio.create_task(execute_copilot_job(**rerun_kwargs))
    else:
        task = asyncio.create_task(execute_job(**rerun_kwargs))
    task.add_done_callback(lambda t, j=new_job_id: _on_task_done(j, t))
    _running_tasks[new_job_id] = task

    return JobResponse(
        job_id=new_job_id,
        repo_url=original["repo_url"],
        jira_ticket=original["jira_ticket"],
        branch=original["branch"],
        extra_prompt=original["extra_prompt"],
        priority=original["priority"],
        requested_by=original["requested_by"],
        agent_mode=original_agent_mode,
        status="queued",
        exit_code=None,
        pr_url=None,
        error_message=None,
        created_at=now,
        started_at=None,
        finished_at=None,
        parent_job_id=job_id,
        position=pos_row["pos"] + 1,
    )


@router.post("/{job_id}/cancel")
async def cancel_job_route(job_id: str):
    """Cancel a running or queued job."""
    success = await cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled")
    return {"status": "cancelled", "job_id": job_id}
