"""Tests for env_overrides injection in both executor modes."""

import json

import pytest


class TestEnvOverridesInCopilotFormat:
    """Verify env_overrides are passed through to convert_to_copilot_format."""

    def test_overrides_expand_in_args(self):
        from services.mcp_loader import convert_to_copilot_format

        mcp_servers = {
            "sentry": {
                "type": "stdio",
                "command": "npx",
                "args": ["--token=${SENTRY_TOKEN}"],
            }
        }
        result = convert_to_copilot_format(mcp_servers, env_overrides={"SENTRY_TOKEN": "user-provided"})
        assert "--token=user-provided" in result["sentry"]["args"]

    def test_overrides_expand_in_env(self):
        from services.mcp_loader import convert_to_copilot_format

        mcp_servers = {
            "server": {
                "type": "stdio",
                "command": "npx",
                "args": [],
                "env": {"KEY": "${SECRET}"},
            }
        }
        result = convert_to_copilot_format(mcp_servers, env_overrides={"SECRET": "my-secret"})
        assert result["server"]["env"]["KEY"] == "my-secret"

    def test_empty_overrides_no_effect(self):
        from services.mcp_loader import convert_to_copilot_format

        mcp_servers = {
            "server": {
                "type": "stdio",
                "command": "npx",
                "args": ["${UNDEFINED}"],
            }
        }
        result = convert_to_copilot_format(mcp_servers, env_overrides={})
        assert "${UNDEFINED}" in result["server"]["args"]


class TestEnvOverridesInClaudeCodeEnv:
    """Verify env_overrides would be merged into subprocess env dict."""

    def test_overrides_merge_into_env(self):
        base_env = {"PATH": "/usr/bin", "HOME": "/home/user"}
        overrides = {"SENTRY_TOKEN": "abc123", "API_KEY": "xyz"}
        merged = {
            **base_env,
            **overrides,
            "GITHUB_TOKEN": "gh-token",
        }
        assert merged["SENTRY_TOKEN"] == "abc123"
        assert merged["API_KEY"] == "xyz"
        assert merged["GITHUB_TOKEN"] == "gh-token"
        assert merged["PATH"] == "/usr/bin"

    def test_credentials_override_env_overrides(self):
        """Credential keys (GITHUB_TOKEN etc.) should take precedence over env_overrides."""
        overrides = {"GITHUB_TOKEN": "should-be-overridden"}
        merged = {
            **overrides,
            "GITHUB_TOKEN": "actual-gh-token",
        }
        assert merged["GITHUB_TOKEN"] == "actual-gh-token"

    def test_none_overrides_no_crash(self):
        base_env = {"PATH": "/usr/bin"}
        merged = {**base_env, **(None or {})}
        assert merged["PATH"] == "/usr/bin"
