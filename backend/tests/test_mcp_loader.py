"""Tests for mcp_loader: repo .mcp.json reading, format conversion, env expansion."""

import json
import os
import tempfile

import pytest


class TestLoadRepoMcpConfig:
    """Test load_repo_mcp_config() — reading .mcp.json from repo."""

    def test_valid_mcp_json(self, tmp_path):
        from services.mcp_loader import load_repo_mcp_config

        mcp_data = {
            "mcpServers": {
                "context7": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@upstash/context7-mcp@latest"],
                }
            }
        }
        (tmp_path / ".mcp.json").write_text(json.dumps(mcp_data))
        result = load_repo_mcp_config(str(tmp_path))
        assert "context7" in result
        assert result["context7"]["command"] == "npx"

    def test_no_mcp_json(self, tmp_path):
        from services.mcp_loader import load_repo_mcp_config

        result = load_repo_mcp_config(str(tmp_path))
        assert result == {}

    def test_malformed_json(self, tmp_path):
        from services.mcp_loader import load_repo_mcp_config

        (tmp_path / ".mcp.json").write_text("not valid json {{{")
        result = load_repo_mcp_config(str(tmp_path))
        assert result == {}

    def test_empty_mcp_servers(self, tmp_path):
        from services.mcp_loader import load_repo_mcp_config

        (tmp_path / ".mcp.json").write_text(json.dumps({"mcpServers": {}}))
        result = load_repo_mcp_config(str(tmp_path))
        assert result == {}

    def test_multiple_servers(self, tmp_path):
        from services.mcp_loader import load_repo_mcp_config

        mcp_data = {
            "mcpServers": {
                "server1": {"type": "stdio", "command": "npx", "args": []},
                "server2": {"type": "sse", "url": "http://localhost:3000"},
            }
        }
        (tmp_path / ".mcp.json").write_text(json.dumps(mcp_data))
        result = load_repo_mcp_config(str(tmp_path))
        assert len(result) == 2


class TestConvertToCopilotFormat:
    """Test convert_to_copilot_format() — .mcp.json → Copilot SDK format."""

    def test_stdio_to_local(self):
        from services.mcp_loader import convert_to_copilot_format

        mcp_servers = {
            "context7": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@upstash/context7-mcp@latest"],
            }
        }
        result = convert_to_copilot_format(mcp_servers)
        assert result["context7"]["type"] == "local"
        assert result["context7"]["command"] == "npx"
        assert result["context7"]["args"] == ["-y", "@upstash/context7-mcp@latest"]
        assert result["context7"]["tools"] == ["*"]

    def test_sse_to_http(self):
        from services.mcp_loader import convert_to_copilot_format

        mcp_servers = {
            "figma": {
                "type": "sse",
                "url": "http://localhost:3845/mcp",
            }
        }
        result = convert_to_copilot_format(mcp_servers)
        assert result["figma"]["type"] == "http"
        assert result["figma"]["url"] == "http://localhost:3845/mcp"
        assert result["figma"]["tools"] == ["*"]

    def test_streamable_http_to_http(self):
        from services.mcp_loader import convert_to_copilot_format

        mcp_servers = {
            "remote": {
                "type": "streamable-http",
                "url": "https://api.example.com/mcp",
            }
        }
        result = convert_to_copilot_format(mcp_servers)
        assert result["remote"]["type"] == "http"

    def test_env_field_preserved(self):
        from services.mcp_loader import convert_to_copilot_format

        mcp_servers = {
            "sentry": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@sentry/mcp"],
                "env": {"SENTRY_TOKEN": "abc123"},
            }
        }
        result = convert_to_copilot_format(mcp_servers)
        assert result["sentry"]["env"] == {"SENTRY_TOKEN": "abc123"}

    def test_default_type_is_stdio(self):
        from services.mcp_loader import convert_to_copilot_format

        mcp_servers = {
            "notype": {
                "command": "npx",
                "args": ["-y", "some-mcp"],
            }
        }
        result = convert_to_copilot_format(mcp_servers)
        assert result["notype"]["type"] == "local"

    def test_headers_preserved_for_http(self):
        from services.mcp_loader import convert_to_copilot_format

        mcp_servers = {
            "authed": {
                "type": "sse",
                "url": "http://localhost:3000",
                "headers": {"Authorization": "Bearer token123"},
            }
        }
        result = convert_to_copilot_format(mcp_servers)
        assert result["authed"]["headers"] == {"Authorization": "Bearer token123"}


