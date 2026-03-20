"""Tests for GET /api/v1/jobs/{id}/chain endpoint."""

import pytest
import pytest_asyncio
import aiosqlite

from datetime import datetime, timezone


@pytest_asyncio.fixture
async def db(tmp_path):
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
                      parent_job_id=None):
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """INSERT INTO jobs (id, repo_url, jira_ticket, branch, extra_prompt,
                            priority, requested_by, status, parent_job_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (job_id, "https://github.com/test/repo", jira_ticket, "main", "",
         3, "tester", status, parent_job_id, now),
    )
    await db.commit()


class TestRerunChain:

    @pytest.mark.asyncio
    async def test_single_job_no_chain(self, db):
        """A single job with no parent and no children returns a chain of one."""
        await _insert_job(db, "TEST-1-1000")

        from routers.jobs import _get_chain_impl
        chain = await _get_chain_impl("TEST-1-1000", db)

        assert len(chain) == 1
        assert chain[0]["job_id"] == "TEST-1-1000"

    @pytest.mark.asyncio
    async def test_two_job_chain(self, db):
        """A rerun creates a 2-job chain, ordered first to latest."""
        await _insert_job(db, "TEST-1-1000", status="completed")
        await _insert_job(db, "TEST-1-2000", status="queued", parent_job_id="TEST-1-1000")

        from routers.jobs import _get_chain_impl
        chain = await _get_chain_impl("TEST-1-2000", db)

        assert len(chain) == 2
        assert chain[0]["job_id"] == "TEST-1-1000"
        assert chain[1]["job_id"] == "TEST-1-2000"

    @pytest.mark.asyncio
    async def test_three_job_chain_from_middle(self, db):
        """Querying chain from any job in the chain returns the full chain."""
        await _insert_job(db, "TEST-1-1000", status="completed")
        await _insert_job(db, "TEST-1-2000", status="failed", parent_job_id="TEST-1-1000")
        await _insert_job(db, "TEST-1-3000", status="queued", parent_job_id="TEST-1-2000")

        from routers.jobs import _get_chain_impl
        chain = await _get_chain_impl("TEST-1-2000", db)

        assert len(chain) == 3
        assert chain[0]["job_id"] == "TEST-1-1000"
        assert chain[1]["job_id"] == "TEST-1-2000"
        assert chain[2]["job_id"] == "TEST-1-3000"

    @pytest.mark.asyncio
    async def test_chain_includes_status(self, db):
        """Each chain entry includes job_id and status."""
        await _insert_job(db, "TEST-1-1000", status="completed")
        await _insert_job(db, "TEST-1-2000", status="running", parent_job_id="TEST-1-1000")

        from routers.jobs import _get_chain_impl
        chain = await _get_chain_impl("TEST-1-1000", db)

        assert chain[0]["status"] == "completed"
        assert chain[1]["status"] == "running"

    @pytest.mark.asyncio
    async def test_chain_nonexistent_job(self, db):
        """Querying chain for non-existent job raises 404."""
        from routers.jobs import _get_chain_impl
        with pytest.raises(Exception) as exc_info:
            await _get_chain_impl("NOPE-999", db)
        assert exc_info.value.status_code == 404
