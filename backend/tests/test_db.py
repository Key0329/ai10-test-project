"""Tests for database schema — job_logs extended columns."""

import aiosqlite
import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def db(tmp_path):
    """Create an in-memory-like temp DB with schema applied."""
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


class TestJobLogsSchema:
    """Verify job_logs table has event_type and metadata columns."""

    @pytest.mark.asyncio
    async def test_insert_with_event_type_and_metadata(self, db):
        await db.execute(
            "INSERT INTO job_logs (job_id, timestamp, stream, message, event_type, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("job-1", "2026-01-01T00:00:00Z", "stdout", "test", "assistant", '{"type":"assistant"}'),
        )
        await db.commit()
        cursor = await db.execute("SELECT event_type, metadata FROM job_logs WHERE job_id = 'job-1'")
        row = await cursor.fetchone()
        assert row["event_type"] == "assistant"
        assert row["metadata"] == '{"type":"assistant"}'

    @pytest.mark.asyncio
    async def test_event_type_defaults_to_raw(self, db):
        await db.execute(
            "INSERT INTO job_logs (job_id, timestamp, stream, message) "
            "VALUES (?, ?, ?, ?)",
            ("job-2", "2026-01-01T00:00:00Z", "stdout", "plain text"),
        )
        await db.commit()
        cursor = await db.execute("SELECT event_type, metadata FROM job_logs WHERE job_id = 'job-2'")
        row = await cursor.fetchone()
        assert row["event_type"] == "raw"
        assert row["metadata"] is None

    @pytest.mark.asyncio
    async def test_metadata_nullable(self, db):
        await db.execute(
            "INSERT INTO job_logs (job_id, timestamp, stream, message, event_type) "
            "VALUES (?, ?, ?, ?, ?)",
            ("job-3", "2026-01-01T00:00:00Z", "stderr", "error msg", "system"),
        )
        await db.commit()
        cursor = await db.execute("SELECT metadata FROM job_logs WHERE job_id = 'job-3'")
        row = await cursor.fetchone()
        assert row["metadata"] is None
