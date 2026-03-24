## ADDED Requirements

### Requirement: Accept env_overrides for variable expansion

The job creation endpoint SHALL accept an `env_overrides` field (dict of string key-value pairs) in the request body. These overrides SHALL be passed to `convert_to_copilot_format()` for Copilot mode and injected into the subprocess environment for Claude Code mode.

#### Scenario: Copilot mode with env_overrides

- **WHEN** a Copilot mode job is created with `env_overrides: {"SENTRY_TOKEN": "abc123"}` and the repo `.mcp.json` references `${SENTRY_TOKEN}`
- **THEN** the executor SHALL expand `${SENTRY_TOKEN}` to `abc123` in the MCP server configuration

#### Scenario: Claude Code mode with env_overrides

- **WHEN** a Claude Code mode job is created with `env_overrides: {"SENTRY_TOKEN": "abc123"}`
- **THEN** the executor SHALL include `SENTRY_TOKEN=abc123` in the subprocess environment variables

#### Scenario: No env_overrides provided

- **WHEN** a job is created without `env_overrides`
- **THEN** the system SHALL behave identically to the current implementation (fallback to system environment variables)
