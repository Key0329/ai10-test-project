"""Tests for POST /api/v1/jobs/{id}/rerun endpoint."""

import pytest
import pytest_asyncio
import aiosqlite

from datetime import datetime, timezone


@pytest_asyncio.fixture
async def db(tmp_path):
    """Create a temp DB with schema applied."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    db_path = str(tmp_path / "test.sqlite")
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row

    from db import CREATE_JOBS_TABLE, CREATE_LOGS_TABLE
    await conn.execute(CREATE_JOBS_TABLE)
    await conn.execute(CREATE_LOGS_TABLE)
    await conn.commit()
    yield conn
    await conn.close()


async def _insert_job(db, job_id, jira_ticket="TEST-1", status="completed",
                      repo_url="https://github.com/test/repo", branch="main",
                      extra_prompt="", priority=3, requested_by="tester",
                      parent_job_id=None):
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """INSERT INTO jobs (id, repo_url, jira_ticket, branch, extra_prompt,
                            priority, requested_by, status, parent_job_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (job_id, repo_url, jira_ticket, branch, extra_prompt,
         priority, requested_by, status, parent_job_id, now),
    )
    await db.commit()


class TestRerunEndpoint:
    """Tests for the rerun_job route function."""

    @pytest.mark.asyncio
    async def test_rerun_completed_job(self, db):
        """Rerun a completed job should create a new queued job with parent_job_id."""
        await _insert_job(db, "TEST-1-1000", status="completed")

        from routers.jobs import _rerun_job_impl
        result = await _rerun_job_impl("TEST-1-1000", db)

        assert result.status == "queued"
        assert result.parent_job_id == "TEST-1-1000"
        assert result.jira_ticket == "TEST-1"
        assert result.repo_url == "https://github.com/test/repo"
        assert result.branch == "main"
        assert result.priority == 3

    @pytest.mark.asyncio
    async def test_rerun_failed_job(self, db):
        """Rerun a failed job should create a new queued job."""
        await _insert_job(db, "TEST-2-1000", jira_ticket="TEST-2", status="failed")

        from routers.jobs import _rerun_job_impl
        result = await _rerun_job_impl("TEST-2-1000", db)

        assert result.status == "queued"
        assert result.parent_job_id == "TEST-2-1000"
        assert result.jira_ticket == "TEST-2"

    @pytest.mark.asyncio
    async def test_rerun_active_job_rejected(self, db):
        """Rerun an active (queued/running/cloning/pushing) job should raise 400."""
        for active_status in ("queued", "cloning", "running", "pushing"):
            await _insert_job(db, f"TEST-3-{active_status}", jira_ticket="TEST-3", status=active_status)

            from routers.jobs import _rerun_job_impl
            with pytest.raises(Exception) as exc_info:
                await _rerun_job_impl(f"TEST-3-{active_status}", db)
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_rerun_duplicate_ticket_rejected(self, db):
        """Rerun should be blocked if another job with same ticket is already active."""
        await _insert_job(db, "TEST-4-1000", jira_ticket="TEST-4", status="completed")
        await _insert_job(db, "TEST-4-2000", jira_ticket="TEST-4", status="running")

        from routers.jobs import _rerun_job_impl
        with pytest.raises(Exception) as exc_info:
            await _rerun_job_impl("TEST-4-1000", db)
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_rerun_nonexistent_job(self, db):
        """Rerun a non-existent job should raise 404."""
        from routers.jobs import _rerun_job_impl
        with pytest.raises(Exception) as exc_info:
            await _rerun_job_impl("NOPE-999", db)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_rerun_cancelled_job(self, db):
        """Rerun a cancelled job should also work (not active)."""
        await _insert_job(db, "TEST-5-1000", jira_ticket="TEST-5", status="cancelled")

        from routers.jobs import _rerun_job_impl
        result = await _rerun_job_impl("TEST-5-1000", db)

        assert result.status == "queued"
        assert result.parent_job_id == "TEST-5-1000"