class TestExpandEnvVars:
    """Test ${VAR} expansion in args, env, and url fields."""

    def test_expand_in_args(self, monkeypatch):
        from services.mcp_loader import convert_to_copilot_format

        monkeypatch.setenv("SENTRY_TOKEN", "abc123")
        mcp_servers = {
            "sentry": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@sentry/mcp", "--token=${SENTRY_TOKEN}"],
            }
        }
        result = convert_to_copilot_format(mcp_servers)
        assert "--token=abc123" in result["sentry"]["args"]

    def test_expand_in_env_values(self, monkeypatch):
        from services.mcp_loader import convert_to_copilot_format

        monkeypatch.setenv("MY_KEY", "secret")
        mcp_servers = {
            "server": {
                "type": "stdio",
                "command": "npx",
                "args": [],
                "env": {"API_KEY": "${MY_KEY}"},
            }
        }
        result = convert_to_copilot_format(mcp_servers)
        assert result["server"]["env"]["API_KEY"] == "secret"

    def test_expand_in_url(self, monkeypatch):
        from services.mcp_loader import convert_to_copilot_format

        monkeypatch.setenv("MCP_HOST", "api.example.com")
        mcp_servers = {
            "remote": {
                "type": "sse",
                "url": "https://${MCP_HOST}/mcp",
            }
        }
        result = convert_to_copilot_format(mcp_servers)
        assert result["remote"]["url"] == "https://api.example.com/mcp"

    def test_undefined_var_preserved(self):
        from services.mcp_loader import convert_to_copilot_format

        mcp_servers = {
            "server": {
                "type": "stdio",
                "command": "npx",
                "args": ["--token=${MISSING_VAR}"],
            }
        }
        result = convert_to_copilot_format(mcp_servers)
        assert "--token=${MISSING_VAR}" in result["server"]["args"]

    def test_env_overrides_take_precedence(self, monkeypatch):
        from services.mcp_loader import convert_to_copilot_format

        monkeypatch.setenv("TOKEN", "from_env")
        mcp_servers = {
            "server": {
                "type": "stdio",
                "command": "npx",
                "args": ["--token=${TOKEN}"],
            }
        }
        result = convert_to_copilot_format(mcp_servers, env_overrides={"TOKEN": "override"})
        assert "--token=override" in result["server"]["args"]


class TestDetectMissingEnvVars:
    """Test detect_missing_env_vars() — find undefined ${VAR} references."""

    def test_all_vars_defined(self, monkeypatch):
        from services.mcp_loader import detect_missing_env_vars

        monkeypatch.setenv("API_KEY", "set")
        mcp_servers = {
            "server": {
                "args": ["--key=${API_KEY}"],
                "env": {},
            }
        }
        result = detect_missing_env_vars(mcp_servers)
        assert result == []

    def test_missing_var_in_args(self, monkeypatch):
        from services.mcp_loader import detect_missing_env_vars

        monkeypatch.delenv("MISSING_TOKEN", raising=False)
        mcp_servers = {
            "server": {
                "args": ["--token=${MISSING_TOKEN}"],
            }
        }
        result = detect_missing_env_vars(mcp_servers)
        assert "MISSING_TOKEN" in result

    def test_missing_var_in_env(self, monkeypatch):
        from services.mcp_loader import detect_missing_env_vars

        monkeypatch.delenv("SECRET", raising=False)
        mcp_servers = {
            "server": {
                "env": {"KEY": "${SECRET}"},
            }
        }
        result = detect_missing_env_vars(mcp_servers)
        assert "SECRET" in result

    def test_multiple_missing_sorted(self, monkeypatch):
        from services.mcp_loader import detect_missing_env_vars

        monkeypatch.delenv("BBB", raising=False)
        monkeypatch.delenv("AAA", raising=False)
        mcp_servers = {
            "server": {
                "args": ["${BBB}", "${AAA}"],
            }
        }
        result = detect_missing_env_vars(mcp_servers)
        assert result == ["AAA", "BBB"]

    def test_no_vars_returns_empty(self):
        from services.mcp_loader import detect_missing_env_vars

        mcp_servers = {
            "server": {
                "args": ["--plain-arg"],
                "env": {"KEY": "literal"},
            }
        }
        result = detect_missing_env_vars(mcp_servers)
        assert result == []
