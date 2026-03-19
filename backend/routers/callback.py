"""Callback endpoint — called by Claude Code when job finishes."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter

from db import get_db
from models.job import CallbackPayload

logger = logging.getLogger("callback")
router = APIRouter(prefix="/api/v1", tags=["callback"])


@router.post("/callback")
async def job_callback(payload: CallbackPayload):
    """Receive completion callback from Claude Code."""
    logger.info(f"Callback received: job={payload.job_id} status={payload.status}")

    db = await get_db()
    async with db:
        now = datetime.now(timezone.utc).isoformat()

        if payload.status == "done":
            await db.execute(
                """UPDATE jobs SET status = 'completed', pr_url = ?, finished_at = ?
                   WHERE id = ?""",
                (payload.pr_url, now, payload.job_id),
            )
        else:
            await db.execute(
                """UPDATE jobs SET status = 'failed', error_message = ?, finished_at = ?
                   WHERE id = ?""",
                (payload.error or "Unknown error from callback", now, payload.job_id),
            )
        await db.commit()

    # TODO: Add Slack notification here
    # TODO: Add Jira status update here

    return {"received": True, "job_id": payload.job_id}
