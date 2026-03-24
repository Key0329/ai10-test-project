"""Tests for _stream_output JSON parsing and _log extended signature."""

import asyncio
import json

import aiosqlite
import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def db(tmp_path, monkeypatch):
    """Set up a temp DB and patch get_db to return fresh connections."""
    db_path = str(tmp_path / "test.sqlite")

    # Initialize schema once
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

    # Yield a read connection for assertions
    read_conn = await aiosqlite.connect(db_path)
    read_conn.row_factory = aiosqlite.Row
    yield read_conn
    await read_conn.close()


def _make_stream(lines: list[str]):
    """Create a fake async stream from a list of strings."""
    data = "".join(line + "\n" for line in lines).encode()
    reader = asyncio.StreamReader()
    reader.feed_data(data)
    reader.feed_eof()
    return reader


class TestLog:
    """Verify _log supports event_type and metadata parameters."""

    @pytest.mark.asyncio
    async def test_log_with_event_type_and_metadata(self, db):
        from services.executor import _log

        await _log("job-1", "stdout", "hello", event_type="assistant", metadata='{"type":"assistant"}')
        cursor = await db.execute("SELECT event_type, metadata FROM job_logs WHERE job_id = 'job-1'")
        row = await cursor.fetchone()
        assert row["event_type"] == "assistant"
        assert row["metadata"] == '{"type":"assistant"}'

    @pytest.mark.asyncio
    async def test_log_defaults_to_raw(self, db):
        from services.executor import _log

        await _log("job-2", "stdout", "plain text")
        cursor = await db.execute("SELECT event_type, metadata FROM job_logs WHERE job_id = 'job-2'")
        row = await cursor.fetchone()
        assert row["event_type"] == "raw"
        assert row["metadata"] is None


class TestStreamOutput:
    """Verify _stream_output parses JSON events and falls back to raw."""

    @pytest.mark.asyncio
    async def test_valid_json_parsed_as_event(self, db):
        from services.executor import _stream_output

        event = json.dumps({"type": "assistant", "message": "hello"})
        stream = _make_stream([event])
        await _stream_output("job-1", "stdout", stream)

        cursor = await db.execute("SELECT message, event_type, metadata FROM job_logs WHERE job_id = 'job-1'")
        row = await cursor.fetchone()
        assert row["event_type"] == "assistant"
        assert row["metadata"] is not None
        parsed = json.loads(row["metadata"])
        assert parsed["type"] == "assistant"

    @pytest.mark.asyncio
    async def test_non_json_line_stored_as_raw(self, db):
        from services.executor import _stream_output

        stream = _make_stream(["this is plain text"])
        await _stream_output("job-2", "stderr", stream)

        cursor = await db.execute("SELECT message, event_type, metadata FROM job_logs WHERE job_id = 'job-2'")
        row = await cursor.fetchone()
        assert row["event_type"] == "raw"
        assert row["metadata"] is None
        assert row["message"] == "this is plain text"

    @pytest.mark.asyncio
    async def test_json_without_type_field_stored_as_raw(self, db):
        from services.executor import _stream_output

        event = json.dumps({"data": "no type field"})
        stream = _make_stream([event])
        await _stream_output("job-3", "stdout", stream)

        cursor = await db.execute("SELECT event_type, metadata FROM job_logs WHERE job_id = 'job-3'")
        row = await cursor.fetchone()
        assert row["event_type"] == "raw"

    @pytest.mark.asyncio
    async def test_mixed_lines(self, db):
        from services.executor import _stream_output

        lines = [
            json.dumps({"type": "tool_use", "tool": "Edit"}),
            "plain stderr output",
            json.dumps({"type": "tool_result", "result": "ok"}),
        ]
        stream = _make_stream(lines)
        await _stream_output("job-4", "stdout", stream)

        cursor = await db.execute(
            "SELECT event_type FROM job_logs WHERE job_id = 'job-4' ORDER BY id"
        )
        rows = await cursor.fetchall()
        assert [r["event_type"] for r in rows] == ["tool_use", "raw", "tool_result"]


class TestExtractDisplayMessage:
    """Verify _extract_display_message refines event_type correctly."""

    def test_pure_text_returns_assistant(self):
        from services.executor import _extract_display_message

        parsed = {
            "message": {
                "content": [{"type": "text", "text": "Hello world"}],
            }
        }
        refined, msg = _extract_display_message("assistant", parsed)
        assert refined == "assistant"
        assert msg == "Hello world"

    def test_tool_use_non_mcp_non_skill_returns_tool_use(self):
        from services.executor import _extract_display_message

        parsed = {
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Edit", "input": {"command": "edit file"}},
                ],
            }
        }
        refined, msg = _extract_display_message("assistant", parsed)
        assert refined == "tool_use"

    def test_mcp_tool_still_returns_mcp(self):
        from services.executor import _extract_display_message

        parsed = {
            "message": {
                "content": [
                    {"type": "tool_use", "name": "mcp__server__tool", "input": {"description": "do stuff"}},
                ],
            }
        }
        refined, msg = _extract_display_message("assistant", parsed)
        assert refined == "mcp"

    def test_skill_tool_still_returns_skill(self):
        from services.executor import _extract_display_message

        parsed = {
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Skill", "input": {"description": "run skill"}},
                ],
            }
        }
        refined, msg = _extract_display_message("assistant", parsed)
        assert refined == "skill"

    def test_mixed_text_and_tool_use_returns_tool_use(self):
        from services.executor import _extract_display_message

        parsed = {
            "message": {
                "content": [
                    {"type": "text", "text": "Let me edit the file"},
                    {"type": "tool_use", "name": "Edit", "input": {"command": "edit"}},
                ],
            }
        }
        refined, msg = _extract_display_message("assistant", parsed)
        assert refined == "tool_use"

    def test_mcp_takes_priority_over_tool_use(self):
        from services.executor import _extract_display_message

        parsed = {
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Edit", "input": {}},
                    {"type": "tool_use", "name": "mcp__server__tool", "input": {}},
                ],
            }
        }
        refined, msg = _extract_display_message("assistant", parsed)
        assert refined == "mcp"

    def test_skill_takes_priority_over_tool_use(self):
        from services.executor import _extract_display_message

        parsed = {
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Edit", "input": {}},
                    {"type": "tool_use", "name": "Skill", "input": {}},
                ],
            }
        }
        refined, msg = _extract_display_message("assistant", parsed)
        assert refined == "skill"

    def test_user_event_returns_tool_result(self):
        from services.executor import _extract_display_message

        parsed = {"tool_use_result": "some output"}
        refined, msg = _extract_display_message("user", parsed)
        assert refined == "tool_result"
        assert msg == "some output"

    def test_user_event_with_dict_result_returns_tool_result(self):
        from services.executor import _extract_display_message

        parsed = {"tool_use_result": {"stdout": "ok", "stderr": ""}}
        refined, msg = _extract_display_message("user", parsed)
        assert refined == "tool_result"
        assert msg == "ok"

    def test_user_event_empty_result_returns_tool_result(self):
        from services.executor import _extract_display_message

        parsed = {"tool_use_result": ""}
        refined, msg = _extract_display_message("user", parsed)
        assert refined == "tool_result"
        assert msg is None
