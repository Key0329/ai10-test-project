"""Tests for MCP/Skill event_type classification in _extract_display_message."""

import json

import pytest


class TestExtractDisplayMessageMcpClassification:
    """Verify MCP tool calls are classified as event_type 'mcp'."""

    def test_mcp_tool_returns_mcp_event_type(self):
        from services.executor import _extract_display_message

        parsed = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "name": "mcp__github__create_pr", "input": {"description": "Create PR"}}
                ]
            },
        }
        event_type, msg = _extract_display_message("assistant", parsed)
        assert event_type == "mcp"
        assert "[mcp]" in msg

    def test_mcp_tool_prefix_in_message(self):
        from services.executor import _extract_display_message

        parsed = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "name": "mcp__context7__query", "input": {"description": "Query docs"}}
                ]
            },
        }
        event_type, msg = _extract_display_message("assistant", parsed)
        assert "[mcp]" in msg
        assert "mcp__context7__query" in msg


class TestExtractDisplayMessageSkillClassification:
    """Verify Skill tool calls are classified as event_type 'skill'."""

    def test_skill_tool_returns_skill_event_type(self):
        from services.executor import _extract_display_message

        parsed = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Skill", "input": {"skill": "commit"}}
                ]
            },
        }
        event_type, msg = _extract_display_message("assistant", parsed)
        assert event_type == "skill"
        assert "[skill]" in msg


class TestExtractDisplayMessageMixedTools:
    """Verify priority logic: mcp > skill > assistant."""

    def test_mixed_mcp_and_regular_returns_mcp(self):
        from services.executor import _extract_display_message

        parsed = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}},
                    {"type": "tool_use", "name": "mcp__github__list_prs", "input": {}},
                ]
            },
        }
        event_type, _ = _extract_display_message("assistant", parsed)
        assert event_type == "mcp"

    def test_mixed_skill_and_regular_returns_skill(self):
        from services.executor import _extract_display_message

        parsed = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}},
                    {"type": "tool_use", "name": "Skill", "input": {"skill": "commit"}},
                ]
            },
        }
        event_type, _ = _extract_display_message("assistant", parsed)
        assert event_type == "skill"

    def test_mixed_mcp_and_skill_returns_mcp(self):
        from services.executor import _extract_display_message

        parsed = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Skill", "input": {"skill": "commit"}},
                    {"type": "tool_use", "name": "mcp__github__create_pr", "input": {}},
                ]
            },
        }
        event_type, _ = _extract_display_message("assistant", parsed)
        assert event_type == "mcp"


class TestExtractDisplayMessageBackwardCompat:
    """Verify regular tools and non-assistant events remain unchanged."""

    def test_regular_tool_returns_assistant_event_type(self):
        from services.executor import _extract_display_message

        parsed = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Bash", "input": {"command": "git status"}},
                ]
            },
        }
        event_type, msg = _extract_display_message("assistant", parsed)
        assert event_type == "assistant"
        assert "[tool]" in msg

    def test_text_only_assistant_returns_assistant(self):
        from services.executor import _extract_display_message

        parsed = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "Hello, world!"},
                ]
            },
        }
        event_type, msg = _extract_display_message("assistant", parsed)
        assert event_type == "assistant"
        assert msg == "Hello, world!"

    def test_system_event_unchanged(self):
        from services.executor import _extract_display_message

        parsed = {"type": "system", "subtype": "init", "model": "opus"}
        event_type, msg = _extract_display_message("system", parsed)
        assert event_type == "system"

    def test_result_event_unchanged(self):
        from services.executor import _extract_display_message

        parsed = {"type": "result", "subtype": "success", "result": "Done"}
        event_type, msg = _extract_display_message("result", parsed)
        assert event_type == "result"

    def test_user_event_unchanged(self):
        from services.executor import _extract_display_message

        parsed = {"type": "user", "tool_use_result": "output text"}
        event_type, msg = _extract_display_message("user", parsed)
        assert event_type == "user"
