"""Tests for _emit_summary — execution summary log on job completion."""

import json

import aiosqlite
import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def db(tmp_path, monkeypatch):
    """Set up a temp DB and patch get_db to return fresh connections."""
    db_path = str(tmp_path / "test.sqlite")

    init_conn = await aiosqlite.connect(db_path)
    from db import CREATE_JOBS_TABLE, CREATE_LOGS_TABLE
    await init_conn.execute(CREATE_JOBS_TABLE)
    await init_conn.execute(CREATE_LOGS_TABLE)
    await init_conn.commit()
    await init_conn.close()

    async def fake_get_db():
        conn = await aiosqlite.connect(db_path)
        conn.row_factory = aiosqlite.Row
        return conn

    monkeypatch.setattr("services.executor.get_db", fake_get_db)

    read_conn = await aiosqlite.connect(db_path)
    read_conn.row_factory = aiosqlite.Row
    yield read_conn
    await read_conn.close()


async def _insert_log(db_fixture, job_id, stream, message, event_type="raw", metadata=None):
    """Helper: insert a log via the patched _log function."""
    from services.executor import _log
    await _log(job_id, stream, message, event_type=event_type, metadata=metadata)


class TestEmitSummaryTokenCost:
    """Verify token and cost data are parsed from result event."""

    @pytest.mark.asyncio
    async def test_summary_contains_token_counts(self, db):
        from services.executor import _emit_summary

        result_meta = json.dumps({
            "type": "result",
            "total_cost_usd": 0.52,
            "num_turns": 8,
            "usage": {
                "input_tokens": 1000,
                "output_tokens": 500,
                "cache_read_input_tokens": 5000,
            },
        })
        await _insert_log(db, "job-s1", "stdout", "[success] Done", event_type="result", metadata=result_meta)

        await _emit_summary("job-s1")

        cursor = await db.execute(
            "SELECT message, event_type FROM job_logs WHERE job_id = 'job-s1' AND message LIKE '%摘要%' ORDER BY id DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row["event_type"] == "system"
        assert "500" in row["message"]  # output_tokens
        assert "1,000" in row["message"] or "1000" in row["message"]  # input_tokens
        assert "0.52" in row["message"]  # cost

    @pytest.mark.asyncio
    async def test_summary_handles_missing_fields(self, db):
        from services.executor import _emit_summary

        result_meta = json.dumps({
            "type": "result",
            "num_turns": 3,
        })
        await _insert_log(db, "job-s2", "stdout", "[success]", event_type="result", metadata=result_meta)

        await _emit_summary("job-s2")

        cursor = await db.execute(
            "SELECT message FROM job_logs WHERE job_id = 'job-s2' AND message LIKE '%摘要%'"
        )
        row = await cursor.fetchone()
        assert row is not None
        assert "N/A" in row["message"]


class TestEmitSummaryMcpCollection:
    """Verify MCP server names are collected from logs."""

    @pytest.mark.asyncio
    async def test_summary_lists_mcp_servers(self, db):
        from services.executor import _emit_summary

        result_meta = json.dumps({"type": "result", "total_cost_usd": 0.1, "num_turns": 2, "usage": {"input_tokens": 10, "output_tokens": 5}})
        await _insert_log(db, "job-m1", "stdout", "[success]", event_type="result", metadata=result_meta)
        await _insert_log(db, "job-m1", "stdout", "[mcp] mcp__github__create_pr: Create PR", event_type="mcp")
        await _insert_log(db, "job-m1", "stdout", "[mcp] mcp__github__list_prs: List PRs", event_type="mcp")
        await _insert_log(db, "job-m1", "stdout", "[mcp] mcp__context7__query: Query", event_type="mcp")

        await _emit_summary("job-m1")

        cursor = await db.execute(
            "SELECT message FROM job_logs WHERE job_id = 'job-m1' AND message LIKE '%摘要%'"
        )
        row = await cursor.fetchone()
        assert "github" in row["message"]
        assert "context7" in row["message"]

    @pytest.mark.asyncio
    async def test_summary_shows_none_when_no_mcp(self, db):
        from services.executor import _emit_summary

        result_meta = json.dumps({"type": "result", "total_cost_usd": 0.1, "num_turns": 1, "usage": {"input_tokens": 10, "output_tokens": 5}})
        await _insert_log(db, "job-m2", "stdout", "[success]", event_type="result", metadata=result_meta)

        await _emit_summary("job-m2")

        cursor = await db.execute(
            "SELECT message FROM job_logs WHERE job_id = 'job-m2' AND message LIKE '%摘要%'"
        )
        row = await cursor.fetchone()
        assert "(none)" in row["message"] or "（無）" in row["message"]


class TestEmitSummarySkillCollection:
    """Verify skill names are collected from logs."""

    @pytest.mark.asyncio
    async def test_summary_lists_skills(self, db):
        from services.executor import _emit_summary

        result_meta = json.dumps({"type": "result", "total_cost_usd": 0.2, "num_turns": 5, "usage": {"input_tokens": 100, "output_tokens": 50}})
        await _insert_log(db, "job-sk1", "stdout", "[success]", event_type="result", metadata=result_meta)
        await _insert_log(db, "job-sk1", "stdout", "[skill] Skill: commit", event_type="skill")
        await _insert_log(db, "job-sk1", "stdout", "[skill] Skill: simplify", event_type="skill")

        await _emit_summary("job-sk1")

        cursor = await db.execute(
            "SELECT message FROM job_logs WHERE job_id = 'job-sk1' AND message LIKE '%摘要%'"
        )
        row = await cursor.fetchone()
        assert "commit" in row["message"]
        assert "simplify" in row["message"]

    @pytest.mark.asyncio
    async def test_summary_shows_none_when_no_skills(self, db):
        from services.executor import _emit_summary

        result_meta = json.dumps({"type": "result", "total_cost_usd": 0.1, "num_turns": 1, "usage": {"input_tokens": 10, "output_tokens": 5}})
        await _insert_log(db, "job-sk2", "stdout", "[success]", event_type="result", metadata=result_meta)

        await _emit_summary("job-sk2")

        cursor = await db.execute(
            "SELECT message FROM job_logs WHERE job_id = 'job-sk2' AND message LIKE '%摘要%'"
        )
        row = await cursor.fetchone()
        assert "(none)" in row["message"] or "（無）" in row["message"]


class TestEmitSummaryMissingResult:
    """Verify summary is skipped when no result event exists."""

    @pytest.mark.asyncio
    async def test_no_summary_when_no_result_event(self, db):
        from services.executor import _emit_summary

        await _insert_log(db, "job-nr1", "stdout", "Some regular log", event_type="assistant")

        await _emit_summary("job-nr1")

        cursor = await db.execute(
            "SELECT message FROM job_logs WHERE job_id = 'job-nr1' AND message LIKE '%摘要%'"
        )
        row = await cursor.fetchone()
        assert row is None
