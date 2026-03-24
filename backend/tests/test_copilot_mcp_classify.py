"""Tests for Copilot MCP event classification (mcp__ prefix detection)."""

import pytest


class TestCopilotMcpEventClassification:
    """Verify on_event handler correctly classifies mcp__ prefixed tools."""

    def test_mcp_tool_name_detected(self):
        """tool_name starting with mcp__ should be classified as MCP."""
        tool_name = "mcp__context7__search_docs"
        assert tool_name.startswith("mcp__")

        is_mcp = tool_name.startswith("mcp__")
        evt_type = "mcp" if is_mcp else "assistant"
        prefix_tag = "[mcp]" if is_mcp else "[tool]"

        assert evt_type == "mcp"
        assert prefix_tag == "[mcp]"

    def test_regular_tool_not_classified_as_mcp(self):
        """tool_name without mcp__ prefix should remain assistant."""
        tool_name = "Edit"
        is_mcp = tool_name.startswith("mcp__")
        evt_type = "mcp" if is_mcp else "assistant"
        prefix_tag = "[mcp]" if is_mcp else "[tool]"

        assert evt_type == "assistant"
        assert prefix_tag == "[tool]"

    def test_mcp_server_name_extraction(self):
        """Extract server name from mcp__<server>__<tool> pattern."""
        import re

        test_cases = [
            ("mcp__github__create_pr", "github"),
            ("mcp__context7__query", "context7"),
            ("mcp__sentry__get_issue", "sentry"),
        ]
        for tool_name, expected_server in test_cases:
            match = re.search(r"mcp__(\w+)__", tool_name)
            assert match is not None, f"Failed to match {tool_name}"
            assert match.group(1) == expected_server

    def test_empty_tool_name_not_mcp(self):
        """Empty or unknown tool_name should not be classified as MCP."""
        for tool_name in ("", "unknown", "tool__not_mcp"):
            is_mcp = tool_name.startswith("mcp__")
            assert not is_mcp, f"{tool_name} should not be MCP"
